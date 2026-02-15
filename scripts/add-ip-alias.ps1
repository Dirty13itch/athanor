# Add a secondary IP on the Wi-Fi adapter to reach Node 2 (10.10.10.10/24)
$adapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.Name -like '*Wi-Fi*' }
if (-not $adapter) {
    $adapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1
}
Write-Host "Using adapter: $($adapter.Name) ($($adapter.InterfaceAlias))"

# Check if already added
$existing = Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress '10.10.10.2' -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "10.10.10.2 already assigned"
} else {
    New-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress '10.10.10.2' -PrefixLength 24 -SkipAsSource $true
    Write-Host "Added 10.10.10.2/24 to $($adapter.Name)"
}

# Test connectivity
Write-Host "Pinging 10.10.10.10..."
Test-Connection -ComputerName 10.10.10.10 -Count 2 -TimeoutSeconds 2
