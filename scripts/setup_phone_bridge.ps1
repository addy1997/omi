# Bridges Windows LAN ports -> WSL2 so your phone can reach Omi.
# Re-run this if the WSL2 IP changes (after a reboot). Must run as Administrator.

$wslIp = "172.27.198.237"   # WSL2 IP (from `hostname -I` in WSL)
$ports = @(9000, 5173)       # platform, dashboard

foreach ($p in $ports) {
    # remove any stale mapping first (idempotent)
    netsh interface portproxy delete v4tov4 listenport=$p listenaddress=0.0.0.0 2>$null
    # forward Windows:p -> WSL2:p
    netsh interface portproxy add v4tov4 listenport=$p listenaddress=0.0.0.0 connectport=$p connectaddress=$wslIp
    # open the Windows firewall for inbound p
    netsh advfirewall firewall delete rule name="Omi-$p" 2>$null | Out-Null
    netsh advfirewall firewall add rule name="Omi-$p" dir=in action=allow protocol=TCP localport=$p | Out-Null
    Write-Host "Bridged port $p  ->  ${wslIp}:$p  (firewall opened)"
}

Write-Host ""
Write-Host "Active port proxies:"
netsh interface portproxy show v4tov4
Write-Host ""
Write-Host "Done. On your phone (same Wi-Fi) open:  http://192.168.1.143:5173"
