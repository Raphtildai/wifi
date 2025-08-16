Here's the updated README reflecting our recent changes:

# Hostapd Wi-Fi Hotspot Management System

## Overview
This system provides a production-grade Wi-Fi hotspot solution with:
- Django backend for management
- Celery for async task processing
- Bash scripts for low-level hotspot control
- Systemd service integration

## Key Improvements

1. **Dual Operation Modes**:
   - **Terminal Mode**: Test hotspots directly with default config
   - **API Mode**: Full integration with Django admin interface

2. **Simplified Configuration**:
   - Minimal Django configuration
   - Automatic network parameter generation
   - Environment variable inheritance

3. **Enhanced Reliability**:
   - Better interface detection
   - Improved error handling
   - Comprehensive logging

## 🔧 Requirements

### Core Packages
```bash
sudo apt update
sudo apt install -y \
    hostapd \
    dnsmasq \
    iptables \
    wireless-tools \
    net-tools \
    python3 \
    python3-pip \
    redis-server
```

### Python Packages
```bash
pip install django celery redis
```

## 📁 File Structure

```
/wifi-prod/
├── main/                      # Django project
│   ├── hotspots/              # Hotspot app
│   │   ├── services.py        # Hotspot control service
│   │   ├── tasks.py           # Celery tasks
│   │   └── views.py           # API endpoints
├── scripts/
│   ├── production/
│   │   ├── django_script.sh   # Main control script
│   │   └── hostapd-prod.env   # Default config
└── README.md
```

## 🚀 Quick Start

### 1. Terminal Testing Mode
```bash
sudo bash django_script.sh start
```
Uses default config from `/etc/hostapd-prod.env`

### 2. Django API Mode
```bash
sudo bash django_script.sh start 5  # Starts hotspot with ID 5
```

### 3.0 Checking Service status Manually:
```bash
sudo systemctl status hotspot_2.service # Checks status for hotspot with ID 2
journalctl -u hotspot_2.service -n 50 --no-pager
```

## Configuration

### Default Config (`/etc/hostapd-prod.env`)
```bash
# Basic configuration
INTERFACE="wlo1"
SSID="DefaultHotspot"
PASSPHRASE="securepassword"
CHANNEL=6

# Network settings
AP_IP="192.168.100.1"
NETMASK="255.255.255.0"
DHCP_RANGE_START="192.168.100.10"
DHCP_RANGE_END="192.168.100.100"
DHCP_LEASE_TIME="12h"
INTERNET_IFACE="eth0"
```

### Hotspot-Specific Config
Generated in `/tmp/hostapd-prod/hotspot_[ID].env` with:
```bash
SSID=CustomName
PASSWORD=CustomPass
CHANNEL=11
```

## System Integration

### Celery Worker
```bash
celery -A main worker --loglevel=info
```

### Systemd Service
Example unit file at `/etc/systemd/system/hotspot_[ID].service`

## 🔍 Debugging

### View Logs
```bash
# Application logs
sudo tail -f /var/log/prod_ap.log

# System logs
sudo journalctl -u hotspot_*.service
```

### Common Fixes
```bash
# Reset wireless driver
sudo modprobe -r iwlwifi && sudo modprobe iwlwifi

# Check interface modes
iw list | grep "Supported interface modes" -A 10
```

## 🧹 Cleanup
The system automatically:
- Releases network interfaces
- Removes iptables rules
- Restores NetworkManager control
- Cleans up temp files

## 📝 Notes
- All operations require root privileges
- Hotspot IDs must be unique
- Consider firewall rules for production use
- Test in controlled environment before deployment

---

© 2025 — Raphael Kipchirchir  
Last Updated: August 2025