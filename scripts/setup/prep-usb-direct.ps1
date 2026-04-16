$UsbDrive = "I:"
$scriptDir = "C:\Users\Shaun\athanor\scripts\setup"
$downloadsDir = "$env:USERPROFILE\Downloads"

# Copy ISO
$isoSource = "$downloadsDir\ubuntu-24.04.4-live-server-amd64.iso"
if (-not (Test-Path $isoSource)) {
    Write-Error "ISO not found at $isoSource"
    exit 1
}

Write-Host "Copying Ubuntu ISO to USB (this will take a few minutes)..."
Copy-Item $isoSource "$UsbDrive\" -Force
Write-Host "  ISO copied."

# Create ventoy config directory
$ventoyDir = "$UsbDrive\ventoy"
if (-not (Test-Path $ventoyDir)) {
    New-Item -ItemType Directory -Path $ventoyDir | Out-Null
}

# Copy ventoy.json
Copy-Item "$scriptDir\ventoy\ventoy.json" "$ventoyDir\ventoy.json" -Force
Write-Host "  ventoy.json copied."

# Copy autoinstall configs
Copy-Item "$scriptDir\node1-autoinstall.yaml" "$ventoyDir\node1-autoinstall.yaml" -Force
Copy-Item "$scriptDir\node2-autoinstall.yaml" "$ventoyDir\node2-autoinstall.yaml" -Force
Write-Host "  Autoinstall configs copied."

Write-Host ""
Write-Host "========================================="
Write-Host "USB DRIVE READY"
Write-Host "========================================="
Write-Host ""
Get-ChildItem "$UsbDrive\" -Recurse | ForEach-Object { Write-Host "  $($_.FullName)" }
