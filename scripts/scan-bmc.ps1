$Target = "192.168.1.216"
$Ports = @(22, 80, 443, 623, 5900, 8080)
$Timeout = 1000

Write-Host "Scanning $Target..."
foreach ($p in $Ports) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $r = $c.BeginConnect($Target, $p, $null, $null)
        $w = $r.AsyncWaitHandle.WaitOne($Timeout, $false)
        if ($w -and $c.Connected) {
            Write-Host "  Port $p OPEN"
        } else {
            Write-Host "  Port $p closed"
        }
        $c.Close()
    } catch {
        Write-Host "  Port $p error: $_"
    }
}
