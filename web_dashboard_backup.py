#!/usr/bin/env python3
"""
Bluetooth IDS Web Dashboard
Simple web interface for ARM/DISARM and scheduling
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
import subprocess
import signal
from datetime import datetime

app = Flask(__name__)

class IDSController:
    def __init__(self):
        self.config_file = "ids_config.json"
        self.status_file = "ids_status.json"
        self.load_config()
    
    def load_config(self):
        """Load configuration"""
        default_config = {
            "armed": False,
            "schedule_enabled": False,
            "schedule": {
                "monday": {"enabled": True, "start": "18:00", "end": "06:00"},
                "tuesday": {"enabled": True, "start": "18:00", "end": "06:00"},
                "wednesday": {"enabled": True, "start": "18:00", "end": "06:00"},
                "thursday": {"enabled": True, "start": "18:00", "end": "06:00"},
                "friday": {"enabled": True, "start": "18:00", "end": "06:00"},
                "saturday": {"enabled": False, "start": "18:00", "end": "06:00"},
                "sunday": {"enabled": False, "start": "18:00", "end": "06:00"}
            },
            "trigger_threshold": 45,
            "scan_interval": 3
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except:
                pass
        
        self.config = default_config
        self.save_config()
    
    def save_config(self):
        """Save configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_system_status(self):
        """Check if IDS is running"""
        try:
            result = subprocess.run(['/usr/bin/pgrep', '-f', 'remote_site_with_email.py'], 
                                  capture_output=True, text=True)
            running = len(result.stdout.strip()) > 0
            
            return {
                "running": running,
                "armed": self.config["armed"],
                "schedule_enabled": self.config["schedule_enabled"],
                "last_updated": datetime.now().isoformat()
            }
        except:
            return {"running": False, "armed": False, "schedule_enabled": False}

ids_controller = IDSController()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    status = ids_controller.get_system_status()
    return render_template('dashboard.html', 
                         status=status, 
                         config=ids_controller.config)


@app.route('/arm', methods=['POST'])
def arm_system():
    """ARM the system"""
    try:
        # Start the IDS script
        subprocess.Popen(["/bin/bash", "-c", "cd /home/andrewdarr/intrusion && source .venv/bin/activate && python3 remote_site_with_email.py"], cwd="/home/andrewdarr/intrusion")
        
        # Wait a moment then check if it actually started
        import time
        time.sleep(2)
        result = subprocess.run(['/usr/bin/pgrep', '-f', 'remote_site_with_email.py'], capture_output=True, text=True)
        actually_running = len(result.stdout.strip()) > 0
        
        ids_controller.config["armed"] = actually_running
        ids_controller.save_config()
        
        return jsonify({"status": "success", "message": "System ARMED" if actually_running else "Failed to start"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/disarm', methods=['POST'])
def disarm_system():
    """DISARM the system"""
    try:
        # Stop the IDS script
        subprocess.run(['/usr/bin/pkill', '-f', 'remote_site_with_email.py'])
        ids_controller.config["armed"] = False
        ids_controller.save_config()
        return jsonify({"status": "success", "message": "System DISARMED"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/status')
def get_status():
    """Get current system status"""
    status = ids_controller.get_system_status()
    return jsonify(status)

@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    """Schedule management"""
    if request.method == 'POST':
        try:
            # Update schedule from form data
            schedule_enabled = request.form.get('schedule_enabled') == 'on'
            ids_controller.config["schedule_enabled"] = schedule_enabled
            
            # Update day schedules
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                enabled = request.form.get(f'{day}_enabled') == 'on'
                start_time = request.form.get(f'{day}_start', '18:00')
                end_time = request.form.get(f'{day}_end', '06:00')
                
                ids_controller.config["schedule"][day] = {
                    "enabled": enabled,
                    "start": start_time,
                    "end": end_time
                }
            
            ids_controller.save_config()
            return redirect(url_for('schedule'))
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    
    return render_template('schedule.html', config=ids_controller.config)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page"""
    if request.method == 'POST':
        try:
            ids_controller.config["trigger_threshold"] = int(request.form.get('trigger_threshold', 45))
            ids_controller.config["scan_interval"] = int(request.form.get('scan_interval', 3))
            ids_controller.save_config()
            return redirect(url_for('settings'))
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    
    return render_template('settings.html', config=ids_controller.config)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
