#!/usr/bin/env python3
"""
Schedule Daemon for Bluetooth IDS
Automatically starts/stops monitoring script based on schedule and manual overrides
"""

import json
import os
import subprocess
import time
import logging
import signal
import sys
from datetime import datetime, timedelta

class ScheduleDaemon:
    def __init__(self):
        self.config_file = "/home/andrewdarr/intrusion/ids_config.json"
        self.monitoring_script = "/home/andrewdarr/intrusion/remote_site_with_email.py"
        self.venv_path = "/home/andrewdarr/intrusion/.venv"
        self.working_dir = "/home/andrewdarr/intrusion"
        
        self.running = True
        self.last_effective_status = None
        self.last_config_check = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - DAEMON - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/home/andrewdarr/intrusion/schedule_daemon.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}
    
    def save_config(self, config):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    def get_next_schedule_transition_time(self, config):
        """Calculate when the next schedule transition will occur"""
        try:
            current_time = datetime.now()
            
            # Check today and next few days for transitions
            for days_ahead in range(0, 7):  # Check up to 1 week ahead
                check_date = current_time.date() + timedelta(days=days_ahead)
                check_day = check_date.strftime('%A').lower()
                
                day_schedule = config.get("schedule", {}).get(check_day, {})
                if not day_schedule.get("enabled", False):
                    continue
                
                start_time_str = day_schedule.get("start", "18:00")
                end_time_str = day_schedule.get("end", "06:00")
                
                start_time = datetime.combine(check_date, 
                    datetime.strptime(start_time_str, '%H:%M').time())
                end_time = datetime.combine(check_date, 
                    datetime.strptime(end_time_str, '%H:%M').time())
                
                # Handle overnight schedules
                if start_time.time() > end_time.time():
                    end_time += timedelta(days=1)
                
                # Find next transition after current time
                if days_ahead == 0:  # Today
                    if current_time < start_time:
                        return start_time
                    elif current_time < end_time:
                        return end_time
                else:  # Future days
                    return start_time
            
            return None
        except Exception as e:
            self.logger.error(f"Error calculating next transition: {e}")
            return None
    
    def check_override_expiry(self, config):
        """Check if manual override has expired"""
        if not config.get("manual_override", False):
            return config, False
        
        override_expires = config.get("override_expires")
        if not override_expires:
            return config, False
        
        try:
            expire_time = datetime.fromisoformat(override_expires)
            current_time = datetime.now()
            
            if current_time >= expire_time:
                # Override has expired, revert to schedule
                config["manual_override"] = False
                config["override_expires"] = None
                self.logger.info(f"Manual override expired, reverting to schedule control")
                return config, True
        except Exception as e:
            self.logger.error(f"Error checking override expiry: {e}")
        
        return config, False
    
    def check_schedule_status(self, config):
        """Check if system should be armed based on current schedule"""
        if not config.get("schedule_enabled", False):
            return False, False
        
        try:
            current_time = datetime.now()
            current_day = current_time.strftime('%A').lower()
            current_time_obj = current_time.time()
            
            day_schedule = config.get("schedule", {}).get(current_day, {})
            
            if not day_schedule.get("enabled", False):
                return True, False
            
            start_time_str = day_schedule.get("start", "18:00")
            end_time_str = day_schedule.get("end", "06:00")
            
            start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time_str, '%H:%M').time()
            
            # Handle overnight schedules
            if start_time_obj > end_time_obj:
                should_be_armed = current_time_obj >= start_time_obj or current_time_obj <= end_time_obj
            else:
                should_be_armed = start_time_obj <= current_time_obj <= end_time_obj
            
            return True, should_be_armed
            
        except Exception as e:
            self.logger.error(f"Error checking schedule: {e}")
            return False, False
    
    def get_effective_arm_status(self, config):
        """Get effective arm status considering manual override and schedule"""
        # If manual override is active, use manual setting
        if config.get("manual_override", False):
            return config.get("armed", False), "manual_override"
        
        # Otherwise, use schedule if enabled
        schedule_enabled, should_be_armed_by_schedule = self.check_schedule_status(config)
        if schedule_enabled:
            return should_be_armed_by_schedule, "schedule"
        else:
            return config.get("armed", False), "manual"
    
    def is_monitoring_script_running(self):
        """Check if monitoring script is currently running"""
        try:
            result = subprocess.run(['/usr/bin/pgrep', '-f', 'remote_site_with_email.py'], 
                                  capture_output=True, text=True)
            return len(result.stdout.strip()) > 0
        except:
            return False
    
    def start_monitoring_script(self):
        """Start the monitoring script"""
        try:
            cmd = f"cd {self.working_dir} && source {self.venv_path}/bin/activate && python3 {self.monitoring_script}"
            subprocess.Popen(["/bin/bash", "-c", cmd], cwd=self.working_dir)
            
            # Wait and verify it started
            time.sleep(3)
            if self.is_monitoring_script_running():
                self.logger.info("Monitoring script started successfully")
                return True
            else:
                self.logger.error("Failed to start monitoring script")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting monitoring script: {e}")
            return False
    
    def stop_monitoring_script(self):
        """Stop the monitoring script"""
        try:
            subprocess.run(['/usr/bin/pkill', '-f', 'remote_site_with_email.py'])
            time.sleep(2)
            
            if not self.is_monitoring_script_running():
                self.logger.info("Monitoring script stopped successfully")
                return True
            else:
                self.logger.warning("Monitoring script may still be running")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping monitoring script: {e}")
            return False
    
    def daemon_loop(self):
        """Main daemon loop"""
        self.logger.info("Schedule Daemon started")
        
        while self.running:
            try:
                # Load current configuration
                config = self.load_config()
                config_changed = False
                
                # Check if override has expired
                config, override_expired = self.check_override_expiry(config)
                if override_expired:
                    config_changed = True
                
                # Get effective arm status
                should_be_armed, control_source = self.get_effective_arm_status(config)
                script_is_running = self.is_monitoring_script_running()
                
                # Log status changes
                if self.last_effective_status != should_be_armed:
                    status_text = "ARMED" if should_be_armed else "DISARMED"
                    self.logger.info(f"Effective status changed to {status_text} (source: {control_source})")
                    self.last_effective_status = should_be_armed
                
                # Debug logging
                self.logger.info(f"Debug: should_be_armed={should_be_armed}, script_is_running={script_is_running}")
                
                # Manage script lifecycle
                if should_be_armed and not script_is_running:
                    self.logger.info("System should be armed but script not running - starting monitoring")
                    self.start_monitoring_script()
                    
                elif not should_be_armed and script_is_running:
                    self.logger.info("System should be disarmed but script running - stopping monitoring")
                    self.stop_monitoring_script()
                
                # Update next transition time for manual overrides
                if config.get("schedule_enabled", False):
                    next_transition = self.get_next_schedule_transition_time(config)
                    if next_transition and not config.get("manual_override", False):
                        config["next_transition"] = next_transition.isoformat()
                        config_changed = True
                
                # Save config if changes were made
                if config_changed:
                    self.save_config(config)
                
                # Sleep before next check
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Daemon loop error: {e}")
                time.sleep(60)  # Wait longer on errors
    
    def signal_handler(self, sig, frame):
        self.logger.info("Received shutdown signal")
        self.shutdown()
    
    def shutdown(self):
        self.logger.info("Shutting down Schedule Daemon")
        self.running = False
        sys.exit(0)

if __name__ == "__main__":
    print("Starting Bluetooth IDS Schedule Daemon...")
    daemon = ScheduleDaemon()
    
    try:
        daemon.daemon_loop()
    except KeyboardInterrupt:
        daemon.shutdown()
    except Exception as e:
        daemon.logger.error(f"Fatal daemon error: {e}")
        daemon.shutdown()
