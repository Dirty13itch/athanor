param(
    [string]$Target,
    [int[]]$Ports = @(623, 161, 69, 5353)
)

Write-Host "UDP probe on $Target..."
foreach ($p in $Ports) {
    try {
        $udp = New-Object System.Net.Sockets.UdpClient
        $udp.Client.ReceiveTimeout = 1000
        $udp.Client.SendTimeout = 1000

        # IPMI Get Channel Auth request (for port 623)
        if ($p -eq 623) {
            # RMCP + ASF ping
            $bytes = [byte[]]@(0x06, 0x00, 0xff, 0x06, 0x00, 0x00, 0x11, 0xbe, 0x80, 0x00, 0x00, 0x00)
            $udp.Send($bytes, $bytes.Length, $Target, $p) | Out-Null
        } else {
            $bytes = [byte[]]@(0x00)
            $udp.Send($bytes, $bytes.Length, $Target, $p) | Out-Null
        }

        $ep = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any, 0)
        try {
            $recv = $udp.Receive([ref]$ep)
            Write-Host "  Port $p RESPONDED ($($recv.Length) bytes)"
        } catch [System.Net.Sockets.SocketException] {
            $code = $_.Exception.SocketErrorCode
            if ($code -eq 'ConnectionReset') {
                Write-Host "  Port $p CLOSED (ICMP unreachable)"
            } else {
                Write-Host "  Port $p TIMEOUT (no response - may be open or filtered)"
            }
        }
        $udp.Close()
    } catch {
        Write-Host "  Port $p error: $_"
    }
}
