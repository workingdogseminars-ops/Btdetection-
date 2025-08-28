#!/bin/bash
# Auto-start script for Bluetooth IDS

cd /home/andrewdarr/intrusion

# Start web dashboard in background
source .venv/bin/activate
python3 web_dashboard.py &

# Wait for web server to start
sleep 10

# Update config to show ARMED status
python3 -c "
import json
config = {'armed': True, 'schedule_enabled': False, 'schedule': {'monday': {'enabled': True, 'start': '18:00', 'end': '06:00'}, 'tuesday': {'enabled': True, 'start': '18:00', 'end': '06:00'}, 'wednesday': {'enabled': True, 'start': '18:00', 'end': '06:00'}, 'thursday': {'enabled': True, 'start': '18:00', 'end': '06:00'}, 'friday': {'enabled': True, 'start': '18:00', 'end': '06:00'}, 'saturday': {'enabled': False, 'start': '18:00', 'end': '06:00'}, 'sunday': {'enabled': False, 'start': '18:00', 'end': '06:00'}}, 'trigger_threshold': 45, 'scan_interval': 3}
with open('ids_config.json', 'w') as f:
    json.dump(config, f, indent=2)
"

# Start IDS system
source .venv/bin/activate
python3 remote_site_with_email.py &

echo "Bluetooth IDS Auto-Started and ARMED"
