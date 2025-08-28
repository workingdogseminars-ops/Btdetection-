#!/usr/bin/env python3
"""
Bluetooth IDS Web Dashboard
Simple web interface for ARM/DISARM and scheduling
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_httpauth import HTTPBasicAuth
import json
import os
import subprocess
import signal
from datetime import datetime
import smtplib
from email.message import EmailMessage

app = Flask(__name__)

# Setup HTTP Basic Authentication
auth = HTTPBasicAuth()

# Default credentials (customers should change these)
@auth.verify_password
def verify_password(username, password):
    # Load credentials from config file
    try:
        with open("web_auth.json", "r") as f:
            creds = json.load(f)
            return username == creds.get("username", "admin") and password == creds.get("password", "admin123")
    except:
        # Fallback default credentials
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
@auth.login_required
def dashboard():
    """Main dashboard page"""
    status = ids_controller.get_system_status()
    return render_template('dashboard.html', 
                         status=status, 
                         config=ids_controller.config)


@app.route('/arm', methods=['POST'])
@auth.login_required
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
@auth.login_required
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
    
    return render_template('settings.html', config=ids_controller.config)


@app.route('/voice')
@auth.login_required
def voice():
    """Voice call settings page"""
    # Load existing email config which will contain voice settings
    try:
        with open('email_config.json', 'r') as f:
            config = json.load(f)
    except:
        config = {}
    
    # Get voice settings or set defaults
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
    
    return render_template('voice.html', voice_config=voice_config)

@app.route('/update_voice', methods=['POST'])
@auth.login_required
def update_voice():
    """Update voice call settings"""
    try:
        # Load existing config
        try:
            with open('email_config.json', 'r') as f:
                config = json.load(f)
        except:
            config = {}
        
        # Update voice settings
        config['voice'] = {
            'enabled': 'voice_enabled' in request.form,
            'phone1': request.form.get('phone1', '').strip(),
            'phone2': request.form.get('phone2', '').strip(),
            'phone3': request.form.get('phone3', '').strip(),
            'message': request.form.get('message', '')[:60],  # Limit to 60 chars
            'email1': request.form.get('email1', '').strip(),
            'email2': request.form.get('email2', '').strip(),
            'email3': request.form.get('email3', '').strip()
        }
        
        # Save config
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
        # Load email config
        with open('email_config.json', 'r') as f:
            config = json.load(f)
        
        # Send test voice call
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
