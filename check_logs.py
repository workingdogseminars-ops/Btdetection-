import subprocess
import re
from datetime import datetime, timedelta

print("=== BLUETOOTH IDS LOG CHECKER ===\n")

# Get recent logs from systemd service
try:
    result = subprocess.run(['sudo', 'journalctl', '-u', 'bluetooth-ids.service', '--since', '10 minutes ago'], 
                          capture_output=True, text=True)
    
    if result.stdout:
        print("? Recent System Logs (last 10 minutes):")
        print("=" * 50)
        
        lines = result.stdout.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['email', 'voice', 'alert', 'error', 'failed']):
                print(line)
        
        print("\n" + "=" * 50)
    else:
        print("No recent logs found")

except Exception as e:
    print(f"Error getting systemd logs: {e}")

# Check if there's a local log file
try:
    import os
    log_files = [f for f in os.listdir('.') if f.endswith('.log')]
    
    if log_files:
        print(f"\n? Found log files: {log_files}")
        
        for log_file in log_files:
            print(f"\n? Recent entries from {log_file}:")
            print("-" * 30)
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Show last 20 lines
                for line in lines[-20:]:
                    if any(keyword in line.lower() for keyword in ['email', 'voice', 'alert', 'error']):
                        print(line.strip())

except Exception as e:
    print(f"Error checking log files: {e}")

# Check if the detection system is actually running
try:
    result = subprocess.run(['pgrep', '-f', 'remote_site_with_email.py'], 
                          capture_output=True, text=True)
    
    if result.stdout.strip():
        print(f"\n? Detection system is running (PID: {result.stdout.strip()})")
    else:
        print("\n? Detection system is NOT running!")

except Exception as e:
    print(f"Error checking process: {e}")

print("\n=== END LOG REPORT ===")
