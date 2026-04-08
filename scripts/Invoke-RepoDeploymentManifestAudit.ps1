[CmdletBinding()]
param(
    [string]$SourceDir = ".\reports\repo-manifest-source",
    [string]$LiveDir = ".\reports\repo-manifest-live",
    [string]$OutputDir = ".\reports\repo-manifest-drift"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

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
    if (-not $normalized.EndsWith("`n")) {
        $normalized += "`n"
    }

    [System.IO.Directory]::CreateDirectory((Split-Path -Path $PathText -Parent)) | Out-Null
    [System.IO.File]::WriteAllText($PathText, $normalized, $utf8NoBom)
}

function Protect-SensitiveText {
    param([string]$Text)

    $result = $Text
    $result = [regex]::Replace($result, 'redis://:([^@/\s]+)@', 'redis://:<redacted>@')
    $result = [regex]::Replace($result, '(?im)^(\s*-\s*[A-Z0-9_]*REDIS_URL[A-Z0-9_]*=).+$', '$1<redacted>')
    $result = [regex]::Replace($result, '(?im)^(\s*[A-Z0-9_]*REDIS_URL[A-Z0-9_]*:\s*).+$', '$1<redacted>')
    $result = [regex]::Replace($result, '(?im)^(\s*-\s*[A-Z0-9_]*(?:KEY|PASSWORD|TOKEN|SECRET|DATABASE_URL)[A-Z0-9_]*=).+$', '$1<redacted>')
    $result = [regex]::Replace($result, '(?im)^(\s*[A-Z0-9_]*(?:KEY|PASSWORD|TOKEN|SECRET|DATABASE_URL)[A-Z0-9_]*:\s*).+$', '$1<redacted>')
    $result = [regex]::Replace($result, '(?im)^(\s*api_key:\s*)"(?!not-needed|os\.environ/)[^"]+"', '$1"<redacted>"')
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

    $encoded = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($commandText))
    $remotePayload = "printf %s " + (ConvertTo-BashLiteral -Text $encoded) + " | base64 -d | bash"
    $bashCommand = "bash -lc " + (ConvertTo-BashLiteral -Text $remotePayload)
    $output = @(& ssh -o BatchMode=yes $HostAlias $bashCommand 2>$null)
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 4) {
        return $null
    }

    if ($exitCode -ne 0) {
        throw "Failed to read remote file '$RemotePath' on host '$HostAlias'."
    }

    return ($output -join "`n")
}

function Get-GitNumStat {
    param(
        [string]$SourcePath,
        [string]$LivePath
    )

    $output = @(& git -c core.autocrlf=false -c core.safecrlf=false diff --no-index --ignore-cr-at-eol --numstat -- $SourcePath $LivePath 2>$null)
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

    return [pscustomobject]@{
        Status = "different"
        AddedLines = [int]$parts[0]
        DeletedLines = [int]$parts[1]
    }
}

function Write-DiffFile {
    param(
        [string]$SourcePath,
        [string]$LivePath,
        [string]$DiffPath
    )

    $diffText = @(& git -c core.autocrlf=false -c core.safecrlf=false diff --no-index --no-color --ignore-cr-at-eol --unified=3 -- $SourcePath $LivePath 2>$null)
    if ($LASTEXITCODE -eq 0 -or -not $diffText -or $diffText.Count -eq 0) {
        return $false
    }

    Write-Utf8File -PathText $DiffPath -Content ($diffText -join "`n")
    return $true
}

New-Item -ItemType Directory -Force -Path $SourceDir | Out-Null
New-Item -ItemType Directory -Force -Path $LiveDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$comparisons = @(
    [pscustomobject]@{
        Id = "foundry-agents-project"
        HostAlias = "foundry"
        SourcePath = "C:\Athanor\projects\agents\docker-compose.yml"
        LivePath = "/opt/athanor/agents/docker-compose.yml"
        SourceFile = "foundry-agents-project.source.yml"
        LiveFile = "foundry-agents-project.live.yml"
    }
    [pscustomobject]@{
        Id = "workshop-dashboard-project"
        HostAlias = "workshop"
        SourcePath = "C:\Athanor\projects\dashboard\docker-compose.yml"
        LivePath = "/opt/athanor/dashboard/docker-compose.yml"
        SourceFile = "workshop-dashboard-project.source.yml"
        LiveFile = "workshop-dashboard-project.live.yml"
    }
    [pscustomobject]@{
        Id = "foundry-gpu-orchestrator-project"
        HostAlias = "foundry"
        SourcePath = "C:\Athanor\projects\gpu-orchestrator\docker-compose.yml"
        LivePath = "/opt/athanor/gpu-orchestrator/docker-compose.yml"
        SourceFile = "foundry-gpu-orchestrator-project.source.yml"
        LiveFile = "foundry-gpu-orchestrator-project.live.yml"
    }
)

$summaryRecords = New-Object System.Collections.Generic.List[object]

foreach ($comparison in $comparisons) {
    Write-Host "Auditing $($comparison.Id)"

    if (-not (Test-Path -LiteralPath $comparison.SourcePath)) {
        throw "Missing local source file '$($comparison.SourcePath)' for comparison '$($comparison.Id)'."
    }

    $sourceOutputPath = Join-Path -Path $SourceDir -ChildPath $comparison.SourceFile
    $liveOutputPath = Join-Path -Path $LiveDir -ChildPath $comparison.LiveFile
    $diffPath = Join-Path -Path $OutputDir -ChildPath ($comparison.Id + ".diff")

    $sourceContent = Get-Content -Path $comparison.SourcePath -Raw -Encoding utf8
    $sanitizedSourceContent = Protect-SensitiveText -Text $sourceContent
    Write-Utf8File -PathText $sourceOutputPath -Content $sanitizedSourceContent

    $liveContent = Get-RemoteFileContent -HostAlias $comparison.HostAlias -RemotePath $comparison.LivePath
    if ($null -eq $liveContent) {
        if (Test-Path -LiteralPath $liveOutputPath) {
            Remove-Item -LiteralPath $liveOutputPath -Force
        }

        $summaryRecords.Add([pscustomobject]@{
            Id = $comparison.Id
            HostAlias = $comparison.HostAlias
            Status = "missing live file"
            AddedLines = 0
            DeletedLines = 0
            SourcePath = $comparison.SourcePath
            LivePath = $comparison.LivePath
            SourceOutputPath = $sourceOutputPath
            LiveOutputPath = ""
            DiffPath = ""
        })
        continue
    }

    $sanitizedLiveContent = Protect-SensitiveText -Text $liveContent
    Write-Utf8File -PathText $liveOutputPath -Content $sanitizedLiveContent
    $numStat = Get-GitNumStat -SourcePath $sourceOutputPath -LivePath $liveOutputPath
    $hasDiff = Write-DiffFile -SourcePath $sourceOutputPath -LivePath $liveOutputPath -DiffPath $diffPath

    $summaryRecords.Add([pscustomobject]@{
        Id = $comparison.Id
        HostAlias = $comparison.HostAlias
        Status = $numStat.Status
        AddedLines = $numStat.AddedLines
        DeletedLines = $numStat.DeletedLines
        SourcePath = $comparison.SourcePath
        LivePath = $comparison.LivePath
        SourceOutputPath = $sourceOutputPath
        LiveOutputPath = $liveOutputPath
        DiffPath = if ($hasDiff) { $diffPath } else { "" }
    })
}

$summaryCsvPath = Join-Path -Path $OutputDir -ChildPath "summary.csv"
$summaryMdPath = Join-Path -Path $OutputDir -ChildPath "summary.md"

$sortedSummary = @($summaryRecords | Sort-Object HostAlias, Id)
$sortedSummary | Export-Csv -Path $summaryCsvPath -NoTypeInformation -Encoding utf8

$summaryLines = New-Object System.Collections.Generic.List[string]
$summaryLines.Add("# Repo Manifest Drift Summary")
$summaryLines.Add("")
$summaryLines.Add("| Comparison | Host | Status | Added | Deleted | Live Path | Diff |")
$summaryLines.Add("| --- | --- | --- | --- | --- | --- | --- |")
foreach ($record in $sortedSummary) {
    $diffLabel = if ([string]::IsNullOrWhiteSpace($record.DiffPath)) { "none" } else { $record.DiffPath }
    $summaryLines.Add("| $($record.Id) | $($record.HostAlias) | $($record.Status) | $($record.AddedLines) | $($record.DeletedLines) | $($record.LivePath) | $diffLabel |")
}

$summaryLines.Add("")
$summaryLines.Add("Local repo snapshots are stored in reports/repo-manifest-source/.")
$summaryLines.Add("Fetched live files are stored in reports/repo-manifest-live/.")
$summaryLines.Add("Unified diffs are stored in reports/repo-manifest-drift/.")
$summaryLines.Add("Live files are sanitized before storage and comparison; secret-only substitutions can still appear as drift.")

Write-Utf8File -PathText $summaryMdPath -Content ($summaryLines -join "`n")

Write-Host ""
Write-Host "Repo deployment manifest audit complete"
Write-Host "Summary CSV: $summaryCsvPath"
Write-Host "Summary MD:  $summaryMdPath"
