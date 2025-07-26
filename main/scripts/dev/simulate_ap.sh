#!/bin/bash
# Requires hostapd and dnsmasq
INTERFACE=${1:-wlan0}
SSID=${2:-TestAP}
CHANNEL=${3:-6}

cat > /tmp/hostapd.conf <<EOF
interface=$INTERFACE
driver=nl80211
ssid=$SSID
hw_mode=g
channel=$CHANNEL
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-EAP
wpa_pairwise=CCMP
rsn_pairwise=CCMP
ieee8021x=1
eap_server=1
eap_user_file=/tmp/hostapd.eap_user
EOF

echo "test_user * test_pass" > /tmp/hostapd.eap_user
hostapd /tmp/hostapd.conf