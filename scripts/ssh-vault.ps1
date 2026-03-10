param(
    [string]$Command = "echo CONNECTED"
)

$vaultHost = if ($env:ATHANOR_VAULT_HOST) { $env:ATHANOR_VAULT_HOST } else { "192.168.1.203" }
$vaultUser = if ($env:ATHANOR_VAULT_USER) { $env:ATHANOR_VAULT_USER } else { "root" }
$vaultPassword = if ($env:ATHANOR_VAULT_PASSWORD) { $env:ATHANOR_VAULT_PASSWORD } elseif ($env:VAULT_SSH_PASSWORD) { $env:VAULT_SSH_PASSWORD } else { "" }
$vaultKeyPath = if ($env:ATHANOR_VAULT_KEY_PATH) { $env:ATHANOR_VAULT_KEY_PATH } elseif ($env:VAULT_SSH_KEY_PATH) { $env:VAULT_SSH_KEY_PATH } else { "$env:USERPROFILE\.ssh\id_ed25519" }

# Use plink (PuTTY) if available, otherwise fall back to expect-like approach
$plink = Get-Command plink -ErrorAction SilentlyContinue
if ($plink -and $vaultPassword) {
    & plink -ssh -l $vaultUser -pw $vaultPassword -batch $vaultHost $Command
} else {
    if ($plink -and -not $vaultPassword) {
        Write-Host "plink found but no vault password set. Trying key-based ssh..."
    } else {
        Write-Host "plink not found. Trying ssh with key..."
    }
    if (Test-Path $vaultKeyPath) {
        & ssh -i $vaultKeyPath -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$vaultUser@$vaultHost" $Command
    } else {
        Write-Host "ERROR: No vault SSH credential available."
        Write-Host "Set ATHANOR_VAULT_PASSWORD or ATHANOR_VAULT_KEY_PATH, or use: ssh $vaultUser@$vaultHost"
    }
}
