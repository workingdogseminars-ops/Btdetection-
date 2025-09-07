#!/usr/bin/env python3
"""
Bluetooth IDS Web Dashboard
Complete version with schedule integration and manual override support
"""

from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_httpauth import HTTPBasicAuth
import json
import os
import subprocess
import signal
from datetime import datetime, time, timedelta
import smtplib
from email.message import EmailMessage

app = Flask(__name__)

# Setup HTTP Basic Authentication
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    try:
        with open("web_auth.json", "r") as f:
            creds = json.load(f)
            return username == creds.get("username", "admin") and password == creds.get("password", "admin123")
    except:
        return username == "admin" and password == "admin123"

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
            "manual_override": False,
            "override_expires": None,
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
    
    def check_schedule_status(self):
        """Check if system should be armed based on current schedule"""
        if not self.config.get("schedule_enabled", False):
            return False, False
        
        try:
            current_time = datetime.now()
            current_day = current_time.strftime('%A').lower()
            current_time_obj = current_time.time()
            
            day_schedule = self.config.get("schedule", {}).get(current_day, {})
            
            if not day_schedule.get("enabled", False):
                return True, False
            
            start_time_str = day_schedule.get("start", "18:00")
            end_time_str = day_schedule.get("end", "06:00")
            
            start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time_str, '%H:%M').time()
            
            if start_time_obj > end_time_obj:
                should_be_armed = current_time_obj >= start_time_obj or current_time_obj <= end_time_obj
            else:
                should_be_armed = start_time_obj <= current_time_obj <= end_time_obj
            
            return True, should_be_armed
            
        except Exception as e:
            print(f"Error checking schedule: {e}")
            return False, False
    
    def get_next_schedule_transition_time(self):
        """Calculate when the next schedule transition will occur"""
        try:
            current_time = datetime.now()
            
            for days_ahead in range(0, 7):
                check_date = current_time.date() + timedelta(days=days_ahead)
                check_day = check_date.strftime('%A').lower()
                
                day_schedule = self.config.get("schedule", {}).get(check_day, {})
                if not day_schedule.get("enabled", False):
                    continue
                
                start_time_str = day_schedule.get("start", "18:00")
                end_time_str = day_schedule.get("end", "06:00")
                
                start_time = datetime.combine(check_date, 
                    datetime.strptime(start_time_str, '%H:%M').time())
                end_time = datetime.combine(check_date, 
                    datetime.strptime(end_time_str, '%H:%M').time())
                
                if start_time.time() > end_time.time():
                    end_time += timedelta(days=1)
                
                if days_ahead == 0:
                    if current_time < start_time:
                        return start_time
                    elif current_time < end_time:
                        return end_time
                else:
                    return start_time
            
            return None
        except Exception as e:
            print(f"Error calculating next transition: {e}")
            return None

    def set_manual_override(self, armed_state):
        """Set manual override that expires at next schedule transition"""
        if self.config.get("schedule_enabled", False):
            next_transition = self.get_next_schedule_transition_time()
            
            self.config["armed"] = armed_state
            self.config["manual_override"] = True if next_transition else False
            self.config["override_expires"] = next_transition.isoformat() if next_transition else None
            self.save_config()
            
            return next_transition
        else:
            self.config["armed"] = armed_state
            self.config["manual_override"] = False
            self.config["override_expires"] = None
            self.save_config()
            return None

    def get_effective_arm_status(self):
        """Get effective arm status considering manual override and schedule"""
        # Check if override has expired
        if self.config.get("manual_override", False):
            override_expires = self.config.get("override_expires")
            if override_expires:
                try:
                    expire_time = datetime.fromisoformat(override_expires)
                    if datetime.now() >= expire_time:
                        self.config["manual_override"] = False
                        self.config["override_expires"] = None
                        self.save_config()
                except:
                    pass
        
        # If manual override is active, use manual setting
        if self.config.get("manual_override", False):
            return self.config.get("armed", False)
        
        # Use schedule if enabled
        schedule_enabled, should_be_armed_by_schedule = self.check_schedule_status()
        if schedule_enabled:
            return should_be_armed_by_schedule
        else:
            return self.config.get("armed", False)
    
    def get_system_status(self):
        """Check if IDS is running"""
        try:
            result = subprocess.run(['/usr/bin/pgrep', '-f', 'remote_site_with_email.py'],
                                  capture_output=True, text=True)
            running = len(result.stdout.strip()) > 0
            
            effective_arm_status = self.get_effective_arm_status()
            schedule_enabled, should_be_armed_by_schedule = self.check_schedule_status()
            
            # Check VPS for armed status
            import requests
            try:
                vps_response = requests.get('https://admin.securecaller.online/api/status', timeout=2)
                if vps_response.status_code == 200:
                    vps_data = vps_response.json()
                    effective_arm_status = vps_data.get('armed', False)
            except:
                pass
            
            return {
                "running": running,
                "armed": self.config["armed"],
                "schedule_enabled": self.config["schedule_enabled"],
                "effective_arm_status": effective_arm_status,
                "should_be_armed_by_schedule": should_be_armed_by_schedule if schedule_enabled else None,
                "manual_override": self.config.get("manual_override", False),
                "override_expires": self.config.get("override_expires"),
                "last_updated": datetime.now().isoformat()
            }
        except:
            return {
                "running": False, 
                "armed": False, 
                "schedule_enabled": False,
                "effective_arm_status": False
            }

ids_controller = IDSController()

# Enhanced Dashboard Template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bluetooth IDS Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="10">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { text-align: center; color: #333; margin-bottom: 30px; }
        .nav { text-align: center; margin-bottom: 20px; padding: 10px 0; }
        .nav a { 
            display: inline-block;
            margin: 5px 8px; 
            text-decoration: none; 
            color: #007bff; 
            padding: 10px 16px; 
            border: 2px solid #007bff; 
            border-radius: 6px;
            min-width: 80px;
            text-align: center;
            font-weight: bold;
        }
        .nav a:hover { background-color: #007bff; color: white; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .status-card { padding: 20px; border-radius: 8px; text-align: center; border: 2px solid; }
        .status-running { background: #d4edda; color: #155724; border-color: #c3e6cb; }
        .status-stopped { background: #f8d7da; color: #721c24; border-color: #f5c6cb; }
        .status-armed { background: #fff3cd; color: #856404; border-color: #ffeaa7; }
        .status-disarmed { background: #d1ecf1; color: #0c5460; border-color: #b8daff; }
        .status-card h3 { margin-top: 0; margin-bottom: 10px; font-size: 16px; }
        .status-card p { margin: 0; font-size: 18px; font-weight: bold; }
        .control-buttons { text-align: center; margin: 30px 0; }
        .btn { padding: 15px 25px; margin: 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; min-width: 120px; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn:hover { opacity: 0.8; }
        .schedule-info { padding: 15px; background: #f8f9fa; border-radius: 6px; margin-top: 20px; border: 1px solid #dee2e6; }
        .override-info { padding: 15px; background: #fff3cd; border-radius: 6px; margin-top: 20px; border: 1px solid #ffeaa7; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="header">Bluetooth IDS Control Dashboard</h1>
        
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/schedule">Schedule</a>
            <a href="/settings">Settings</a>
            <a href="/voice">Voice</a>
        </div>

        <div class="status-grid">
            <div class="status-card {{ 'status-running' if status.running else 'status-stopped' }}">
                <h3>System Status</h3>
                <p>{{ 'RUNNING' if status.running else 'STOPPED' }}</p>
            </div>
            
            <div class="status-card {{ 'status-armed' if status.armed else 'status-disarmed' }}">
                <h3>Manual Status</h3>
                <p>{{ 'ARMED' if status.armed else 'DISARMED' }}</p>
            </div>
            
            <div class="status-card {{ 'status-armed' if status.effective_arm_status else 'status-disarmed' }}">
                <h3>Effective Status</h3>
                <p>{{ 'ARMED' if status.effective_arm_status else 'DISARMED' }}</p>
            </div>
            
            <div class="status-card {{ 'status-running' if status.schedule_enabled else 'status-stopped' }}">
                <h3>Schedule</h3>
                <p>{{ 'ENABLED' if status.schedule_enabled else 'DISABLED' }}</p>
            </div>
        </div>

        <div class="control-buttons">
            <button class="btn btn-success" onclick="armSystem()">ARM SYSTEM</button>
            <button class="btn btn-danger" onclick="disarmSystem()">DISARM SYSTEM</button>
        </div>
        
        {% if status.manual_override %}
        <div class="override-info">
            <h4>Manual Override Active</h4>
            <p><strong>Current Status:</strong> {{ 'ARMED' if status.armed else 'DISARMED' }} (manual override)</p>
            {% if status.override_expires %}
            <p><strong>Override Expires:</strong> {{ status.override_expires[:16].replace('T', ' ') }}</p>
            <p><em>System will return to schedule control at next transition.</em></p>
            {% endif %}
        </div>
        {% endif %}
        
        {% if status.schedule_enabled and not status.manual_override %}
        <div class="schedule-info">
            <h4>Schedule Information</h4>
            <p><strong>Schedule Mode:</strong> ACTIVE - System automatically managed by schedule</p>
            {% if status.should_be_armed_by_schedule is not none %}
            <p><strong>Current Schedule Status:</strong> {{ 'Should be ARMED' if status.should_be_armed_by_schedule else 'Should be DISARMED' }}</p>
            {% endif %}
        </div>
        {% endif %}
        
        <p style="text-align: center; margin-top: 30px; color: #666;">
            Last updated: {{ status.last_updated[:19] if status.last_updated else 'Unknown' }}
        </p>
    </div>

    <script>
        function armSystem() {
            fetch('/arm', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                window.location.reload();
            })
            .catch(error => alert('Error: ' + error));
        }
        
        function disarmSystem() {
            fetch('/disarm', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                window.location.reload();
            })
            .catch(error => alert('Error: ' + error));
        }
    </script>
</body>
</html>
"""

@app.route('/')
@auth.login_required
def dashboard():
    """Main dashboard page"""
    status = ids_controller.get_system_status()
    return render_template_string(DASHBOARD_TEMPLATE, status=status, config=ids_controller.config)

@app.route('/arm', methods=['POST'])
@auth.login_required
def arm_system():
    """ARM the system via VPS API"""
    try:
        import requests
        response = requests.post('https://admin.securecaller.online/api/arm', timeout=5)
        if response.status_code == 200:
            message = "System ARMED"
        else:
            raise Exception(f"VPS returned {response.status_code}")
        
        return jsonify({"status": "success", "message": message})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/disarm', methods=['POST'])
@auth.login_required
def disarm_system():
    """DISARM the system via VPS API"""
    try:
        import requests
        response = requests.post('https://admin.securecaller.online/api/disarm', timeout=5)
        if response.status_code == 200:
            message = "System DISARMED"
        else:
            raise Exception(f"VPS returned {response.status_code}")
        
        return jsonify({"status": "success", "message": message})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/status')
@auth.login_required
def get_status():
    """Get current system status"""
    status = ids_controller.get_system_status()
    return jsonify(status)

@app.route('/schedule', methods=['GET', 'POST'])
@auth.login_required
def schedule():
    """Schedule management"""
    if request.method == 'POST':
        try:
            schedule_enabled = 'schedule_enabled' in request.form
            ids_controller.config["schedule_enabled"] = schedule_enabled
            
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                enabled = f'{day}_enabled' in request.form
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
    
    schedule_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bluetooth IDS - Schedule Management</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #333; margin-bottom: 30px; }
            .nav { text-align: center; margin-bottom: 20px; padding: 10px 0; }
            .nav a { 
                display: inline-block;
                margin: 5px 8px; 
                text-decoration: none; 
                color: #007bff; 
                padding: 10px 16px; 
                border: 2px solid #007bff; 
                border-radius: 6px;
                min-width: 80px;
                text-align: center;
                font-weight: bold;
            }
            .nav a:hover { background-color: #007bff; color: white; }
            .schedule-control { margin-bottom: 30px; padding: 20px; background: #f8f9fa; border-radius: 6px; border: 1px solid #dee2e6; }
            .day-schedule { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 6px; background: #fff; }
            .day-header { font-weight: bold; color: #333; margin-bottom: 10px; text-transform: capitalize; }
            .time-inputs { display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }
            .time-group { display: flex; align-items: center; gap: 5px; }
            input[type="time"] { padding: 5px; border: 1px solid #ccc; border-radius: 4px; }
            input[type="checkbox"] { transform: scale(1.2); }
            .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #0056b3; }
            .btn-success { background: #28a745; }
            .btn-success:hover { background: #1e7e34; }
            .status { padding: 10px; margin: 10px 0; border-radius: 4px; text-align: center; }
            .status.enabled { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status.disabled { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="header">Bluetooth IDS - Schedule Management</h1>
            
            <div class="nav">
                <a href="/">Dashboard</a>
                <a href="/schedule">Schedule</a>
                <a href="/settings">Settings</a>
                <a href="/voice">Voice</a>
            </div>

            <div class="schedule-control">
                <h2>Schedule Status</h2>
                <div class="status {{ 'enabled' if config.schedule_enabled else 'disabled' }}">
                    <strong>Schedule Function: {{ 'ENABLED' if config.schedule_enabled else 'DISABLED' }}</strong>
                </div>
                
                <form method="POST" style="margin-top: 20px;">
                    <label>
                        <input type="checkbox" name="schedule_enabled" {{ 'checked' if config.schedule_enabled else '' }}>
                        Enable Schedule-Based Arming
                    </label>
                    
                    <p><strong>Note:</strong> When schedule is enabled, manual arm/disarm creates temporary overrides until next schedule transition.</p>
            </div>

            <h2>Weekly Schedule Configuration</h2>
            
                {% for day, settings in config.schedule.items() %}
                <div class="day-schedule">
                    <div class="day-header">{{ day.title() }}</div>
                    <div class="time-inputs">
                        <label>
                            <input type="checkbox" name="{{ day }}_enabled" {{ 'checked' if settings.enabled else '' }}>
                            Enabled
                        </label>
                        <div class="time-group">
                            <label>Start:</label>
                            <input type="time" name="{{ day }}_start" value="{{ settings.start }}">
                        </div>
                        <div class="time-group">
                            <label>End:</label>
                            <input type="time" name="{{ day }}_end" value="{{ settings.end }}">
                        </div>
                    </div>
                </div>
                {% endfor %}
                
                <div style="text-align: center; margin-top: 30px;">
                    <button type="submit" class="btn btn-success">Save Schedule Configuration</button>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(schedule_template, config=ids_controller.config)

@app.route('/settings', methods=['GET', 'POST'])
@auth.login_required
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
    
    settings_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bluetooth IDS - Settings</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #333; margin-bottom: 30px; }
            .nav { text-align: center; margin-bottom: 20px; padding: 10px 0; }
            .nav a { 
                display: inline-block;
                margin: 5px 8px; 
                text-decoration: none; 
                color: #007bff; 
                padding: 10px 16px; 
                border: 2px solid #007bff; 
                border-radius: 6px;
                min-width: 80px;
                text-align: center;
                font-weight: bold;
            }
            .nav a:hover { background-color: #007bff; color: white; }
            .form-group { margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 6px; border: 1px solid #dee2e6; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #495057; }
            .form-group input { padding: 8px 12px; border: 1px solid #ced4da; border-radius: 4px; width: 100px; }
            .btn { background: #28a745; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #1e7e34; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="header">Bluetooth IDS - Settings</h1>
            
            <div class="nav">
                <a href="/">Dashboard</a>
                <a href="/schedule">Schedule</a>
                <a href="/settings">Settings</a>
                <a href="/voice">Voice</a>
            </div>

            <form method="POST">
                <div class="form-group">
                    <label for="trigger_threshold">Trigger Threshold</label>
                    <input type="number" id="trigger_threshold" name="trigger_threshold" value="{{ config.trigger_threshold }}" min="1" max="300">
                    <span>seconds</span>
                </div>
                
                <div class="form-group">
                    <label for="scan_interval">Scan Interval</label>
                    <input type="number" id="scan_interval" name="scan_interval" value="{{ config.scan_interval }}" min="1" max="60">
                    <span>seconds</span>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <button type="submit" class="btn">Save Settings</button>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(settings_template, config=ids_controller.config)

@app.route('/voice')
@auth.login_required
def voice():
    """Voice call settings page"""
    try:
        with open('email_config.json', 'r') as f:
            config = json.load(f)
    except:
        config = {}
    
    voice_config = config.get('voice', {
        'enabled': True,
        'phone1': '',
        'phone2': '',
        'phone3': '',
        'message': 'phone intrusion detected. Alarm island, alarm island',
        'email1': '',
        'email2': '',
        'email3': ''
    })
    
    voice_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bluetooth IDS - Voice Settings</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #333; margin-bottom: 30px; }
            .nav { text-align: center; margin-bottom: 20px; padding: 10px 0; }
            .nav a { 
                display: inline-block;
                margin: 5px 8px; 
                text-decoration: none; 
                color: #007bff; 
                padding: 10px 16px; 
                border: 2px solid #007bff; 
                border-radius: 6px;
                min-width: 80px;
                text-align: center;
                font-weight: bold;
            }
            .nav a:hover { background-color: #007bff; color: white; }
            .form-section { margin-bottom: 25px; padding: 20px; background: #f8f9fa; border-radius: 6px; border: 1px solid #dee2e6; }
            .form-section h3 { margin-top: 0; color: #495057; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #495057; }
            .form-group input[type="tel"], .form-group input[type="email"], .form-group input[type="text"] { padding: 8px 12px; border: 1px solid #ced4da; border-radius: 4px; width: 250px; }
            .form-group input[type="checkbox"] { transform: scale(1.2); margin-right: 8px; }
            .btn { background: #28a745; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #1e7e34; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="header">Bluetooth IDS - Voice Call Settings</h1>
            
            <div class="nav">
                <a href="/">Dashboard</a>
                <a href="/schedule">Schedule</a>
                <a href="/settings">Settings</a>
                <a href="/voice">Voice</a>
            </div>

            <form action="/update_voice" method="POST">
                <div class="form-section">
                    <h3>Voice Call Configuration</h3>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="voice_enabled" {{ 'checked' if voice_config.enabled else '' }}>
                            Enable Voice Calls
                        </label>
                    </div>
                    
                    <div class="form-group">
                        <label for="message">Voice Message</label>
                        <input type="text" id="message" name="message" value="{{ voice_config.message }}" maxlength="60">
                    </div>
                </div>
                
                <div class="form-section">
                    <h3>Phone Numbers</h3>
                    <div class="form-group">
                        <label for="phone1">Phone 1</label>
                        <input type="tel" id="phone1" name="phone1" value="{{ voice_config.phone1 }}">
                    </div>
                    <div class="form-group">
                        <label for="phone2">Phone 2</label>
                        <input type="tel" id="phone2" name="phone2" value="{{ voice_config.phone2 }}">
                    </div>
                    <div class="form-group">
                        <label for="phone3">Phone 3</label>
                        <input type="tel" id="phone3" name="phone3" value="{{ voice_config.phone3 }}">
                    </div>
                </div>
                
                <div class="form-section">
                    <h3>Email Alerts</h3>
                    <div class="form-group">
                        <label for="email1">Email 1</label>
                        <input type="email" id="email1" name="email1" value="{{ voice_config.email1 }}">
                    </div>
                    <div class="form-group">
                        <label for="email2">Email 2</label>
                        <input type="email" id="email2" name="email2" value="{{ voice_config.email2 }}">
                    </div>
                    <div class="form-group">
                        <label for="email3">Email 3</label>
                        <input type="email" id="email3" name="email3" value="{{ voice_config.email3 }}">
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <button type="submit" class="btn">Save Voice Settings</button>
                </div>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(voice_template, voice_config=voice_config)

@app.route('/update_voice', methods=['POST'])
@auth.login_required
def update_voice():
    """Update voice call settings"""
    try:
        try:
            with open('email_config.json', 'r') as f:
                config = json.load(f)
        except:
            config = {}
        
        config['voice'] = {
            'enabled': 'voice_enabled' in request.form,
            'phone1': request.form.get('phone1', '').strip(),
            'phone2': request.form.get('phone2', '').strip(),
            'phone3': request.form.get('phone3', '').strip(),
            'message': request.form.get('message', '')[:60],
            'email1': request.form.get('email1', '').strip(),
            'email2': request.form.get('email2', '').strip(),
            'email3': request.form.get('email3', '').strip()
        }
        
        with open('email_config.json', 'w') as f:
            json.dump(config, f, indent=4)
        
        return redirect(url_for('voice'))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/test_voice', methods=['POST'])
@auth.login_required
def test_voice():
    """Test voice call functionality"""
    phone = request.json.get('phone', '')
    if not phone:
        return jsonify({'success': False, 'message': 'Phone number required'})
    
    try:
        with open('email_config.json', 'r') as f:
            config = json.load(f)
        
        msg = EmailMessage()
        msg.set_content('Test call from security system')
        msg['Subject'] = 'Voice Test'
        msg['From'] = config['sender_email']
        msg['To'] = f"{phone}@voice.clicksend.com"
        
        server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
        server.starttls()
        server.login(config['sender_email'], config['sender_password'])
        server.send_message(msg)
        server.quit()
        
        return jsonify({'success': True, 'message': 'Test call sent!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
