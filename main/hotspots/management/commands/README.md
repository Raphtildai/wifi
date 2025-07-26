# WiFi Hotspot Management System

## Table of Contents
- [System Overview](#system-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Django Integration](#django-integration)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [Security](#security)

## System Overview

This system provides seamless Django integration with Linux hostapd for WiFi hotspot management, featuring:
- Web interface for hotspot control
- Multi-hotspot support
- Real-time status monitoring
- Session management
- Integrated logging

## Prerequisites

### Hardware
- Wireless NIC supporting AP mode
- Wired internet connection for NAT

### Software
```bash
# Required packages
sudo apt update
sudo apt install -y hostapd dnsmasq iw python3 python3-pip
sudo systemctl stop hostapd dnsmasq
sudo systemctl disable hostapd dnsmasq
```

### Python Packages
```bash
pip install django djangorestframework
```

## Installation

### 1. Deploy Hotspot Script
```bash
sudo cp start-ap.sh /usr/local/bin/hotspotctl
sudo chmod +x /usr/local/bin/hotspotctl
sudo mkdir -p /etc/hotspot/conf.d /var/log/hotspots
```

### 2. Configure Sudo Access
Create `/etc/sudoers.d/hotspot`:
```bash
%hotspot-admin ALL=(root) NOPASSWD: /usr/local/bin/hotspotctl
Defaults!/usr/local/bin/hotspotctl !requiretty
```

### 3. Base Configuration
Create `/etc/hotspot/base.env`:
```ini
# Core configuration
INTERFACE=wlan0
AP_IP=192.168.50.1
NETMASK=255.255.255.0
DHCP_RANGE_START=192.168.50.10
DHCP_RANGE_END=192.168.50.100
COUNTRY_CODE=US
```

## Django Integration

### Model Extensions
Add to `hotspots/models.py`:
```python
class Hotspot(models.Model):
    # ... existing fields ...
    
    def control(self, action):
        """Execute hotspot control command"""
        from django.core.management import call_command
        call_command('hotspotctl', action, str(self.id))
        
    def get_status(self):
        try:
            result = subprocess.run(
                ['sudo', 'hotspotctl', 'status', str(self.id)],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
```

### Management Commands
Create `management/commands/hotspotctl.py`:
```python
from django.core.management.base import BaseCommand
import subprocess

class Command(BaseCommand):
    help = 'Hotspot control interface'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'])
        parser.add_argument('hotspot_id', type=int)

    def handle(self, *args, **options):
        try:
            subprocess.run(
                ['sudo', '/usr/local/bin/hotspotctl',
                 options['action'],
                 str(options['hotspot_id'])],
                check=True,
                timeout=30
            )
        except subprocess.TimeoutExpired:
            self.stderr.write("Error: Operation timed out")
        except subprocess.CalledProcessError as e:
            self.stderr.write(f"Command failed: {e.stderr}")
```

## Commands
### Django Integration Points:

1. Starting a Hotspot:
    ```python

    subprocess.run(['sudo', '/path/to/start-ap.sh', 'start', str(hotspot.id)], check=True)
    ```
2. Stopping a Hotspot:
    ```python

    subprocess.run(['sudo', '/path/to/start-ap.sh', 'stop', str(hotspot.id)], check=True)
    ```

3. Checking Status:
    ```python

    try:
        subprocess.run(['sudo', '/path/to/start-ap.sh', 'status', str(hotspot.id)], 
                    check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
    ```

## API Endpoints

### Available Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/hotspots/` | GET | List all hotspots |
| `/api/hotspots/<id>/start/` | POST | Start specific hotspot |
| `/api/hotspots/<id>/stop/` | POST | Stop specific hotspot |
| `/api/hotspots/<id>/status/` | GET | Get hotspot status |

### Sample View
```python
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def start_hotspot(request, pk):
    hotspot = get_object_or_404(Hotspot, pk=pk)
    try:
        hotspot.control('start')
        return Response({"status": "started"})
    except Exception as e:
        return Response({"error": str(e)}, status=500)
```

## Monitoring

### Log Locations
- System logs: `/var/log/hotspots/system.log`
- Hotspot-specific: `/var/log/hotspots/hotspot_<id>.log`
- Authentication: `/var/log/hotspots/auth.log`

### Log Rotation
Configure `/etc/logrotate.d/hotspots`:
```bash
/var/log/hotspots/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    sharedscripts
    postrotate
        systemctl reload rsyslog >/dev/null 2>&1 || true
    endscript
}
```

## Troubleshooting

### Common Issues

**1. Interface Not Found**
```bash
# Check available interfaces
iw dev

# Verify driver support
modinfo iwlwifi
```

**2. AP Mode Not Supported**
```bash
iw phy0 info | grep -A 10 "Supported interface modes"
```

**3. DHCP Failures**
```bash
# Check DHCP leases
cat /var/lib/misc/dnsmasq.leases

# Test DHCP server
dhclient -v wlan0
```

## Security

### Best Practices
1. **Network Isolation**:
   ```bash
   iptables -A FORWARD -i wlan0 -o eth0 -m state --state ESTABLISHED,RELATED -j DROP
   ```

2. **Encryption**:
   ```ini
   # In hotspot config
   wpa=2
   wpa_key_mgmt=WPA-PSK
   rsn_pairwise=CCMP
   ```

3. **Regular Updates**:
   ```bash
   sudo apt update && sudo apt upgrade hostapd dnsmasq
   ```

### Audit Checklist
- [ ] Verify sudo restrictions
- [ ] Validate input sanitization
- [ ] Confirm WPA2 encryption
- [ ] Check firewall rules
- [ ] Review access logs weekly

## Support

For assistance, contact:
- **Email**: support@yourcompany.com
- **Slack**: #hotspot-support
- **Emergency**: +1 (555) 123-4567 (24/7)

---

> **Note**: Always test in a staging environment before production deployment.  
> Last Updated: 2023-11-15 | Version: 2.1.0
```

This README provides:
1. Complete installation instructions
2. Ready-to-use code snippets
3. Comprehensive troubleshooting guide
4. Security best practices
5. Maintenance procedures

Simply copy this content into a `README.md` file in your project root directory. Customize the contact information and version details as needed.