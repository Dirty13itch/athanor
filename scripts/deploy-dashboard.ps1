[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$DashboardArgs
)

$ErrorActionPreference = "Stop"

function ConvertTo-GitBashPath {
    param([string]$PathText)

    $resolved = (Resolve-Path -LiteralPath $PathText).Path
    if ($resolved -match '^[A-Za-z]:\\') {
        $drive = $resolved.Substring(0, 1).ToLowerInvariant()
        $rest = $resolved.Substring(2).Replace('\', '/')
        return "/$drive$rest"
    }

    return $resolved.Replace('\', '/')
}

function Get-GitBashExe {
    $candidates = @(
        "C:\Program Files\Git\bin\bash.exe"
        "C:\Program Files\Git\usr\bin\bash.exe"
        "C:\Program Files (x86)\Git\bin\bash.exe"
        "C:\Program Files (x86)\Git\usr\bin\bash.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "Git Bash was not found. Install Git for Windows or run deploy-dashboard.sh from a Bash shell directly."
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$bashExe = Get-GitBashExe
$repoBashPath = ConvertTo-GitBashPath -PathText $repoRoot
$scriptBashPath = "$repoBashPath/scripts/deploy-dashboard.sh"

Write-Host "Using Git Bash: $bashExe"
Write-Host "Launching: $scriptBashPath $($DashboardArgs -join ' ')"

& $bashExe $scriptBashPath @DashboardArgs
exit $LASTEXITCODE
