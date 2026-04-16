#!/bin/bash
# Athanor Post-Install Audit Script
# Run this on a freshly installed Ubuntu node to get full hardware inventory.
# Usage: ssh athanor@<node-ip> 'bash -s' < post-install-audit.sh

set -euo pipefail

echo "============================================"
echo "ATHANOR HARDWARE AUDIT — $(hostname)"
echo "Date: $(date -Iseconds)"
echo "============================================"
echo ""

echo "=== SYSTEM ==="
sudo dmidecode -t system 2>/dev/null | grep -E 'Manufacturer|Product|Serial|UUID' || echo "dmidecode not available"
echo ""

echo "=== MOTHERBOARD ==="
sudo dmidecode -t baseboard 2>/dev/null | grep -E 'Manufacturer|Product|Version|Serial' || echo "N/A"
echo ""

echo "=== BIOS ==="
sudo dmidecode -t bios 2>/dev/null | grep -E 'Vendor|Version|Release|Date' || echo "N/A"
echo ""

echo "=== CPU ==="
lscpu | grep -E 'Model name|Socket|Core|Thread|CPU MHz|CPU max|Architecture|Virtualization|L1|L2|L3|Flags' || cat /proc/cpuinfo | head -30
echo ""

echo "=== MEMORY SUMMARY ==="
free -h
echo ""
echo "=== MEMORY DIMMS ==="
sudo dmidecode -t memory 2>/dev/null | grep -E 'Size|Type|Speed|Manufacturer|Part|Locator|Form' | grep -v "No Module" || echo "N/A"
echo ""

echo "=== GPU / PCI VIDEO ==="
lspci | grep -iE 'VGA|3D|Display' || echo "No GPU detected"
echo ""
echo "=== GPU DETAILS ==="
lspci -v | grep -A 12 -iE 'VGA|3D|Display' || echo "N/A"
echo ""
if command -v nvidia-smi &>/dev/null; then
    echo "=== NVIDIA-SMI ==="
    nvidia-smi || echo "nvidia-smi failed"
    echo ""
fi

echo "=== STORAGE ==="
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL,SERIAL,ROTA,TRAN
echo ""
echo "=== NVME DEVICES ==="
sudo nvme list 2>/dev/null || echo "nvme-cli not available or no NVMe devices"
echo ""
echo "=== SMART STATUS ==="
for dev in $(lsblk -dno NAME | grep -E '^sd|^nvme'); do
    echo "--- /dev/$dev ---"
    sudo smartctl -i /dev/$dev 2>/dev/null | grep -E 'Model|Serial|Capacity|Rotation|Form' || echo "N/A"
done
echo ""

echo "=== NETWORK ==="
ip addr show | grep -E 'state|inet ' | grep -v '127.0.0.1'
echo ""
echo "=== NETWORK HARDWARE ==="
lspci | grep -iE 'Ethernet|Network|Wi-Fi' || echo "N/A"
echo ""

echo "=== PCI DEVICES (ALL) ==="
lspci
echo ""

echo "=== USB CONTROLLERS ==="
lspci | grep -i USB
echo ""

echo "=== IPMI ==="
if command -v ipmitool &>/dev/null; then
    sudo ipmitool lan print 1 2>/dev/null | grep -E 'IP Address|MAC|Source' || echo "IPMI not configured or not available"
else
    echo "ipmitool not installed"
fi
echo ""

echo "=== OS ==="
cat /etc/os-release | grep -E 'PRETTY_NAME|VERSION'
uname -r
echo ""

echo "============================================"
echo "AUDIT COMPLETE — $(hostname)"
echo "============================================"
