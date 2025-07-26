#!/bin/bash
set -euo pipefail

# Initialize logging
mkdir -p /etc/hostapd-prod
LOG_FILE="/var/log/prod_ap.log"

# Parse command line arguments
ACTION="${1:-start}"  # Default to 'start' if no action provided
HOTSPOT_ID="${2:-}"   # Optional hotspot ID

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

# Add this function near the top of your script
reset_wireless_interface() {
    log "🔄 Resetting wireless interface $INTERFACE..."
    
    # Bring interface down and flush
    sudo ip link set $INTERFACE down
    sudo ip addr flush dev $INTERFACE
    
    # Kill conflicting processes
    sudo pkill wpa_supplicant || true
    sudo pkill dhclient || true
    
    # Reset driver (for Intel cards)
    if lsmod | grep -q iwlwifi; then
        sudo modprobe -r iwlmvm
        sudo modprobe -r mac80211
        sudo modprobe -r cfg80211
        sudo modprobe -r iwlwifi
        sleep 2
        sudo modprobe iwlwifi
        sudo modprobe cfg80211
        sudo modprobe mac80211
        sudo modprobe iwlmvm
        sleep 2
    fi
    
    # Unblock WiFi
    sudo rfkill unblock all
    sleep 2
}

log "🔧 Starting hotspot control with action: $ACTION, hotspot ID: ${HOTSPOT_ID:-none}"

# Load environment - modified to support hotspot-specific configs
ENV_FILE="/etc/hostapd-prod.env"
if [[ -n "$HOTSPOT_ID" ]]; then
    # If hotspot ID provided, look for a hotspot-specific env file
    HOTSPOT_ENV_FILE="/tmp/hostapd-prod/hotspot_${HOTSPOT_ID}.env"
    if [[ -f "$HOTSPOT_ENV_FILE" ]]; then
        ENV_FILE="$HOTSPOT_ENV_FILE"
        log "🔄 Loading hotspot-specific environment from $HOTSPOT_ENV_FILE"
    else
        log "⚠️ Hotspot-specific config not found, falling back to default"
    fi
fi

if [[ ! -f "$ENV_FILE" ]]; then
    log "❌ Critical: No environment file found at $ENV_FILE"
    log "ℹ️ Please create the environment file first"
    exit 1
fi

log "🔄 Loading environment from $ENV_FILE"
source "$ENV_FILE"

# Verify required SSID is set
if [[ -z "${SSID:-}" ]]; then
    log "❌ Critical: SSID not set in environment file"
    exit 1
fi

log "✅ Using SSID: $SSID"

# Handle different actions
case "$ACTION" in
    start)
        # Continue with normal startup
        ;;
    stop)
        log "🛑 Stopping hotspot services..."
        cleanup
        exit 0
        ;;
    restart)
        log "🔄 Restarting hotspot services..."
        cleanup
        # Continue with normal startup
        ;;
    status)
        log "ℹ️ Checking hotspot status..."
        if pgrep -f "hostapd.*$HOSTAPD_CONF" >/dev/null; then
            log "✅ Hotspot is running"
            exit 0
        else
            log "❌ Hotspot is not running"
            exit 1
        fi
        ;;
    *)
        log "❌ Unknown action: $ACTION"
        log "Usage: $0 {start|stop|restart|status} [hotspot_id]"
        exit 1
        ;;
esac

# Enhanced wireless interface activation
activate_wireless_interface() {
    # 1. Completely stop all network services
    sudo systemctl stop NetworkManager
    sudo systemctl stop wpa_supplicant
    sudo killall wpa_supplicant 2>/dev/null || true
    sudo killall dhclient 2>/dev/null || true
    
    # 2. Reset all possible wireless interfaces
    for iface in $(ls /sys/class/net | grep -E 'wlo|wlan|wlp'); do
        sudo ip link set $iface down 2>/dev/null || true
        sudo ip addr flush dev $iface 2>/dev/null || true
    done
    
    # 3. Full wireless stack reset (for Intel cards)
    if lsmod | grep -q iwlwifi; then
        log "🔧 Resetting Intel wireless stack..."
        sudo modprobe -r iwlmvm 2>/dev/null || true
        sudo modprobe -r mac80211 2>/dev/null || true
        sudo modprobe -r cfg80211 2>/dev/null || true
        sudo modprobe -r iwlwifi 2>/dev/null || true
        sleep 3  # Increased delay
        sudo modprobe iwlwifi 2>/dev/null || true
        sudo modprobe cfg80211 2>/dev/null || true
        sudo modprobe mac80211 2>/dev/null || true
        sudo modprobe iwlmvm 2>/dev/null || true
        sleep 3  # Increased delay
    fi
    
    # 4. Hardware unblock
    sudo rfkill unblock all
    sleep 2
    
    # 5. Find active interface
    local interface=$(iw dev | awk '$1=="Interface"{print $2}' | head -n1)
    if [[ -n "$interface" ]]; then
        echo "$interface"
        return 0
    fi
    
    # 6. Try to manually bring up interfaces
    for iface in $(ls /sys/class/net | grep -E 'wlo|wlan|wlp'); do
        sudo ip link set $iface up 2>/dev/null && {
            echo "$iface"
            return 0
        }
    done
    
    log "❌ Could not activate wireless interface after full reset"
    return 1
}

# Main interface detection
log "🔍 Activating wireless interface..."
INTERFACE=$(activate_wireless_interface) || {
    log "❌ Critical: Wireless interface cannot be activated"
    log "ℹ️ Diagnostic commands to try:"
    log "1. Check hardware: sudo lshw -C network"
    log "2. Check kernel messages: dmesg | grep iwl"
    log "3. Check rfkill: sudo rfkill list"
    log "4. Check PCI devices: lspci -nnk | grep -iA3 net"
    exit 1
}
log "✅ Wireless interface activated: $INTERFACE"

# Detect wired interface
WIRED_IFACE=$(ip route | awk '/default/ {print $5}' | head -n1)
if [[ -z "$WIRED_IFACE" ]] || [[ "$WIRED_IFACE" == "$INTERFACE" ]]; then
    WIRED_IFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -vE 'lo|wlan|wlp|wlo' | head -n1)
fi

if [[ -z "$WIRED_IFACE" ]]; then
    log "❌ Could not determine wired internet interface"
    exit 1
fi
log "ℹ️ Using wired internet interface: $WIRED_IFACE"

# Verify required variables
REQUIRED_VARS=(AP_IP NETMASK SSID PASSPHRASE CHANNEL DHCP_RANGE_START DHCP_RANGE_END DHCP_LEASE_TIME)
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        log "❌ Missing required variable: $var"
        exit 1
    fi
done

# Configuration files
HOSTAPD_CONF="/etc/hostapd-prod/hostapd.conf"
DNSMASQ_CONF="/etc/hostapd-prod/dnsmasq.conf"

cleanup() {
    log "🧹 Cleaning up services..."
    
    # Stop services
    sudo killall hostapd 2>/dev/null || true
    sudo killall dnsmasq 2>/dev/null || true
    
    # Restore iptables
    sudo iptables -t nat -D POSTROUTING -o "$WIRED_IFACE" -j MASQUERADE 2>/dev/null || true
    sudo iptables -D FORWARD -i "$INTERFACE" -j ACCEPT 2>/dev/null || true
    sudo iptables -D FORWARD -o "$INTERFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
    
    # Reset interface
    sudo ip link set "$INTERFACE" down 2>/dev/null || true
    sudo ip addr flush dev "$INTERFACE" 2>/dev/null || true
    
    # Restore NetworkManager
    if systemctl is-active --quiet NetworkManager; then
        log "🔄 Restoring NetworkManager control"
        sudo nmcli device set "$INTERFACE" managed yes 2>/dev/null || true
        sudo systemctl restart NetworkManager 2>/dev/null || true
    else
        sudo systemctl start NetworkManager 2>/dev/null || true
    fi
    
    log "✅ Network services restored"
}
trap cleanup EXIT

# NetworkManager handling
if systemctl is-active --quiet NetworkManager; then
    log "🔧 Taking control of $INTERFACE from NetworkManager"
    sudo nmcli device set "$INTERFACE" managed no || {
        log "⚠️ Could not set interface to unmanaged, stopping NetworkManager"
        sudo systemctl stop NetworkManager
    }
fi

# Ensure WiFi is unblocked
sudo rfkill unblock wifi
sleep 1

# Configure interface
log "📡 Configuring $INTERFACE..."
sudo ip link set "$INTERFACE" down || true
sudo ip addr flush dev "$INTERFACE" || true

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
    log "❌ Failed to convert netmask $NETMASK to CIDR"
    exit 1
fi

log "🔧 Assigning IP $AP_IP/$CIDR to $INTERFACE..."
sudo ip addr add "$AP_IP/$CIDR" dev "$INTERFACE" || {
    log "❌ Failed to assign IP address"
    exit 1
}
sudo ip link set "$INTERFACE" up || {
    log "❌ Failed to bring up interface"
    exit 1
}

# Call this right before starting hostapd
# reset_wireless_interface

log "📝 Configuring hostapd..."
cat <<EOF > "/etc/hostapd-prod/hostapd.conf"
# Basic configuration
interface=$INTERFACE
driver=nl80211
ssid=$SSID
country_code=KE
hw_mode=g
channel=$CHANNEL

# Security configuration
wpa=2
wpa_passphrase=$PASSPHRASE
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
auth_algs=1

# Critical performance settings
beacon_int=100
dtim_period=2
max_num_sta=8

# Disable advanced features temporarily
ieee80211n=0
ieee80211ac=0
wmm_enabled=0
EOF

# Dnsmasq configuration
log "📝 Configuring dnsmasq..."
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

# Enable NAT
log "🔁 Enabling NAT..."
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A POSTROUTING -o "$WIRED_IFACE" -j MASQUERADE
sudo iptables -A FORWARD -i "$INTERFACE" -j ACCEPT
sudo iptables -A FORWARD -o "$INTERFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT

# Verify AP mode support
if ! iw phy "$(cat /sys/class/net/$INTERFACE/phy80211/name)" info | grep -q "AP"; then
    log "❌ Interface $INTERFACE doesn't support AP mode"
    exit 1
fi

# Start hostapd in foreground for better debugging
log "🚀 Starting hostapd (debug mode)..."
sudo hostapd -d "$HOSTAPD_CONF"

log "✅ Access point setup complete. Press Ctrl+C to stop."

# Keep script running until interrupted
while true; do
    sleep 3600
done