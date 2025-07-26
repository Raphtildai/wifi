#!/bin/bash
set -euo pipefail

mkdir -p /etc/hostapd-prod

# Enhanced logging function
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "${LOG_FILE:-/var/log/prod_ap.log}"
}

# Load environment
ENV_FILE="/etc/hostapd-prod.env"

if [[ -f "$ENV_FILE" ]]; then
    log "🔄 Loading environment from $ENV_FILE"
    source "$ENV_FILE"
else
    log "❌ Env file not found: $ENV_FILE"
    exit 1
fi

# Detect wireless interface
if [[ -z "${INTERFACE:-}" ]]; then
    INTERFACE=$(iw dev | awk '$1=="Interface"{print $2}' | head -n1)
    if [[ -z "$INTERFACE" ]]; then
        log "❌ Could not detect wireless interface."
        exit 1
    fi
    log "ℹ️ Using wireless interface: $INTERFACE"
fi

# Verify required variables
REQUIRED_VARS=(INTERFACE AP_IP NETMASK SSID PASSPHRASE CHANNEL DHCP_RANGE_START DHCP_RANGE_END DHCP_LEASE_TIME)
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        log "❌ Missing required variable: $var"
        exit 1
    fi
done

# Configuration files
HOSTAPD_CONF="/etc/hostapd-prod/hostapd.conf"
DNSMASQ_CONF="/etc/hostapd-prod/dnsmasq.conf"
LOG_FILE="/var/log/prod_ap.log"

# Detect default internet interface (preserve wired connection)
DEFAULT_IFACE=$(ip route | awk '/default/ {print $5}' | grep -v "$INTERFACE" | head -n1)
if [[ -z "$DEFAULT_IFACE" ]]; then
    log "❌ Could not determine default internet interface."
    exit 1
fi
log "ℹ️ Using default internet interface: $DEFAULT_IFACE"

# Cleanup function to restore state
cleanup() {
    log "🧹 Cleaning up services..."
    
    # Stop services
    sudo killall hostapd 2>/dev/null || true
    sudo killall dnsmasq 2>/dev/null || true
    
    # Restore iptables
    sudo iptables -t nat -D POSTROUTING -o "$DEFAULT_IFACE" -j MASQUERADE 2>/dev/null || true
    sudo iptables -D FORWARD -i "$INTERFACE" -j ACCEPT 2>/dev/null || true
    sudo iptables -D FORWARD -o "$INTERFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
    
    # Reset wireless interface
    sudo ip link set "$INTERFACE" down 2>/dev/null
    sudo ip addr flush dev "$INTERFACE" 2>/dev/null
    
    # Restore NetworkManager control if it's running
    if systemctl is-active --quiet NetworkManager; then
        log "🔄 Restoring NetworkManager control of $INTERFACE"
        sudo nmcli device set "$INTERFACE" managed yes 2>/dev/null || true
        sudo nmcli connection reload
    fi
    
    log "✅ Network services restored"
}
trap cleanup EXIT

# Configure wireless interface
log "📡 Configuring Wi-Fi interface..."

# Release interface from NetworkManager without stopping the service
if systemctl is-active --quiet NetworkManager; then
    log "🔧 Taking control of $INTERFACE from NetworkManager"
    sudo nmcli device set "$INTERFACE" managed no || {
        log "⚠️ Could not set interface to unmanaged, trying alternative approach"
        sudo systemctl stop NetworkManager
        sleep 2
    }
fi

sudo rfkill unblock wifi
sudo ip link set "$INTERFACE" down
sudo ip addr flush dev "$INTERFACE"

# Convert netmask to CIDR
netmask_to_cidr() {
    local nbits=0
    local IFS=.
    for octet in $1; do
        case $octet in
            255) let nbits+=8 ;;
            254) let nbits+=7 ;;
            252) let nbits+=6 ;;
            248) let nbits+=5 ;;
            240) let nbits+=4 ;;
            224) let nbits+=3 ;;
            192) let nbits+=2 ;;
            128) let nbits+=1 ;;
            0) ;;
            *) echo ""; return 1 ;;
        esac
    done
    echo "$nbits"
}

CIDR=$(netmask_to_cidr "$NETMASK")
if [[ -z "$CIDR" ]]; then
    log "❌ Failed to convert netmask $NETMASK to CIDR."
    exit 1
fi

# Configure AP IP
log "🔧 Configuring interface $INTERFACE with IP $AP_IP/$CIDR..."
sudo ip addr add "$AP_IP/$CIDR" dev "$INTERFACE"
sudo ip link set "$INTERFACE" up

# Hostapd configuration
log "📝 Writing hostapd.conf..."
cat <<EOF > "$HOSTAPD_CONF"
interface=$INTERFACE
driver=nl80211
logger_syslog=-1
logger_syslog_level=2
logger_stdout=-1
logger_stdout_level=2
debug=2
ssid=$SSID
wpa_passphrase=$PASSPHRASE
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
auth_algs=1
hw_mode=g
channel=$CHANNEL
country_code=KE
ieee80211n=1
ieee80211ac=1
require_ht=1
obss_interval=5
ht_capab=[HT40][SHORT-GI-20][SHORT-GI-40][DSSS_CCK-40]
beacon_int=100
dtim_period=2
max_num_sta=8
wmm_enabled=1
EOF

# Dnsmasq configuration
log "📝 Writing dnsmasq.conf..."
cat <<EOF > "$DNSMASQ_CONF"
interface=$INTERFACE
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,$DHCP_LEASE_TIME
dhcp-option=option:router,$AP_IP
dhcp-option=option:dns-server,$AP_IP,8.8.8.8
dhcp-authoritative
log-dhcp
EOF

# Start dnsmasq
log "🚀 Starting dnsmasq..."
if ! command -v dnsmasq >/dev/null; then
    log "❌ dnsmasq not installed!"
    exit 1
fi
sudo pkill dnsmasq || true
sudo dnsmasq -C "$DNSMASQ_CONF" --log-facility="$LOG_FILE"

# Enable NAT and IP forwarding
log "🔁 Enabling NAT and IP forwarding..."
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A POSTROUTING -o "$DEFAULT_IFACE" -j MASQUERADE
sudo iptables -A FORWARD -i "$INTERFACE" -j ACCEPT
sudo iptables -A FORWARD -o "$INTERFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT

# Verify interface supports AP mode
PHY_NAME=$(cat /sys/class/net/$INTERFACE/phy80211/name)
if ! iw phy $PHY_NAME info | grep -q "AP"; then
    log "❌ Interface $INTERFACE doesn't support AP mode!"
    exit 1
fi

# Reload wireless driver if needed
log "🔄 Reloading wireless driver..."
DRIVER=$(basename $(readlink /sys/class/net/$INTERFACE/device/driver/module))
if [ -n "$DRIVER" ]; then
    sudo modprobe -r $DRIVER 2>/dev/null || true
    sudo modprobe $DRIVER
    sleep 2
else
    log "⚠️ Could not determine driver name, skipping reload"
fi

# Start hostapd
log "🚀 Starting hostapd..."
if ! command -v hostapd >/dev/null; then
    log "❌ hostapd not installed!"
    exit 1
fi

sudo hostapd -B "$HOSTAPD_CONF"

log "✅ Access point setup complete. Press Ctrl+C to stop."
log "🌐 Wired connection remains active on $DEFAULT_IFACE"

# Keep script running
while true; do
    sleep 3600
done