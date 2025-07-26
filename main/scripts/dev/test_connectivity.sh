#!/bin/bash

# Start services
sudo systemctl start freeradius
python manage.py runserver &

# Run tests
pytest hotspots/tests/test_connectivity/ -v

# Cleanup
pkill -f "manage.py runserver"
sudo systemctl stop freeradius