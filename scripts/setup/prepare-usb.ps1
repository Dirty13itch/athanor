# Athanor USB Preparation Script
# Run this AFTER Ventoy has been installed on the USB drive.
# This copies the ISO and autoinstall configs to the correct locations.

param(
    [Parameter(Mandatory=$true)]
    [string]$UsbDrive  # e.g., "E:"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$downloadsDir = "$env:USERPROFILE\Downloads"

# Verify USB drive exists
if (-not (Test-Path $UsbDrive)) {
    Write-Error "Drive $UsbDrive does not exist."
    exit 1
}

# Check for Ventoy by volume label or existing ventoy directory
$driveLetter = $UsbDrive.TrimEnd(':\')
$vol = Get-Volume -DriveLetter $driveLetter -ErrorAction SilentlyContinue
if ($vol.FileSystemLabel -eq 'Ventoy' -or $vol.FileSystemLabel -eq 'ventoy' -or (Test-Path "$UsbDrive\ventoy")) {
    Write-Host "USB drive: $UsbDrive (Ventoy detected — label: '$($vol.FileSystemLabel)')"
} else {
    Write-Host "WARNING: $UsbDrive does not appear to have Ventoy installed (label: '$($vol.FileSystemLabel)')."
    Write-Host "Run Ventoy2Disk.exe first to install Ventoy on this USB drive."
    Write-Host "Then re-run this script."
    exit 1
}

# Copy ISO
$isoSource = "$downloadsDir\ubuntu-24.04.4-live-server-amd64.iso"
if (-not (Test-Path $isoSource)) {
    Write-Error "ISO not found at $isoSource. Download it first."
    exit 1
}

Write-Host "Copying Ubuntu ISO to USB (this will take a few minutes)..."
Copy-Item $isoSource "$UsbDrive\" -Force
Write-Host "  ISO copied."

# Create ventoy config directory and copy configs
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
Write-Host "Contents:"
Write-Host "  $UsbDrive\ubuntu-24.04.4-live-server-amd64.iso"
Write-Host "  $UsbDrive\ventoy\ventoy.json"
Write-Host "  $UsbDrive\ventoy\node1-autoinstall.yaml"
Write-Host "  $UsbDrive\ventoy\node2-autoinstall.yaml"
Write-Host ""
Write-Host "BOOT INSTRUCTIONS:"
Write-Host "  1. Plug USB into node"
Write-Host "  2. Boot from USB (F11 or F8 for boot menu)"
Write-Host "  3. Ventoy menu appears - select the Ubuntu ISO"
Write-Host "  4. When prompted, select the autoinstall config for this node"
Write-Host "     - node1-autoinstall.yaml for Node 1 (core)"
Write-Host "     - node2-autoinstall.yaml for Node 2 (interface)"
Write-Host "  5. Installation runs automatically (~5-10 minutes)"
Write-Host "  6. Remove USB when prompted, node reboots into Ubuntu"
Write-Host ""
Write-Host "After install, SSH in with:"
Write-Host '  ssh -i ~/.ssh/athanor_mgmt athanor@<node-ip>'
Write-Host ""
