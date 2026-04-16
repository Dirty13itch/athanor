param(
    [string]$Command = "echo CONNECTED"
)

$runtimeEnvPath = if ($env:ATHANOR_RUNTIME_ENV_FILE) {
    $env:ATHANOR_RUNTIME_ENV_FILE
} else {
    Join-Path $env:USERPROFILE ".athanor\runtime.env"
}

if (Test-Path $runtimeEnvPath) {
    foreach ($rawLine in Get-Content $runtimeEnvPath) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }
        if ($line.StartsWith("export ")) {
            $line = $line.Substring(7).Trim()
        }
        if (-not $line.Contains("=")) {
            continue
        }
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $currentValue = if ($key) { [Environment]::GetEnvironmentVariable($key) } else { $null }
        if ($key -and [string]::IsNullOrEmpty($currentValue)) {
            Set-Item -Path ("Env:{0}" -f $key) -Value $value
        }
    }
}

function Resolve-SshPath {
    $command = Get-Command ssh -ErrorAction SilentlyContinue
    if ($command -and $command.Source) {
        return $command.Source
    }
    foreach ($candidate in @(
        (Join-Path $env:WINDIR "System32\OpenSSH\ssh.exe"),
        (Join-Path $env:SystemRoot "System32\OpenSSH\ssh.exe"),
        "C:\Windows\System32\OpenSSH\ssh.exe"
    )) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    return $null
}

$vaultHost = if ($env:ATHANOR_VAULT_HOST) { $env:ATHANOR_VAULT_HOST } else { "192.168.1.203" }
$vaultUser = if ($env:ATHANOR_VAULT_USER) { $env:ATHANOR_VAULT_USER } else { "root" }
$vaultPassword = if ($env:ATHANOR_VAULT_PASSWORD) { $env:ATHANOR_VAULT_PASSWORD } elseif ($env:VAULT_SSH_PASSWORD) { $env:VAULT_SSH_PASSWORD } else { "" }

$keyCandidates = @(
    $env:ATHANOR_VAULT_KEY_PATH,
    $env:VAULT_SSH_KEY_PATH,
    (Join-Path $env:USERPROFILE ".ssh\id_ed25519"),
    (Join-Path $env:USERPROFILE ".ssh\athanor_mgmt")
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

$plink = Get-Command plink -ErrorAction SilentlyContinue
if ($plink -and $vaultPassword) {
    & plink -ssh -l $vaultUser -pw $vaultPassword -batch $vaultHost $Command
    exit $LASTEXITCODE
}

$sshPath = Resolve-SshPath
if (-not $sshPath) {
    Write-Host "ERROR: No SSH client is available."
    exit 1
}

foreach ($keyPath in $keyCandidates) {
    & $sshPath -i $keyPath -o BatchMode=yes -o ConnectTimeout=5 "$vaultUser@$vaultHost" $Command
    if ($LASTEXITCODE -eq 0) {
        exit 0
    }
}

& $sshPath -o BatchMode=yes -o ConnectTimeout=5 "$vaultUser@$vaultHost" $Command
if ($LASTEXITCODE -eq 0) {
    exit 0
}

Write-Host "ERROR: No vault SSH credential succeeded."
Write-Host "Set ATHANOR_VAULT_PASSWORD or ATHANOR_VAULT_KEY_PATH, or ensure a working key exists under $env:USERPROFILE\.ssh."
exit 1
