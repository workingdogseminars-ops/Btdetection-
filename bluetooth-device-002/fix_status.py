import re

# Read the current web_dashboard.py
with open('web_dashboard.py', 'r') as f:
    content = f.read()

# Replace the ARM function to properly sync status
arm_function = '''@app.route('/arm', methods=['POST'])
def arm_system():
    """ARM the system"""
    try:
        # Start the IDS script
        subprocess.Popen(["/bin/bash", "-c", "cd /home/andrewdarr/intrusion && source .venv/bin/activate && python3 remote_site_continuous.py"], cwd="/home/andrewdarr/intrusion")
        
        # Wait a moment then check if it actually started
        import time
        time.sleep(2)
        result = subprocess.run(['/usr/bin/pgrep', '-f', 'remote_site_continuous.py'], capture_output=True, text=True)
        actually_running = len(result.stdout.strip()) > 0
        
        ids_controller.config["armed"] = actually_running
        ids_controller.save_config()
        
        return jsonify({"status": "success", "message": "System ARMED" if actually_running else "Failed to start"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})'''

# Replace the ARM function
content = re.sub(r"@app\.route\('/arm'.*?except Exception as e:\s+return jsonify.*?\n", arm_function + '\n\n', content, flags=re.DOTALL)

# Write back
with open('web_dashboard.py', 'w') as f:
    f.write(content)
