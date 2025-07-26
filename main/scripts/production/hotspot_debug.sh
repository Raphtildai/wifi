#!/bin/bash
# hotspot_debug.sh

# Check wireless interface
echo "=== Wireless Interface Status ==="
iwconfig wlo1
iw dev wlo1 info
echo ""

# Check hostapd
echo "=== Hostapd Status ==="
sudo systemctl status hostapd
pgrep -fa hostapd
sudo ls -la /var/run/hostapd
echo ""

# Check dnsmasq
echo "=== Dnsmasq Status ==="
sudo systemctl status dnsmasq
pgrep -fa dnsmasq
echo ""

# Check logs
echo "=== Recent Logs ==="
sudo tail -20 /var/log/syslog | grep -E 'hostapd|dnsmasq'
sudo journalctl -u hostapd -n 20 --no-pager
echo ""

# Check kernel messages
echo "=== Kernel Messages ==="
dmesg | tail -20
echo ""

# Check network configuration
echo "=== Network Config ==="
ip addr show wlo1
sudo iptables -t nat -L -v
echo ""

# Verify packages
echo "=== Package Versions ==="
dpkg -l hostapd dnsmasq iw