[CmdletBinding()]
param(
    [string]$AnsibleRoot = "C:\Athanor\ansible",
    [string]$RenderedDir = ".\reports\rendered",
    [string]$LiveDir = ".\reports\live",
    [string]$OutputDir = ".\reports\deployment-drift"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$rendererPath = Join-Path -Path $PSScriptRoot -ChildPath "render_ansible_template.py"

function ConvertTo-BashLiteral {
    param([string]$Text)

    if ($null -eq $Text) {
        return "''"
    }

    return "'" + $Text.Replace("'", ("'" + '"' + "'" + '"' + "'")) + "'"
}

function Write-Utf8File {
    param(
        [string]$PathText,
        [string]$Content
    )

    $normalized = $Content -replace "`r`n", "`n"
    while ($normalized.Contains("`n`n`n")) {
        $normalized = $normalized -replace "(`n){3,}", "`n`n"
    }
    $normalized = $normalized.TrimEnd("`r", "`n")
    if (-not $normalized.EndsWith("`n")) {
        $normalized += "`n"
    }

    [System.IO.Directory]::CreateDirectory((Split-Path -Path $PathText -Parent)) | Out-Null
    [System.IO.File]::WriteAllText($PathText, $normalized, $utf8NoBom)
}

function Invoke-RemoteScript {
    param(
        [string]$HostAlias,
        [string]$CommandText
    )

    $encoded = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($CommandText))
    $remotePayload = "printf %s " + (ConvertTo-BashLiteral -Text $encoded) + " | base64 -d | bash"
    $bashCommand = "bash -lc " + (ConvertTo-BashLiteral -Text $remotePayload)
    $output = @(& ssh -o BatchMode=yes $HostAlias $bashCommand 2>$null)

    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output = ($output -join "`n")
    }
}

function Protect-SensitiveText {
    param([string]$Text)

    $result = $Text
    $result = $result -replace "`0", ""
    $result = [regex]::Replace($result, '(?m)(\s+)#.*$', '')
    $result = [regex]::Replace($result, 'redis://:([^@/\s]+)@', 'redis://:<redacted>@')
    $result = [regex]::Replace($result, '(?im)^(\s*-\s*[A-Z0-9_]*REDIS_URL[A-Z0-9_]*=).+$', '$1<redacted>')
    $result = [regex]::Replace($result, '(?im)^(\s*[A-Z0-9_]*REDIS_URL[A-Z0-9_]*:\s*).+$', '$1<redacted>')
    $result = [regex]::Replace($result, '(?im)^(\s*-\s*[A-Z0-9_]*(?:KEY|PASSWORD|TOKEN|SECRET|DATABASE_URL)[A-Z0-9_]*=).+$', '$1<redacted>')
    $result = [regex]::Replace($result, '(?im)^(\s*[A-Z0-9_]*(?:KEY|PASSWORD|TOKEN|SECRET|DATABASE_URL)[A-Z0-9_]*:\s*).+$', '$1<redacted>')
    $result = [regex]::Replace($result, '(?im)^(\s*api_key:\s*)"(?!not-needed|os\.environ/)[^"]+"', '$1"<redacted>"')
    $result = [regex]::Replace($result, '(?m)^[ \t]*\r?\n', '')
    return $result
}

function Get-RemoteFileContent {
    param(
        [string]$HostAlias,
        [string]$RemotePath
    )

    $commandText = @(
        "target=" + (ConvertTo-BashLiteral -Text $RemotePath)
        'if [ -f "$target" ]; then'
        '  cat "$target"'
        'else'
        '  exit 4'
        'fi'
    ) -join "`n"

    $result = Invoke-RemoteScript -HostAlias $HostAlias -CommandText $commandText
    $exitCode = $result.ExitCode

    if ($exitCode -eq 4) {
        return $null
    }

    if ($exitCode -ne 0) {
        throw "Failed to read remote file '$RemotePath' on host '$HostAlias'."
    }

    return $result.Output
}

function Get-ComposeRuntimeSnapshot {
    param(
        [string]$HostAlias,
        [string]$RemotePath
    )

    $commandText = @(
        "target=" + (ConvertTo-BashLiteral -Text $RemotePath)
        'if [ ! -f "$target" ]; then'
        '  exit 4'
        'fi'
        'project_dir=$(dirname "$target")'
        'project_name=$(basename "$project_dir")'
        'primary_output=$(docker compose -f "$target" ps -a --format json 2>&1)'
        'primary_status=$?'
        'if [ $primary_status -eq 0 ] && [ -n "$(printf %s "$primary_output" | tr -d ''[:space:]'')" ]; then'
        '  printf "%s\n" "$primary_output"'
        '  exit 0'
        'fi'
        'fallback_output=$(docker ps -a --filter "label=com.docker.compose.project=$project_name" --format json 2>&1)'
        'fallback_status=$?'
        'if [ $fallback_status -eq 0 ] && [ -n "$(printf %s "$fallback_output" | tr -d ''[:space:]'')" ]; then'
        '  printf "%s\n" "$fallback_output"'
        '  exit 0'
        'fi'
        'if [ $primary_status -ne 0 ]; then'
        '  printf "%s\n" "$primary_output"'
        '  exit $primary_status'
        'fi'
        'if [ $fallback_status -ne 0 ]; then'
        '  printf "%s\n" "$fallback_output"'
        '  exit $fallback_status'
        'fi'
    ) -join "`n"

    $result = Invoke-RemoteScript -HostAlias $HostAlias -CommandText $commandText
    if ($result.ExitCode -eq 4) {
        return [pscustomobject]@{
            RuntimeState = "missing_live_file"
            ContainerCount = 0
            RunningCount = 0
            Services = @()
        }
    }

    if ($result.ExitCode -ne 0) {
        return [pscustomobject]@{
            RuntimeState = "probe_failed"
            ContainerCount = 0
            RunningCount = 0
            Services = @()
        }
    }

    $serviceRecords = New-Object System.Collections.Generic.List[object]
    $rawOutput = [string]$result.Output
    $rawOutput = $rawOutput.Trim()
    if (-not [string]::IsNullOrWhiteSpace($rawOutput)) {
        foreach ($line in ($rawOutput -split "`r?`n")) {
            $trimmed = $line.Trim()
            if ([string]::IsNullOrWhiteSpace($trimmed)) {
                continue
            }

            $parsed = $trimmed | ConvertFrom-Json
            $name = if ($null -ne $parsed.Name -and [string]$parsed.Name) {
                [string]$parsed.Name
            } elseif ($null -ne $parsed.Names -and [string]$parsed.Names) {
                [string]$parsed.Names
            } else {
                ""
            }
            $serviceRecords.Add([pscustomobject]@{
                Name = $name
                Service = [string]$parsed.Service
                State = [string]$parsed.State
                Status = [string]$parsed.Status
                Image = [string]$parsed.Image
                Ports = [string]$parsed.Ports
            })
        }
    }

    $services = $serviceRecords.ToArray()
    $containerCount = $services.Count
    $runningCount = @($services | Where-Object { $_.State -eq "running" }).Count
    $runtimeState = if ($containerCount -eq 0) {
        "no_containers"
    } elseif ($runningCount -eq $containerCount) {
        "running"
    } elseif ($runningCount -gt 0) {
        "partial"
    } else {
        "not_running"
    }

    return [pscustomobject]@{
        RuntimeState = $runtimeState
        ContainerCount = $containerCount
        RunningCount = $runningCount
        Services = $services
    }
}

function Get-GitNumStat {
    param(
        [string]$RenderedPath,
        [string]$LivePath
    )

    $output = @(& git -c core.autocrlf=false -c core.safecrlf=false diff --no-index --ignore-cr-at-eol --text --numstat -- $RenderedPath $LivePath 2>$null)
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0 -or -not $output -or $output.Count -eq 0) {
        return [pscustomobject]@{
            Status = "identical"
            AddedLines = 0
            DeletedLines = 0
        }
    }

    $firstLine = $output[0].Trim()
    $parts = @($firstLine -split "`t")
    if ($parts.Count -lt 2) {
        return [pscustomobject]@{
            Status = "different"
            AddedLines = 0
            DeletedLines = 0
        }
    }

    $addedLines = 0
    $deletedLines = 0
    [void][int]::TryParse($parts[0], [ref]$addedLines)
    [void][int]::TryParse($parts[1], [ref]$deletedLines)

    return [pscustomobject]@{
        Status = "different"
        AddedLines = $addedLines
        DeletedLines = $deletedLines
    }
}

function Write-DiffFile {
    param(
        [string]$RenderedPath,
        [string]$LivePath,
        [string]$DiffPath
    )

    $diffText = @(& git -c core.autocrlf=false -c core.safecrlf=false diff --no-index --no-color --ignore-cr-at-eol --text --unified=3 -- $RenderedPath $LivePath 2>$null)
    if ($LASTEXITCODE -eq 0 -or -not $diffText -or $diffText.Count -eq 0) {
        if (Test-Path -LiteralPath $DiffPath) {
            Remove-Item -LiteralPath $DiffPath -Force
        }
        return $false
    }

    Write-Utf8File -PathText $DiffPath -Content ($diffText -join "`n")
    return $true
}

if (-not (Test-Path -LiteralPath $rendererPath)) {
    throw "Missing renderer script: $rendererPath"
}

New-Item -ItemType Directory -Force -Path $RenderedDir | Out-Null
New-Item -ItemType Directory -Force -Path $LiveDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$comparisons = @(
    [pscustomobject]@{
        Id = "vault-litellm"
        HostAlias = "vault"
        HostVars = "vault"
        Template = "roles\vault-litellm\templates\litellm_config.yaml.j2"
        Defaults = @("roles\vault-litellm\defaults\main.yml")
        LivePath = "/mnt/user/appdata/litellm/config.yaml"
        RenderedFile = "vault-litellm-config.rendered.yaml"
        LiveFile = "vault-litellm-config.live.yaml"
    }
    [pscustomobject]@{
        Id = "vault-prometheus"
        HostAlias = "vault"
        HostVars = "vault"
        Template = "roles\vault-monitoring\templates\prometheus.yml.j2"
        Defaults = @("roles\vault-monitoring\defaults\main.yml")
        LivePath = "/mnt/user/appdata/prometheus/prometheus.yml"
        RenderedFile = "vault-prometheus.rendered.yml"
        LiveFile = "vault-prometheus.live.yml"
    }
    [pscustomobject]@{
        Id = "vault-alert-rules"
        HostAlias = "vault"
        HostVars = "vault"
        Template = "roles\vault-monitoring\templates\alert-rules.yml.j2"
        Defaults = @("roles\vault-monitoring\defaults\main.yml")
        LivePath = "/mnt/user/appdata/prometheus/alert-rules.yml"
        RenderedFile = "vault-alert-rules.rendered.yml"
        LiveFile = "vault-alert-rules.live.yml"
    }
    [pscustomobject]@{
        Id = "vault-backup-alerts"
        HostAlias = "vault"
        HostVars = "vault"
        Template = "roles\vault-grafana-alerts\templates\backup-alerts.yml.j2"
        Defaults = @("roles\vault-grafana-alerts\defaults\main.yml")
        LivePath = "/mnt/appdatacache/grafana/provisioning/alerting/backup-alerts.yml"
        RenderedFile = "vault-backup-alerts.rendered.yml"
        LiveFile = "vault-backup-alerts.live.yml"
    }
    [pscustomobject]@{
        Id = "foundry-agents"
        HostAlias = "foundry"
        HostVars = "core"
        Template = "roles\agents\templates\docker-compose.yml.j2"
        Defaults = @("roles\agents\defaults\main.yml")
        LivePath = "/opt/athanor/agents/docker-compose.yml"
        RenderedFile = "foundry-agents.rendered.yml"
        LiveFile = "foundry-agents.live.yml"
    }
    [pscustomobject]@{
        Id = "foundry-qdrant"
        HostAlias = "foundry"
        HostVars = "core"
        Template = "roles\qdrant\templates\config.yaml.j2"
        Defaults = @("roles\qdrant\defaults\main.yml")
        LivePath = "/opt/athanor/qdrant/config/config.yaml"
        RenderedFile = "foundry-qdrant.rendered.yml"
        LiveFile = "foundry-qdrant.live.yml"
    }
    [pscustomobject]@{
        Id = "foundry-vllm"
        HostAlias = "foundry"
        HostVars = "core"
        Template = "roles\vllm\templates\docker-compose.yml.j2"
        Defaults = @("roles\vllm\defaults\main.yml")
        LivePath = "/opt/athanor/vllm/docker-compose.yml"
        RenderedFile = "foundry-vllm.rendered.yml"
        LiveFile = "foundry-vllm.live.yml"
    }
    [pscustomobject]@{
        Id = "foundry-gpu-orchestrator"
        HostAlias = "foundry"
        HostVars = "core"
        Template = "roles\gpu-orchestrator\templates\docker-compose.yml.j2"
        Defaults = @("roles\gpu-orchestrator\defaults\main.yml")
        LivePath = "/opt/athanor/gpu-orchestrator/docker-compose.yml"
        RenderedFile = "foundry-gpu-orchestrator.rendered.yml"
        LiveFile = "foundry-gpu-orchestrator.live.yml"
    }
    [pscustomobject]@{
        Id = "workshop-dashboard"
        HostAlias = "workshop"
        HostVars = "interface"
        Template = "roles\dashboard\templates\docker-compose.yml.j2"
        Defaults = @("roles\dashboard\defaults\main.yml")
        LivePath = "/opt/athanor/dashboard/docker-compose.yml"
        RenderedFile = "workshop-dashboard.rendered.yml"
        LiveFile = "workshop-dashboard.live.yml"
    }
    [pscustomobject]@{
        Id = "workshop-open-webui"
        HostAlias = "workshop"
        HostVars = "interface"
        Template = "roles\open-webui\templates\docker-compose.yml.j2"
        Defaults = @("roles\open-webui\defaults\main.yml")
        LivePath = "/opt/athanor/open-webui/docker-compose.yml"
        RenderedFile = "workshop-open-webui.rendered.yml"
        LiveFile = "workshop-open-webui.live.yml"
    }
    [pscustomobject]@{
        Id = "workshop-vllm"
        HostAlias = "workshop"
        HostVars = "interface"
        Template = "roles\vllm\templates\docker-compose.yml.j2"
        Defaults = @("roles\vllm\defaults\main.yml")
        LivePath = "/opt/athanor/vllm-node2/docker-compose.yml"
        RenderedFile = "workshop-vllm.rendered.yml"
        LiveFile = "workshop-vllm.live.yml"
    }
    [pscustomobject]@{
        Id = "workshop-comfyui"
        HostAlias = "workshop"
        HostVars = "interface"
        Template = "roles\comfyui\templates\docker-compose.yml.j2"
        Defaults = @("roles\comfyui\defaults\main.yml")
        LivePath = "/opt/athanor/comfyui/docker-compose.yml"
        RenderedFile = "workshop-comfyui.rendered.yml"
        LiveFile = "workshop-comfyui.live.yml"
    }
    [pscustomobject]@{
        Id = "workshop-eoq"
        HostAlias = "workshop"
        HostVars = "interface"
        Template = "roles\eoq\templates\docker-compose.yml.j2"
        Defaults = @("roles\eoq\defaults\main.yml")
        LivePath = "/opt/athanor/eoq/docker-compose.yml"
        RenderedFile = "workshop-eoq.rendered.yml"
        LiveFile = "workshop-eoq.live.yml"
    }
    [pscustomobject]@{
        Id = "workshop-ulrich-energy"
        HostAlias = "workshop"
        HostVars = "interface"
        Template = "roles\ulrich-energy\templates\docker-compose.yml.j2"
        Defaults = @("roles\ulrich-energy\defaults\main.yml")
        LivePath = "/opt/athanor/ulrich-energy/docker-compose.yml"
        RenderedFile = "workshop-ulrich-energy.rendered.yml"
        LiveFile = "workshop-ulrich-energy.live.yml"
    }
)

$summaryRecords = New-Object System.Collections.Generic.List[object]

foreach ($comparison in $comparisons) {
    Write-Host "Auditing $($comparison.Id)"

    $renderedPath = Join-Path -Path $RenderedDir -ChildPath $comparison.RenderedFile
    $livePath = Join-Path -Path $LiveDir -ChildPath $comparison.LiveFile
    $diffPath = Join-Path -Path $OutputDir -ChildPath ($comparison.Id + ".diff")
    $runtimePath = Join-Path -Path $LiveDir -ChildPath ($comparison.Id + ".runtime.json")
    $isComposeComparison = $comparison.LivePath.EndsWith("/docker-compose.yml")

    $defaultsArgs = @()
    foreach ($defaultsPath in $comparison.Defaults) {
        $defaultsArgs += @("--defaults", $defaultsPath)
    }

    $renderCommand = @(
        "python"
        $rendererPath
        "--ansible-root"
        $AnsibleRoot
        "--host"
        $comparison.HostVars
        "--template"
        $comparison.Template
        "--output"
        $renderedPath
    ) + $defaultsArgs

    & $renderCommand[0] $renderCommand[1..($renderCommand.Count - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to render template for $($comparison.Id)."
    }

    $renderedContent = Get-Content -LiteralPath $renderedPath -Raw -Encoding utf8
    $sanitizedRenderedContent = Protect-SensitiveText -Text $renderedContent
    Write-Utf8File -PathText $renderedPath -Content $sanitizedRenderedContent

    $liveContent = Get-RemoteFileContent -HostAlias $comparison.HostAlias -RemotePath $comparison.LivePath
    if ($null -eq $liveContent) {
        if (Test-Path -LiteralPath $livePath) {
            Remove-Item -LiteralPath $livePath -Force
        }
        if (Test-Path -LiteralPath $runtimePath) {
            Remove-Item -LiteralPath $runtimePath -Force
        }

        $summaryRecords.Add([pscustomobject]@{
            Id = $comparison.Id
            HostAlias = $comparison.HostAlias
            Status = "missing live file"
            AddedLines = 0
            DeletedLines = 0
            Template = $comparison.Template
            LivePath = $comparison.LivePath
            RenderedPath = $renderedPath
            LiveOutputPath = ""
            DiffPath = ""
            RuntimeState = "missing_live_file"
            RuntimeContainerCount = 0
            RuntimeRunningCount = 0
            RuntimeOutputPath = ""
        })
        continue
    }

    $sanitizedLiveContent = Protect-SensitiveText -Text $liveContent
    Write-Utf8File -PathText $livePath -Content $sanitizedLiveContent
    $numStat = Get-GitNumStat -RenderedPath $renderedPath -LivePath $livePath
    $hasDiff = Write-DiffFile -RenderedPath $renderedPath -LivePath $livePath -DiffPath $diffPath
    $runtimeSnapshot = $null
    if ($isComposeComparison) {
        $runtimeSnapshot = Get-ComposeRuntimeSnapshot -HostAlias $comparison.HostAlias -RemotePath $comparison.LivePath
        $runtimePayload = @{
            id = $comparison.Id
            host_alias = $comparison.HostAlias
            live_path = $comparison.LivePath
            observed_at = (Get-Date).ToUniversalTime().ToString("o")
            runtime_state = $runtimeSnapshot.RuntimeState
            container_count = $runtimeSnapshot.ContainerCount
            running_count = $runtimeSnapshot.RunningCount
            services = @($runtimeSnapshot.Services)
        } | ConvertTo-Json -Depth 6
        Write-Utf8File -PathText $runtimePath -Content $runtimePayload
    } elseif (Test-Path -LiteralPath $runtimePath) {
        Remove-Item -LiteralPath $runtimePath -Force
    }

    $summaryRecords.Add([pscustomobject]@{
        Id = $comparison.Id
        HostAlias = $comparison.HostAlias
        Status = $numStat.Status
        AddedLines = $numStat.AddedLines
        DeletedLines = $numStat.DeletedLines
        Template = $comparison.Template
        LivePath = $comparison.LivePath
        RenderedPath = $renderedPath
        LiveOutputPath = $livePath
        DiffPath = if ($hasDiff) { $diffPath } else { "" }
        RuntimeState = if ($runtimeSnapshot) { $runtimeSnapshot.RuntimeState } else { "not_applicable" }
        RuntimeContainerCount = if ($runtimeSnapshot) { $runtimeSnapshot.ContainerCount } else { 0 }
        RuntimeRunningCount = if ($runtimeSnapshot) { $runtimeSnapshot.RunningCount } else { 0 }
        RuntimeOutputPath = if ($runtimeSnapshot) { $runtimePath } else { "" }
    })
}

$summaryCsvPath = Join-Path -Path $OutputDir -ChildPath "summary.csv"
$summaryMdPath = Join-Path -Path $OutputDir -ChildPath "summary.md"

$sortedSummary = @($summaryRecords | Sort-Object HostAlias, Id)
$sortedSummary | Export-Csv -Path $summaryCsvPath -NoTypeInformation -Encoding utf8

$summaryLines = New-Object System.Collections.Generic.List[string]
$summaryLines.Add("# Deployment Drift Summary")
$summaryLines.Add("")
$summaryLines.Add("| Comparison | Host | Drift | Runtime | Added | Deleted | Live Path | Diff | Runtime Evidence |")
$summaryLines.Add("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
foreach ($record in $sortedSummary) {
    $diffLabel = if ([string]::IsNullOrWhiteSpace($record.DiffPath)) { "none" } else { $record.DiffPath }
    $runtimeLabel = "$($record.RuntimeState) ($($record.RuntimeRunningCount)/$($record.RuntimeContainerCount))"
    $runtimeEvidence = if ([string]::IsNullOrWhiteSpace($record.RuntimeOutputPath)) { "none" } else { $record.RuntimeOutputPath }
    $summaryLines.Add("| $($record.Id) | $($record.HostAlias) | $($record.Status) | $runtimeLabel | $($record.AddedLines) | $($record.DeletedLines) | $($record.LivePath) | $diffLabel | $runtimeEvidence |")
}

$summaryLines.Add("")
$summaryLines.Add("Rendered files are stored in reports/rendered/.")
$summaryLines.Add("Fetched live files are stored in reports/live/.")
$summaryLines.Add("Unified diffs are stored in reports/deployment-drift/.")
$summaryLines.Add("Compose runtime snapshots are stored in reports/live/*.runtime.json.")
$summaryLines.Add("Live files are sanitized before storage and comparison; secret-only substitutions can still appear as drift.")

Write-Utf8File -PathText $summaryMdPath -Content ($summaryLines -join "`n")

Write-Host ""
Write-Host "Deployment drift audit complete"
Write-Host "Summary CSV: $summaryCsvPath"
Write-Host "Summary MD:  $summaryMdPath"
