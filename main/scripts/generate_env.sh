#!/bin/bash

# Prompt for input or use defaults
read -p "Enter Hotspot ID (e.g., 1): " HOTSPOT_ID
HOTSPOT_ID=${HOTSPOT_ID:-1}

read -p "Enter SSID [TestNet]: " SSID
SSID=${SSID:-TestNet}

read -p "Enter Password [1234567890]: " PASSWORD
PASSWORD=${PASSWORD:-1234567890}

read -p "Enter Channel [1, 6 or 11]: " CHANNEL
CHANNEL=${CHANNEL:-6}

CONFIG_DIR="/tmp/hostapd-prod"
CONFIG_FILE="$CONFIG_DIR/hotspot_${HOTSPOT_ID}.env"

# Create directory if needed
sudo mkdir -p "$CONFIG_DIR"
sudo chmod 777 "$CONFIG_DIR"  # Temporary wide permissions for debugging

# Create config file
cat <<EOF | sudo tee "$CONFIG_FILE" > /dev/null
# Hostapd production environment config
ENABLE_LOG="1"
LOG_FILE="/var/log/prod_ap_${HOTSPOT_ID}.log"
INTERFACE="wlo1"
SSID="${SSID}"
PASSPHRASE="${PASSWORD}"
AP_IP="192.168.${HOTSPOT_ID}.1"
NETMASK="255.255.255.0"
CHANNEL=${CHANNEL}

# DHCP config
DHCP_RANGE_START="192.168.${HOTSPOT_ID}.10"
DHCP_RANGE_END="192.168.${HOTSPOT_ID}.100"
DHCP_LEASE_TIME="12h"
INTERNET_IFACE="eth0"
EOF

# Set proper permissions
sudo chmod 644 "$CONFIG_FILE"

echo "Created config file at $CONFIG_FILE"
echo "Contents:"
cat "$CONFIG_FILE"