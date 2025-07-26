#!/bin/bash
# hostapd_test.sh - safely start and stop hostapd with given config for testing

CONFIG_PATH="/tmp/test_ap.conf"
HOSTAPD_BIN=$(which hostapd)

if [[ -z "$HOSTAPD_BIN" ]]; then
  echo "hostapd is not installed or not in PATH."
  exit 1
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Hostapd config file not found at $CONFIG_PATH"
  exit 1
fi

# Start hostapd in background and save PID
echo "Starting hostapd..."
$HOSTAPD_BIN -B "$CONFIG_PATH"
sleep 3

# Get PID of hostapd process (assuming only one instance running)
PID=$(pgrep -f "hostapd.*$CONFIG_PATH")

if [[ -z "$PID" ]]; then
  echo "Failed to start hostapd"
  exit 1
fi

echo "hostapd started with PID $PID"

# Wait for user input to stop hostapd
read -p "Press Enter to stop hostapd..."

echo "Stopping hostapd (PID $PID)..."
kill "$PID"
sleep 2

if kill -0 "$PID" 2>/dev/null; then
  echo "hostapd did not stop, killing forcefully"
  kill -9 "$PID"
fi

echo "hostapd stopped."
