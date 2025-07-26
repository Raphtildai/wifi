
# Hostapd Wi-Fi Access Point Setup (Production Version)

This setup allows you to run a production-grade Wi-Fi Access Point using `hostapd`, `dnsmasq`, and shell scripts.
Designed for stable and reliable use in live environments.

## 🔧 Requirements

- A Linux machine with a wireless interface that supports AP mode
- Packages:
  - `hostapd`
  - `dnsmasq`
  - `iptables`
  - `nmcli`
  - `wpa_supplicant`

## 🔧 Installing the packages
  ```bash
  sudo apt update
  sudo apt install hostapd dnsmasq iptables wireless-tools net-tools -y
  ```

## 📁 Files

- `/etc/hostapd-prod.env`: Environment configuration for production
-  `start-ap.sh`: Starts and stops hostapd with a given config
- `run_ap.sh`: Main script to bring up AP, configure networking, and handle cleanup

## ✅ Installation Steps

### 1. Create Environment Config

```bash
sudo tee /etc/hostapd-prod.env > /dev/null <<'EOF'
# Hostapd production environment config
INTERFACE=$(iw dev | awk '$1=="Interface"{print $2}')
AP_IP="192.168.50.1"
NETMASK="255.255.255.0"
SSID="ProdNetwork"
PASSPHRASE="YourStrongSecurePassphrase"
CHANNEL=6
DHCP_RANGE_START="192.168.50.10"
DHCP_RANGE_END="192.168.50.100"
DHCP_LEASE_TIME="12h"
INTERNET_IFACE="eth0"
EOF
```

### 2. Add the Scripts

Place `start-ap.sh` and `run_ap.sh` in a secure directory (e.g., `~/wifi-prod/`) and make them executable:

```bash
chmod +x start-ap.sh run_ap.sh
```
### Contents of run_ap.sh:
```bash
#!/bin/bash
set -euo pipefail

# Load environment variables
ENV_FILE="/etc/hostapd-prod.env"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE" || { echo "❌ Env file not found: $ENV_FILE"; exit 1; }

REQUIRED_VARS=(INTERFACE AP_IP NETMASK SSID PASSPHRASE CHANNEL DHCP_RANGE_START DHCP_RANGE_END DHCP_LEASE_TIME)
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo "❌ Missing required variable: $var"
        exit 1
    fi
done

# Constants
HOSTAPD_CONF="/etc/hostapd-prod/hostapd.conf"
DNSMASQ_CONF="/etc/hostapd-prod/dnsmasq.conf"
LOG_FILE="/var/log/prod_ap.log"

# Clean up on exit
cleanup() {
    echo "[INFO] Cleaning up services..."
    pkill hostapd || true
    pkill dnsmasq || true
    iptables -t nat -D POSTROUTING -o "$DEFAULT_IFACE" -j MASQUERADE || true
    iptables -D FORWARD -i "$INTERFACE" -j ACCEPT || true
    iptables -D FORWARD -o "$INTERFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT || true
    ip link set "$INTERFACE" down || true
}
trap cleanup EXIT

# Stop conflicting services
echo "[INFO] Stopping NetworkManager and wpa_supplicant..."
systemctl stop NetworkManager.service || true
nmcli radio wifi off || true
systemctl stop wpa_supplicant.service || true

# Network config
echo "[INFO] Configuring interface $INTERFACE with IP $AP_IP/$NETMASK..."
ip link set "$INTERFACE" down
ip addr flush dev "$INTERFACE"
ip addr add "$AP_IP/$NETMASK" dev "$INTERFACE"
ip link set "$INTERFACE" up

# Write hostapd.conf
mkdir -p /etc/hostapd-prod
cat <<EOF > "$HOSTAPD_CONF"
interface=$INTERFACE
driver=nl80211
ssid=$SSID
channel=$CHANNEL
hw_mode=g
auth_algs=1
wmm_enabled=1
wpa=2
wpa_passphrase=$PASSPHRASE
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

# Write dnsmasq.conf
cat <<EOF > "$DNSMASQ_CONF"
interface=$INTERFACE
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,$DHCP_LEASE_TIME
dhcp-option=3,$AP_IP
dhcp-option=6,8.8.8.8,8.8.4.4
EOF

# Start dnsmasq
echo "[INFO] Starting dnsmasq..."
dnsmasq -C "$DNSMASQ_CONF" --log-facility="$LOG_FILE"

# Enable IP forwarding and set up NAT
echo "[INFO] Enabling NAT and packet forwarding..."
sysctl -w net.ipv4.ip_forward=1
DEFAULT_IFACE=$(ip route | awk '/default/ {print $5}' | head -n1)
iptables -t nat -A POSTROUTING -o "$DEFAULT_IFACE" -j MASQUERADE
iptables -A FORWARD -i "$INTERFACE" -j ACCEPT
iptables -A FORWARD -o "$INTERFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT

# Start hostapd
echo "[INFO] Starting hostapd..."
hostapd "$HOSTAPD_CONF" >> "$LOG_FILE" 2>&1
```

### 3. Run the AP Setup

```bash
sudo ./run_ap.sh
```

### 4. Stop the AP

Once you're done, press `Enter` in the terminal running hostapd to trigger cleanup.

## 🧹 What Cleanup Does

- Stops `hostapd`, `dnsmasq`
- Resets interface IP and services
- Removes NAT and iptables rules
- Restarts `NetworkManager` and `wpa_supplicant`

## Checking logs
```bash
sudo tail -f /var/log/hotspot/hotspot.log
sudo tail -f /var/log/hotspot/hostapd.log
```

## Fixing driver issues
```bash
sudo modprobe -r iwlwifi && sudo modprobe iwlwifi
```

## 📓 Notes

- Run with `sudo`
- Designed for production environments — more reliable and secure than test setups
- Consider creating systemd service units for automatic startup and better management
- Store your environment and config files securely and restrict permissions
---

© 2025 — Raphael Kipchirchir 
