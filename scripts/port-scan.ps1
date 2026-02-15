param(
    [string]$Target,
    [int[]]$Ports = @(22, 80, 443, 623, 5900, 5901, 8080, 8443, 50000),
    [int]$Timeout = 500
)

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
