$scriptDir = "C:\Users\Shaun\athanor\scripts\setup"

# Find the Ventoy drive
$ventoyDrive = $null
foreach ($letter in @('D','E','F','G','H','I','J','K')) {
    $vol = Get-Volume -DriveLetter $letter -ErrorAction SilentlyContinue
    if ($vol -and $vol.FileSystemLabel -eq 'Ventoy') {
        $ventoyDrive = "${letter}:"
        break
    }
}

if (-not $ventoyDrive) {
    Write-Error "No Ventoy drive found. Plug in the USB."
    exit 1
}

Write-Host "Found Ventoy drive: $ventoyDrive"

# Verify ISO is there
if (Test-Path "$ventoyDrive\ubuntu-24.04.4-live-server-amd64.iso") {
    $size = (Get-Item "$ventoyDrive\ubuntu-24.04.4-live-server-amd64.iso").Length
    Write-Host "ISO present: $([math]::Round($size / 1GB, 2)) GB"
} else {
    Write-Host "WARNING: ISO not found on drive!"
}

# Copy fixed ventoy.json
Copy-Item "$scriptDir\ventoy\ventoy.json" "$ventoyDrive\ventoy\ventoy.json" -Force
Write-Host "Fixed ventoy.json copied."

# Verify contents
Write-Host ""
Write-Host "USB contents:"
Get-ChildItem "$ventoyDrive\" -Recurse -File | ForEach-Object {
    Write-Host "  $($_.FullName) ($([math]::Round($_.Length / 1MB, 1)) MB)"
}
