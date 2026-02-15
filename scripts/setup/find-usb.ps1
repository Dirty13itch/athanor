Get-Volume | Where-Object { $_.DriveType -eq 'Removable' } | Format-Table DriveLetter, FileSystemLabel, Size, SizeRemaining -AutoSize
