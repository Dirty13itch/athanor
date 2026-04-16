# Ventoy may have changed the drive letter after formatting
Get-Volume | Where-Object { $_.DriveType -eq 'Removable' } | Format-Table DriveLetter, FileSystemLabel, Size, SizeRemaining -AutoSize
Write-Host ""

# Check each removable drive for ventoy
foreach ($letter in @('E','F','G','H','I','J','K')) {
    $path = "${letter}:\ventoy"
    if (Test-Path "${letter}:\") {
        $label = (Get-Volume -DriveLetter $letter -ErrorAction SilentlyContinue).FileSystemLabel
        if ($label -eq 'Ventoy' -or $label -eq 'ventoy' -or (Test-Path $path)) {
            Write-Host "FOUND: Drive ${letter}: label='$label'"
        }
    }
}
