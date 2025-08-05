# Hotspot Management System - Setup & Testing Guide

## Project Overview
This application provides WiFi hotspot management capabilities including creation, configuration, and monitoring of wireless access points.

## Prerequisites
- Python 3.8+
- Redis (for Celery task queue)
- systemd (for service management)
- hostapd, dnsmasq (for hotspot functionality)
- Virtual environment (recommended)

## Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:Raphtildai/wifi.git
   cd wifi
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # OR
   venv\Scripts\activate    # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Environment variables**
   Create a `.env` file in the project root:
   ```ini
   DEBUG=True
   SECRET_KEY=your-secret-key
   DATABASE_URL=sqlite:///db.sqlite3
   REDIS_URL=redis://localhost:6379/0
   ```

## Running the Application

### 1. Start Required Services

**In separate terminal windows/tabs:**

1. **Database migrations**
   ```bash
   python manage.py migrate
   ```

2. **Redis (task queue)**
   ```bash
   sudo systemctl start redis
   # OR manually:
   redis-server
   ```

3. **Celery worker**
    - Starting Celery worker
        
    ```bash
    celery -A main worker --loglevel=info
    ```
    - Clear Old tasks
    ```bash
    celery -A main purge -f
    ```

4. **Django development server**
   ```bash
   python manage.py runserver
   ```

### 2. Testing Commands

**Create a test hotspot (via API):**
```bash
curl -X POST http://localhost:8000/api/hotspots/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "ssid": "TestHotspot",
    "password": "test1234",
    "interface": "wlan0",
    "channel": 6,
    "hotspot_type": "public"
  }'
```

**Check hotspot status:**
```bash
curl http://localhost:8000/api/hotspots/1/status/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Check Celery task status:**
```bash
curl "http://localhost:8000/api/hotspots/1/task_status/?task_id=TASK_ID" \
  -H "Authorization: Token YOUR_TOKEN"
```

## Development Workflow

1. **Reset environment for clean testing:**
   ```bash
   # Stop all services
   pkill -f "celery worker"
   pkill -f "runserver"
   sudo systemctl stop redis

   # Clear existing data
   rm db.sqlite3
   find . -name "*.pyc" -delete

   # Restart
   sudo systemctl start redis
   python manage.py migrate
   python manage.py runserver & celery -A main worker --loglevel=info
   ```

2. **Monitoring tools:**
   - **Celery flower** (task monitoring):
     ```bash
     pip install flower
     celery -A main flower
     ```
     Then visit: `http://localhost:5555`

   - **Database browser**:
     ```bash
     sqlite3 db.sqlite3
     ```

## Troubleshooting

**Common issues and fixes:**

1. **Celery tasks not executing:**
   - Verify Redis is running: `redis-cli ping` (should return "PONG")
   - Check worker logs for errors
   - Ensure the task is properly decorated with `@shared_task`

2. **Hotspot not starting:**
   - Check system logs: `journalctl -u hotspot_*.service -n 50`
   - Verify required packages: `sudo apt install hostapd dnsmasq`

3. **Permission errors:**
   - Ensure your user has sudo privileges for service management
   - Check SELinux/AppArmor settings if on Linux

## Production Notes

For production deployment, consider:
- Using gunicorn/uWSGI instead of runserver
- Setting up Celery as a systemd service
- Proper SSL configuration
- Database backups

---
