# Scan 192.168.1.1-254 for SSH (port 22) to find new Ubuntu nodes
$timeout = 300

Write-Host "Scanning 192.168.1.1-254 for SSH (port 22)..."
foreach ($i in 1..254) {
    $ip = "192.168.1.$i"
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $r = $c.BeginConnect($ip, 22, $null, $null)
        $w = $r.AsyncWaitHandle.WaitOne($timeout, $false)
        if ($w -and $c.Connected) {
            Write-Host "  $ip - SSH OPEN"
        }
        $c.Close()
    } catch {}
}
Write-Host "Scan complete."
