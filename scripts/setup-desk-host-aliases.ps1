$ErrorActionPreference = "Stop"

$hostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"
$aliases = [ordered]@{
    "athanor.local" = "192.168.1.189"
    "dev.athanor.local" = "192.168.1.189"
    "vault.athanor.local" = "192.168.1.203"
    "interface.athanor.local" = "192.168.1.225"
    "core.athanor.local" = "192.168.1.244"
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    throw "Run this script from an elevated PowerShell session or via 'sudo powershell -ExecutionPolicy Bypass -File C:\Athanor\scripts\setup-desk-host-aliases.ps1'."
}

$existingLines = @()
if (Test-Path -LiteralPath $hostsPath) {
    $existingLines = Get-Content -LiteralPath $hostsPath
}

$managedStart = "# >>> Athanor command-center aliases >>>"
$managedEnd = "# <<< Athanor command-center aliases <<<"

$filteredLines = New-Object System.Collections.Generic.List[string]
$insideManagedBlock = $false

foreach ($line in $existingLines) {
    if ($line -eq $managedStart) {
        $insideManagedBlock = $true
        continue
    }
    if ($line -eq $managedEnd) {
        $insideManagedBlock = $false
        continue
    }
    if ($insideManagedBlock) {
        continue
    }
    $filteredLines.Add($line)
}

$managedLines = New-Object System.Collections.Generic.List[string]
$managedLines.Add($managedStart)
foreach ($hostname in $aliases.Keys) {
    $managedLines.Add(("{0}`t{1}" -f $aliases[$hostname], $hostname))
}
$managedLines.Add($managedEnd)

if ($filteredLines.Count -gt 0 -and $filteredLines[$filteredLines.Count - 1] -ne "") {
    $filteredLines.Add("")
}
foreach ($line in $managedLines) {
    $filteredLines.Add($line)
}

Set-Content -LiteralPath $hostsPath -Value $filteredLines -Encoding ASCII

Write-Host "Updated $hostsPath with Athanor command-center aliases:"
foreach ($hostname in $aliases.Keys) {
    Write-Host ("  {0} -> {1}" -f $hostname, $aliases[$hostname])
}
