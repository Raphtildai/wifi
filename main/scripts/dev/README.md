
# Hostapd Wi-Fi Access Point Setup (Test Mode)

This setup allows you to run a temporary Wi-Fi Access Point using `hostapd`, `dnsmasq`, and shell scripts.
Useful for development and testing.

## 🔧 Requirements

- A Linux machine with a wireless interface that supports AP mode
- Packages:
  - `hostapd`
  - `dnsmasq`
  - `iptables`
  - `nmcli`
  - `wpa_supplicant`

## Installing the packages
  ```bash
  sudo apt update
  sudo apt install hostapd dnsmasq iptables wireless-tools net-tools -y
  ```

## 📁 Files

- `/etc/hostapd-test.env`: Environment configuration
- `hostapd_test.sh`: Starts and stops hostapd with a given config
- `run_ap.sh`: Main script to bring up AP, configure networking, and handle cleanup

## ✅ Installation Steps

### 1. Create Environment Config

```bash
sudo tee /etc/hostapd-test.env > /dev/null <<'EOF'
# Hostapd test environment config
INTERFACE=$(iw dev | awk '$1=="Interface"{print $2}')
AP_IP="192.168.50.1"
NETMASK="255.255.255.0"
SSID="DevTestNetwork"
PASSPHRASE="mySecureAP123"
CHANNEL=6
DHCP_RANGE_START="192.168.50.10"
DHCP_RANGE_END="192.168.50.100"
DHCP_LEASE_TIME="12h"
INTERNET_IFACE="eth0"
EOF
```

### 2. Add the Scripts

Place `hostapd_test.sh` and `run_ap.sh` in a safe directory (e.g., `~/wifi-test/`) and make them executable:

```bash
chmod +x hostapd_test.sh run_ap.sh
```
```bash
#!/bin/bash

set -euo pipefail

ENV_FILE="/etc/hostapd-test.env"
HOSTAPD_CONF="/tmp/test_ap.conf"
DNSMASQ_CONF="/tmp/test_dnsmasq.conf"
LOG_FILE="/var/log/test_ap.log"

# Load environment variables
if [[ -f "$ENV_FILE" ]]; then
    source "$ENV_FILE"
else
    echo "[-] Environment file not found at $ENV_FILE"
    exit 1
fi

# Validate required environment variables
REQUIRED_VARS=(INTERFACE AP_IP NETMASK SSID PASSPHRASE CHANNEL DHCP_RANGE_START DHCP_RANGE_END DHCP_LEASE_TIME)
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo "[-] Missing required environment variable: $var"
        exit 1
    fi
done

# Trap to clean up
cleanup() {
    echo "[*] Cleaning up..."
    sudo pkill hostapd || true
    sudo pkill dnsmasq || true
    sudo iptables -t nat -D POSTROUTING -o "$DEFAULT_IFACE" -j MASQUERADE || true
    sudo iptables -D FORWARD -i "$INTERFACE" -j ACCEPT || true
    sudo iptables -D FORWARD -o "$INTERFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT || true
    sudo ip link set "$INTERFACE" down
    sudo systemctl start NetworkManager.service || true
    sudo nmcli radio wifi on || true
    sudo systemctl start wpa_supplicant.service || true
    echo "[*] Cleanup done."
}
trap cleanup EXIT

echo "[+] Checking dependencies..."
for cmd in hostapd dnsmasq ip iptables; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "[-] Required command '$cmd' is not installed."
        exit 1
    fi
done

echo "[+] Checking if interface $INTERFACE exists..."
if ! ip link show "$INTERFACE" &>/dev/null; then
    echo "[-] Interface $INTERFACE not found. Check your wireless device name."
    exit 1
fi

echo "[+] Stopping interfering services..."
sudo systemctl stop NetworkManager.service || true
sudo nmcli radio wifi off || true
sudo systemctl stop wpa_supplicant.service || true

echo "[+] Configuring interface $INTERFACE..."
sudo ip link set "$INTERFACE" down
sudo ip addr flush dev "$INTERFACE"
sudo ip addr add "$AP_IP/$NETMASK" dev "$INTERFACE"
sudo ip link set "$INTERFACE" up

echo "[+] Generating hostapd config at $HOSTAPD_CONF..."
cat <<EOF | sudo tee "$HOSTAPD_CONF" > /dev/null
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
logger_syslog=-1
logger_syslog_level=0
logger_stdout=-1
logger_stdout_level=0
EOF

echo "[+] Generating dnsmasq config at $DNSMASQ_CONF..."
cat <<EOF | sudo tee "$DNSMASQ_CONF" > /dev/null
interface=$INTERFACE
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,$DHCP_LEASE_TIME
dhcp-option=3,$AP_IP
dhcp-option=6,8.8.8.8,8.8.4.4
log-queries
log-dhcp
EOF

echo "[+] Restarting dnsmasq..."
sudo pkill dnsmasq || true
sudo dnsmasq -C "$DNSMASQ_CONF" --log-facility="$LOG_FILE"

echo "[+] Enabling IP forwarding and setting up NAT..."
sudo sysctl -w net.ipv4.ip_forward=1
DEFAULT_IFACE=$(ip route | awk '/default/ {print $5}' | head -n1)
if [[ -z "$DEFAULT_IFACE" ]]; then
    echo "[-] Could not detect default internet interface."
    exit 1
fi

sudo iptables -t nat -A POSTROUTING -o "$DEFAULT_IFACE" -j MASQUERADE
sudo iptables -A FORWARD -i "$INTERFACE" -j ACCEPT
sudo iptables -A FORWARD -o "$INTERFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT

echo "[+] Starting hostapd..."
sudo hostapd "$HOSTAPD_CONF" -dd | tee -a "$LOG_FILE"
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

## 📓 Notes

- Run with `sudo`
- Works best on systems where `NetworkManager` is used and not interfering with manual configs
- For production, consider writing systemd service units

---

© 2025 — Raphael Kipchirchir
