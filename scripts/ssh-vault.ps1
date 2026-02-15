param(
    [string]$Command = "echo CONNECTED"
)

# Use plink (PuTTY) if available, otherwise fall back to expect-like approach
$plink = Get-Command plink -ErrorAction SilentlyContinue
if ($plink) {
    & plink -ssh -l root -pw "Hockey1298" -batch 192.168.1.203 $Command
} else {
    Write-Host "plink not found. Trying ssh with key..."
    # Try reinstalling the key
    $keyPath = "$env:USERPROFILE\.ssh\id_ed25519"
    if (Test-Path $keyPath) {
        & ssh -i $keyPath -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@192.168.1.203 $Command
    } else {
        Write-Host "ERROR: No ssh key found and no plink available."
        Write-Host "Install PuTTY/plink or use: ssh root@192.168.1.203 (will prompt for password)"
    }
}
