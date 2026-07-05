# Check services status
$ports = @(8000, 8001, 8002, 8003)
$results = @()

foreach ($port in $ports) {
    $result = @{
        Port = $port
        Status = "Not responding"
    }
    
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("localhost", $port)
        $tcp.Close()
        $result.Status = "OK"
    } catch {
        $result.Status = "Down"
    }
    
    $results += $result
}

$results | Format-Table -AutoSize
