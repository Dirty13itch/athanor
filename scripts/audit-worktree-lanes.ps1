[CmdletBinding()]
param(
    [switch]$WriteReport,
    [string]$OutputPath,
    [string[]]$RepoPaths = @(
        "C:\Athanor",
        "C:\Users\Shaun\dev\athanor-next",
        "C:\Users\Shaun\dev\Local-System",
        "C:\Agentic Coding Tools",
        "C:\Codex System Config"
    ),
    [string]$CodexHome = (Join-Path $env:USERPROFILE ".codex")
)

$ErrorActionPreference = "Stop"

if (-not $OutputPath) {
    $OutputPath = Join-Path (Split-Path -Parent $PSScriptRoot) "reports\reconciliation\worktree-lanes-latest.md"
}

function Test-GitRepo {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return $false
    }

    $inside = @(& git -C $Path rev-parse --is-inside-work-tree 2>$null)
    return ($LASTEXITCODE -eq 0 -and ($inside -join "").Trim() -eq "true")
}

function Get-DirtyEntryCount {
    param(
        [string]$RepoPath
    )

    if (-not (Test-Path $RepoPath)) {
        return -2
    }

    $statusLines = @(& git -C $RepoPath status --short 2>$null)
    if ($LASTEXITCODE -ne 0) {
        return -1
    }

    return $statusLines.Count
}

function Get-CurrentBranch {
    param(
        [string]$RepoPath
    )

    $branch = @(& git -C $RepoPath branch --show-current 2>$null)
    if ($LASTEXITCODE -ne 0 -or $branch.Count -eq 0) {
        return "detached"
    }

    $value = $branch[0].Trim()
    if ([string]::IsNullOrWhiteSpace($value)) {
        return "detached"
    }

    return $value
}

function Get-LastCommitDate {
    param(
        [string]$RepoPath
    )

    if (-not (Test-Path $RepoPath)) {
        return "missing"
    }

    $value = @(& git -C $RepoPath log -1 --date=short --format=%cd 2>$null)
    if ($LASTEXITCODE -ne 0 -or $value.Count -eq 0) {
        return "unknown"
    }

    return $value[0].Trim()
}

function Get-WorktreeRecords {
    param(
        [string]$RepoPath
    )

    $lines = @(& git -C $RepoPath worktree list --porcelain 2>$null)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read worktree list for $RepoPath"
    }

    $records = New-Object System.Collections.Generic.List[object]
    $current = @{}

    foreach ($line in ($lines + "")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            if ($current.ContainsKey("worktree")) {
                $branch = if ($current.ContainsKey("branch")) {
                    ($current["branch"] -replace "^refs/heads/", "")
                } else {
                    "detached"
                }

                $records.Add([pscustomobject]@{
                    Path = $current["worktree"]
                    Head = $current["HEAD"]
                    Branch = $branch
                    Detached = $current.ContainsKey("detached")
                    Locked = $current.ContainsKey("locked")
                    Prunable = $current.ContainsKey("prunable")
                })
            }

            $current = @{}
            continue
        }

        $parts = $line -split " ", 2
        $key = $parts[0]
        $value = if ($parts.Count -gt 1) { $parts[1] } else { "" }

        if ($key -in @("detached", "locked", "prunable")) {
            $current[$key] = $true
        } else {
            $current[$key] = $value
        }
    }

    return $records
}

$managedRoot = Join-Path $CodexHome "worktrees"
$resolvedManagedRoot = if (Test-Path $managedRoot) { (Resolve-Path $managedRoot).Path } else { $managedRoot }
$results = New-Object System.Collections.Generic.List[object]

foreach ($repoPath in $RepoPaths) {
    if (-not (Test-GitRepo -Path $repoPath)) {
        continue
    }

    $resolvedRepo = (Resolve-Path $repoPath).Path
    $worktrees = Get-WorktreeRecords -RepoPath $resolvedRepo

    foreach ($worktree in $worktrees) {
        $resolvedWorktree = if (Test-Path $worktree.Path) { (Resolve-Path $worktree.Path).Path } else { $worktree.Path }
        $dirtyCount = Get-DirtyEntryCount -RepoPath $resolvedWorktree
        $status = if ($dirtyCount -lt 0) {
            if ($dirtyCount -eq -2) {
                "missing"
            } else {
                "unavailable"
            }
        } elseif ($dirtyCount -eq 0) {
            "clean"
        } else {
            "dirty ($dirtyCount)"
        }
        $role = if ($resolvedWorktree -eq $resolvedRepo) { "primary" } else { "lane" }
        $managed = $resolvedWorktree.StartsWith($resolvedManagedRoot, [System.StringComparison]::OrdinalIgnoreCase)
        $branch = if ($worktree.Detached) { "detached" } elseif ([string]::IsNullOrWhiteSpace($worktree.Branch)) { Get-CurrentBranch -RepoPath $resolvedWorktree } else { $worktree.Branch }

        $results.Add([pscustomobject]@{
            Repo = Split-Path -Leaf $resolvedRepo
            RepoPath = $resolvedRepo
            WorktreePath = $resolvedWorktree
            Role = $role
            Branch = $branch
            Status = $status
            Managed = if ($managed) { "yes" } else { "no" }
            LastCommitDate = Get-LastCommitDate -RepoPath $resolvedWorktree
        })
    }
}

$laneCount = @($results | Where-Object { $_.Role -eq "lane" }).Count
$dirtyCount = @($results | Where-Object { $_.Status -like "dirty*" }).Count

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# Worktree Lane Status")
$lines.Add("")
$lines.Add(("Generated: {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz")))
$lines.Add("")
$lines.Add("## Summary")
$lines.Add("")
$lines.Add(("- repos_scanned={0}" -f (($results | Select-Object -ExpandProperty RepoPath -Unique).Count)))
$lines.Add(("- active_lanes={0}" -f $laneCount))
$lines.Add(("- dirty_worktrees={0}" -f $dirtyCount))
$lines.Add(('- managed_root=`{0}`' -f $resolvedManagedRoot))
$lines.Add("")
$lines.Add("## Worktrees")
$lines.Add("")
$lines.Add("| Repo | Branch | Role | Status | Managed | Last commit | Path |")
$lines.Add("|---|---|---|---|---|---|---|")

foreach ($result in ($results | Sort-Object Repo, Role, Branch, WorktreePath)) {
    $lines.Add(("| {0} | `{1}` | {2} | {3} | {4} | {5} | `{6}` |" -f $result.Repo, $result.Branch, $result.Role, $result.Status, $result.Managed, $result.LastCommitDate, $result.WorktreePath))
}

foreach ($repoGroup in ($results | Group-Object Repo | Sort-Object Name)) {
    $lines.Add("")
    $lines.Add(("## {0}" -f $repoGroup.Name))
    $lines.Add("")

    foreach ($item in ($repoGroup.Group | Sort-Object Role, Branch, WorktreePath)) {
        $lines.Add(("- `{0}` | branch=`{1}` | role={2} | status={3} | managed={4}" -f $item.WorktreePath, $item.Branch, $item.Role, $item.Status, $item.Managed))
    }
}

$report = $lines -join [Environment]::NewLine

if ($WriteReport) {
    $outDir = Split-Path -Parent $OutputPath
    if (-not (Test-Path $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }

    Set-Content -Path $OutputPath -Value $report
}

Write-Output $report
