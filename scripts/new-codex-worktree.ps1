[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetRepo,
    [Parameter(Mandatory = $true)]
    [string]$Task,
    [string]$BaseRef,
    [string]$CodexHome = (Join-Path $env:USERPROFILE ".codex"),
    [string]$BranchPrefix = "codex"
)

$ErrorActionPreference = "Stop"

function Assert-GitRepo {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        throw "Repo path not found: $Path"
    }

    $inside = @(& git -C $Path rev-parse --is-inside-work-tree 2>$null)
    if ($LASTEXITCODE -ne 0 -or ($inside -join "").Trim() -ne "true") {
        throw "Not a git repo: $Path"
    }
}

function Get-Slug {
    param(
        [string]$Value
    )

    $normalized = $Value.ToLowerInvariant()
    $normalized = [regex]::Replace($normalized, "[^a-z0-9]+", "-")
    $normalized = $normalized.Trim("-")

    if ([string]::IsNullOrWhiteSpace($normalized)) {
        throw "Could not derive a slug from input: $Value"
    }

    return $normalized
}

function Test-BranchExists {
    param(
        [string]$RepoPath,
        [string]$BranchName
    )

    & git -C $RepoPath show-ref --verify --quiet ("refs/heads/" + $BranchName)
    return ($LASTEXITCODE -eq 0)
}

function Get-DirtyEntryCount {
    param(
        [string]$RepoPath
    )

    $statusLines = @(& git -C $RepoPath status --short 2>$null)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read git status for $RepoPath"
    }

    return $statusLines.Count
}

$resolvedRepo = (Resolve-Path $TargetRepo).Path
Assert-GitRepo -Path $resolvedRepo

$repoName = Get-Slug -Value (Split-Path -Leaf $resolvedRepo)
$taskSlug = Get-Slug -Value $Task
$worktreesRoot = Join-Path $CodexHome "worktrees"
$repoWorktreeRoot = Join-Path $worktreesRoot $repoName

if (-not $BaseRef) {
    $currentBranch = @(& git -C $resolvedRepo branch --show-current 2>$null)
    if ($LASTEXITCODE -eq 0 -and $currentBranch.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($currentBranch[0])) {
        $BaseRef = $currentBranch[0].Trim()
    } else {
        $BaseRef = "HEAD"
    }
}

$laneSlug = $taskSlug
$suffix = 2
while ($true) {
    $branchName = "{0}/{1}-{2}" -f $BranchPrefix, $repoName, $laneSlug
    $worktreePath = Join-Path $repoWorktreeRoot $laneSlug

    if ((-not (Test-Path $worktreePath)) -and (-not (Test-BranchExists -RepoPath $resolvedRepo -BranchName $branchName))) {
        break
    }

    $laneSlug = "{0}-{1}" -f $taskSlug, $suffix
    $suffix++
}

$dirtyEntries = Get-DirtyEntryCount -RepoPath $resolvedRepo

if ($PSCmdlet.ShouldProcess($worktreePath, "Create worktree $branchName from $BaseRef")) {
    if (-not (Test-Path $repoWorktreeRoot)) {
        New-Item -ItemType Directory -Path $repoWorktreeRoot -Force | Out-Null
    }

    & git -C $resolvedRepo worktree add $worktreePath -b $branchName $BaseRef
    if ($LASTEXITCODE -ne 0) {
        throw "git worktree add failed for $resolvedRepo"
    }
}

Write-Output ("repo=" + $resolvedRepo)
Write-Output ("task=" + $Task)
Write-Output ("base_ref=" + $BaseRef)
Write-Output ("branch=" + $branchName)
Write-Output ("worktree=" + $worktreePath)
Write-Output ("source_repo_dirty_entries=" + $dirtyEntries)

if ($dirtyEntries -gt 0) {
    Write-Output "note=The source repo has uncommitted changes. The new lane was created from committed history only."
}
