Get-Disk | Where-Object { $_.BusType -eq 'USB' } | ForEach-Object {
    $disk = $_
    Write-Host "=== Disk $($disk.Number): $($disk.FriendlyName) ($([math]::Round($disk.Size / 1GB, 1)) GB) ==="
    Get-Partition -DiskNumber $disk.Number | ForEach-Object {
        $vol = Get-Volume -Partition $_ -ErrorAction SilentlyContinue
        if ($vol) {
            Write-Host "  Partition $($_.PartitionNumber): Drive $($vol.DriveLetter): '$($vol.FileSystemLabel)' ($([math]::Round($_.Size / 1GB, 1)) GB)"
        } else {
            Write-Host "  Partition $($_.PartitionNumber): No volume ($([math]::Round($_.Size / 1GB, 1)) GB)"
        }
    }
    Write-Host ""
}
