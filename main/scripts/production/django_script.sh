#!/bin/bash
set -euo pipefail

# Initialize logging
mkdir -p /etc/hostapd-prod
LOG_FILE="/var/log/prod_ap.log"

# Parse command line arguments
ACTION="${1:-start}"  # Default to 'start' if no action provided
HOTSPOT_ID="${2:-}"   # Optional hotspot ID

# Interface detection
DETECTED_INTERFACE=$(iw dev | awk '$1=="Interface"{print $2}' | head -1)
[ -z "$DETECTED_INTERFACE" ] && DETECTED_INTERFACE="wlo1"

# Systemd-Specific wireless reset handling
SYSTEMD_RUNNING=0
if systemd-detect-virt --quiet --container; then
    SYSTEMD_RUNNING=1
    log "⚠️ Running under systemd - adjusting behavior"
fi

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

log "🔧 Starting hotspot control with action: $ACTION, hotspot ID: ${HOTSPOT_ID:-none}"

# Environment loading with better debugging
load_environment() {
    local config_id="$1"
    local default_env="/etc/hostapd-prod.env"
    local hotspot_env="/tmp/hostapd-prod/hotspot_${config_id}.env"
    
    # Always load default config first
    if [ -f "$default_env" ]; then
        log "🔧 Loading base configuration from $default_env"
        source "$default_env"
    else
        log "⚠️ No default configuration found at $default_env"
    fi
    
    # For API calls (not terminal mode), load hotspot-specific config
    if [ "$config_id" != "default" ] && [ -f "$hotspot_env" ]; then
        log "🔄 Loading hotspot-specific overrides from $hotspot_env"
        source "$hotspot_env"
        
        # Auto-generate network params if not specified
        export AP_IP="${AP_IP:-192.168.${config_id}.1}"
        export DHCP_RANGE_START="${DHCP_RANGE_START:-192.168.${config_id}.10}"
        export DHCP_RANGE_END="${DHCP_RANGE_END:-192.168.${config_id}.100}"
    fi

    # Debug output
    log "⚙️ Active configuration:"
    log " - SSID: ${SSID:-NOT SET}"
    log " - INTERFACE: ${INTERFACE:-will auto-detect}"
    log " - AP_IP: ${AP_IP:-NOT SET}"
    log " - CHANNEL: ${CHANNEL:-6}"
}

# Interface detection (prioritizes env file, then auto-detects)
detect_interface() {
    # Use configured interface if specified
    if [ -n "${INTERFACE:-}" ]; then
        if iw dev "$INTERFACE" info >/dev/null 2>&1; then
            echo "$INTERFACE"
            return 0
        fi
        log "⚠️ Configured interface $INTERFACE not found, auto-detecting..."
    fi

    # 2. Automatic detection
    local interfaces=()
    # Modern Linux (phy80211)
    if [ -d /sys/class/net ]; then
        interfaces+=($(ls /sys/class/net | grep -E 'wlan[0-9]+|wlo[0-9]+|wlp[0-9]+s[0-9]+'))
    fi
    
    # Fallback to iw
    if [ ${#interfaces[@]} -eq 0 ]; then
        interfaces+=($(iw dev | awk '/Interface/{print $2}'))
    fi

    # Verify each interface
    for iface in "${interfaces[@]}"; do
        if iw phy $(cat /sys/class/net/$iface/phy80211/name) info | grep -q "AP"; then
            echo "$iface"
            return 0
        fi
    done

    return 1
}

# Clean up
cleanup() {
    log "🧹 Cleaning up services..."
    
    # Stop services
    sudo pkill hostapd 2>/dev/null || true
    sudo pkill dnsmasq 2>/dev/null || true
    
    # Restore iptables
    sudo iptables -t nat -D POSTROUTING -o "$WIRED_IFACE" -j MASQUERADE 2>/dev/null || true
    sudo iptables -D FORWARD -i "$INTERFACE" -j ACCEPT 2>/dev/null || true
    
    # Reset interface
    sudo ip link set "$INTERFACE" down 2>/dev/null || true
    sudo ip addr flush dev "$INTERFACE" 2>/dev/null || true
    sudo iw dev "$INTERFACE" set type managed 2>/dev/null || true
    
    # Restore NetworkManager
    if [ -f /etc/NetworkManager/conf.d/99-hotspot.conf ]; then
        sudo rm /etc/NetworkManager/conf.d/99-hotspot.conf
    fi
    
    if systemctl is-active --quiet NetworkManager; then
        log "🔄 Restoring NetworkManager control"
        sudo nmcli device set "$INTERFACE" managed yes 2>/dev/null || true
        sudo nmcli connection reload
    else
        sudo systemctl start NetworkManager 2>/dev/null || true
    fi
    
    log "✅ Network services restored"
}
trap cleanup EXIT
# cleanup() {
#     log "🧹 Cleaning up services..."
    
#     # Stop services
#     sudo pkill hostapd 2>/dev/null || true
#     sudo pkill dnsmasq 2>/dev/null || true
    
#     # Restore iptables
#     sudo iptables -t nat -D POSTROUTING -o "$WIRED_IFACE" -j MASQUERADE 2>/dev/null || true
#     sudo iptables -D FORWARD -i "$INTERFACE" -j ACCEPT 2>/dev/null || true
#     sudo iptables -D FORWARD -o "$INTERFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
    
#     # Reset interface
#     sudo ip link set "$INTERFACE" down 2>/dev/null || true
#     sudo ip addr flush dev "$INTERFACE" 2>/dev/null || true
    
#     # Restore NetworkManager
#     if systemctl is-active --quiet NetworkManager; then
#         log "🔄 Restoring NetworkManager control"
#         sudo nmcli device set "$INTERFACE" managed yes 2>/dev/null || true
#         sudo systemctl restart NetworkManager 2>/dev/null || true
#     else
#         sudo systemctl start NetworkManager 2>/dev/null || true
#     fi
    
#     log "✅ Network services restored"
# }
# trap cleanup EXIT

# Recover network
recover_network() {
    log "🔄 Attempting network recovery..."
    sudo nmcli networking off
    sleep 2
    sudo nmcli networking on
    sleep 5
    sudo systemctl restart NetworkManager
    log "✅ Network recovery restored successfully"
}
trap recover_network EXIT


# Handle different actions
case "$ACTION" in
    start)
        if [ -z "$HOTSPOT_ID" ]; then
            # Terminal testing mode
            log "🔧 Starting in terminal test mode"
            if [ ! -f "/etc/hostapd-prod.env" ]; then
                log "❌ Default config /etc/hostapd-prod.env not found"
                exit 1
            fi
            load_environment "default"  # Special case for terminal
        else
            # Django API mode
            load_environment "$HOTSPOT_ID"
        fi
        
        # Common startup logic
        INTERFACE=$(detect_interface) || {
            log "❌ No suitable wireless interface found"
            exit 1
        }
        log "✅ Using interface: $INTERFACE"
        ;;
    stop)
        log "🛑 Stopping hotspot services..."
        cleanup
        exit 0
        ;;
    restart)
        if [ -z "$HOTSPOT_ID" ]; then
            log "❌ Hotspot ID not provided"
            exit 1
        fi
        load_environment "$HOTSPOT_ID"
        INTERFACE=$(detect_interface) || {
            log "❌ No suitable wireless interface found"
            exit 1
        }
        log "✅ Using interface: $INTERFACE"
        # Verifying we can read the environment variables
        log "🔍 Verifying environment variables..."
        log " - SSID: ${SSID:-NOT SET}"
        log " - AP_IP: ${AP_IP:-NOT SET}"
        log "🔄 Restarting hotspot services for $HOTSPOT_ID..."
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

# Main interface detection
log "🔍 Activating wireless interface..."
INTERFACE=$(iw dev | awk '$1=="Interface"{print $2}' | head -n1)
if [[ -z "$INTERFACE" ]]; then
    # Try alternative detection methods
    INTERFACE=$(ls /sys/class/net | grep -E 'wlo|wlan|wlp' | head -n1)
fi

if [[ -z "$INTERFACE" ]]; then
    log "❌ Could not detect wireless interface"
    exit 1
fi

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

# Now verify required variables (after environment is loaded)
if [[ "$ACTION" == "start" || "$ACTION" == "restart" ]]; then
    REQUIRED_VARS=(AP_IP NETMASK SSID PASSPHRASE CHANNEL DHCP_RANGE_START DHCP_RANGE_END DHCP_LEASE_TIME)
    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log "❌ Missing required variable: $var"
            exit 1
        fi
    done
    log "✅ Using SSID: $SSID"
fi

# Enhanced wireless interface cleanup and activation
if [ "$SYSTEMD_RUNNING" -eq 1 ]; then
    log "🔧 Systemd mode: Skipping aggressive driver reloads"
else
    reset_wireless_interface() {
        local interface="$1"
        
        log "🔧 Performing safe reset of $interface..."
        
        # 1. Release from NetworkManager gently
        if systemctl is-active --quiet NetworkManager; then
            sudo nmcli device disconnect "$interface" 2>/dev/null || true
            sudo nmcli device set "$interface" managed no 2>/dev/null || true
        fi
        
        # 2. Basic interface reset
        sudo ip link set "$interface" down
        sudo ip addr flush dev "$interface"
        sudo iw dev "$interface" set type managed
        sudo rfkill unblock wifi
        
        # 3. Bring back up
        sudo ip link set "$interface" up
        sleep 2
        
        # 4. Verify
        if ! iwconfig "$interface" >/dev/null 2>&1; then
            log "⚠️ Soft reset failed, trying more aggressive approach"
            sudo systemctl restart NetworkManager
            sleep 3
            sudo ip link set "$interface" up
        fi
        
        log "✅ Interface $interface reset"
    }
fi

# Perform full reset of the interface
if ! reset_wireless_interface "$INTERFACE"; then
    log "❌ Critical: Wireless interface cannot be activated"
    log "ℹ️ Diagnostic commands to try:"
    log "1. Check hardware: sudo lshw -C network"
    log "2. Check kernel messages: dmesg | grep iwl"
    log "3. Check rfkill: sudo rfkill list"
    log "4. Check PCI devices: lspci -nnk | grep -iA3 net"
    exit 1
fi
log "✅ Wireless interface activated: $INTERFACE"

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

# NetworkManager handling
if systemctl is-active --quiet NetworkManager; then
    log "🔧 Disabling NetworkManager control of $INTERFACE..."
    sudo nmcli device set "$INTERFACE" managed no 2>/dev/null || {
        log "⚠️ Could not set unmanaged, stopping NetworkManager"
        sudo systemctl stop NetworkManager
        sleep 2
    }
    
    # Add persistent unmanaged
    if [ -d /etc/NetworkManager/conf.d ]; then
        echo -e "[keyfile]\nunmanaged-devices=interface-name:$INTERFACE" | \
        sudo tee /etc/NetworkManager/conf.d/99-hotspot.conf >/dev/null
        sudo systemctl restart NetworkManager
        sleep 2
    fi
fi
# if systemctl is-active --quiet NetworkManager; then
#     log "🔧 Taking control of $INTERFACE from NetworkManager"
#     sudo nmcli device set "$INTERFACE" managed no || {
#         log "⚠️ Could not set interface to unmanaged, stopping NetworkManager"
#         sudo systemctl stop NetworkManager
#     }
# fi

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

log "📝 Configuring hostapd..."
cat <<EOF > "$HOSTAPD_CONF"
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
# daemonize=0

# Performance settings
beacon_int=100
dtim_period=2
max_num_sta=8

# Disable advanced features for maximum compatibility
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

# Additional check for interface state
log "🔍 Verifying AP mode support..."
PHY=$(cat /sys/class/net/$INTERFACE/phy80211/name)
if ! iw phy $PHY info | grep -A 10 "Supported interface modes" | grep -q "\* AP"; then
    log "❌ Interface $INTERFACE doesn't support AP mode"
    log "ℹ️ Supported modes:"
    iw phy $PHY info | grep -A 10 "Supported interface modes"
    exit 1
fi
log "✅ Interface supports AP mode"

# Add this check right before starting hostapd:
log "🔄 Final interface state check..."
sudo ip link set $INTERFACE down
sleep 1
sudo ip link set $INTERFACE up
sleep 1

# Start hostapd in foreground for better debugging
log "🚀 Starting hostapd (debug mode)..."
sudo hostapd -d "$HOSTAPD_CONF" || {
    log "❌ hostapd failed to start"
    log "ℹ️ Common issues:"
    log "1. Interface already in use (try: sudo lsof -i | grep $INTERFACE)"
    log "2. Driver issues (try: sudo modprobe -r iwlwifi && sudo modprobe iwlwifi)"
    log "3. Hardware not supporting AP mode"
    exit 1
}

log "✅ Access point setup complete. Press Ctrl+C to stop."

# Keep script running until interrupted
while true; do
    sleep 3600
done