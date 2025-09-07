#!/usr/bin/env python3
"""
Remote Site Bluetooth Intrusion Detection - Fixed Version
Integrates with web dashboard arm/disarm functionality
"""

import asyncio
import csv
import logging
import time
from datetime import datetime
import signal
import sys
import os
import subprocess
import json

import RPi.GPIO as GPIO
from bleak import BleakScanner

class RemoteSiteIDS:
    def __init__(self):
        # Configuration
        self.trigger_threshold = 45  # seconds
        self.scan_interval = 8       # seconds between scans
        self.alarm_duration = 0      # 0 = no auto-stop
        self.relay_pin = 18
        
        # State tracking
        self.running = True
        self.alarm_active = False
        self.first_detection_time = None
        self.detected_devices = {}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('remote_ids.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.relay_pin, GPIO.OUT)
        GPIO.output(self.relay_pin, GPIO.LOW)
        self.logger.info("GPIO setup complete - Pin 18 ready")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def get_pi_mac(self):
        """Get Pi's Bluetooth MAC address to ignore it"""
        try:
            result = subprocess.run(['/usr/bin/hciconfig', 'hci0'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'BD Address:' in line:
                    mac = line.split('BD Address: ')[1].split()[0].upper()
                    self.logger.info(f"Pi's Bluetooth MAC: {mac} (will be ignored)")
                    return mac
        except Exception as e:
            self.logger.error(f"Error getting Pi MAC: {e}")
        return None
    
    def is_armed(self):
        """Check if system is armed by querying VPS"""
        try:
            import requests
            response = requests.get(
                'https://admin.securecaller.online/api/status',
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                armed = data.get("armed", False)
                self.logger.debug(f"VPS armed status: {armed}")
                return armed
            else:
                self.logger.debug(f"VPS status check failed: {response.status_code}")
                return False
        except Exception as e:
            self.logger.debug(f"Could not check VPS armed state: {e}")
            return False
    
    async def scan_devices(self):
        """Scan for Bluetooth devices"""
        try:
            devices = await BleakScanner.discover(timeout=5.0, return_adv=True)
            found_devices = {}
            pi_mac = self.get_pi_mac()
            
            for device, adv_data in devices.items():
                # Handle device data properly
                if isinstance(device, str):
                    mac = device.upper()
                    name = "Unknown"
                else:
                    mac = device.address.upper()
                    name = device.name or "Unknown"
                
                # Skip Pi's own Bluetooth
                if mac == pi_mac:
                    continue
                    
                rssi = adv_data.rssi if hasattr(adv_data, 'rssi') else -100
                
                found_devices[mac] = {
                    'name': name,
                    'signal': rssi,
                    'last_seen': datetime.now()
                }
            
            return found_devices
            
        except Exception as e:
            self.logger.error(f"Scan error: {e}")
            return {}
    
    def log_event(self, event_type, details):
        """Log detection events to CSV"""
        try:
            with open('remote_detections.csv', 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([datetime.now().isoformat(), event_type, details])
        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
    
    def trigger_alarm(self, device_count):
        """Trigger alarm and send notifications"""
        if self.alarm_active:
            return
            
        self.alarm_active = True
        self.logger.warning(f"🚨 ALARM TRIGGERED! {device_count} device(s) detected for {self.trigger_threshold}+ seconds")
        
        # Activate relay
        GPIO.output(self.relay_pin, GPIO.HIGH)
        
        # Create device list for notifications
        device_list = "\n".join([f"- {info['name']} ({mac}) - {info['signal']}dBm" 
                                for mac, info in self.detected_devices.items()])
        
        # Send notifications
        self.send_email_alert(device_count, device_list)
        self.send_voice_alerts(device_count, device_list)
        
        self.log_event("ALARM_TRIGGERED", f"{device_count} devices detected")
    
    def stop_alarm(self):
        """Stop the alarm"""
        if self.alarm_active:
            GPIO.output(self.relay_pin, GPIO.LOW)
            self.alarm_active = False
            self.logger.info("🔇 Alarm stopped")
    
    def send_email_alert(self, device_count, device_list):
        """Send email notification"""
        try:
            import smtplib
            from email.message import EmailMessage
            
            # Load email config
            with open("/home/andrewdarr/intrusion/email_config.json", "r") as f:
                email_config = json.load(f)
            
            if not email_config.get("email_enabled", False):
                return
            
            # Create message
            msg = EmailMessage()
            body = f"""🚨 SECURITY ALERT 🚨

INTRUSION DETECTED at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Number of devices detected: {device_count}
Device ID: {email_config.get("device_id", "Unknown Device")}
Device details:
{device_list}

System Status: ARMED and TRIGGERED
Relay: ACTIVATED
"""
            
            msg.set_content(body)
            msg["Subject"] = email_config["subject"]
            msg["From"] = email_config["sender_email"]
            msg["To"] = email_config["recipient_email"]
            
            # Send email
            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
            server.starttls()
            server.login(email_config["sender_email"], email_config["sender_password"])
            server.send_message(msg)
            server.quit()
            
            self.logger.info("📧 Email alert sent!")
            
        except Exception as e:
            self.logger.error(f"📧 Email failed: {e}")
    
    def send_voice_alerts(self, device_count, device_list):
        """Send voice call notifications"""
        try:
            import smtplib
            from email.message import EmailMessage
            
            # Load email config (which contains voice settings)
            with open("/home/andrewdarr/intrusion/email_config.json", "r") as f:
                email_config = json.load(f)
            
            voice_config = email_config.get("voice", {})
            
            if not voice_config.get("enabled", False):
                self.logger.info("Voice calls disabled, skipping...")
                return
            
            # Get phone numbers and message
            phone_numbers = [
                voice_config.get("phone1", ""),
                voice_config.get("phone2", ""),
                voice_config.get("phone3", "")
            ]
            message = voice_config.get("message", "Security alert detected")[:60]
            
            success_count = 0
            for phone in phone_numbers:
                if phone.strip():
                    try:
                        # Convert to E.164 format for Telnyx
                        import requests
                        phone_formatted = phone.strip()
                        if phone_formatted.startswith('0'):
                            phone_formatted = '+61' + phone_formatted[1:]
                        elif not phone_formatted.startswith('+'):
                            phone_formatted = '+' + phone_formatted
                        
                        # Call VPS Telnyx API
                        response = requests.post(
                            'https://admin.securecaller.online/api/make-call',
                            json={
                                'phone_numbers': [phone_formatted],
                                'message': message,
                                'device_id': 'btids001'
                            },
                            timeout=10
                        )
                        
                        if response.status_code != 200:
                            raise Exception(f"API returned {response.status_code}")
                        
                        self.logger.info(f"📞 Voice call sent to {phone}")
                        success_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"📞 Voice call failed to {phone}: {e}")
            
            self.logger.info(f"📞 Voice alerts completed: {success_count} calls sent")
            
            # Send additional email notifications
            self.send_additional_emails(device_count, device_list, email_config)
            
        except Exception as e:
            self.logger.error(f"📞 Voice alert system failed: {e}")
    
    def send_additional_emails(self, device_count, device_list, email_config):
        """Send alerts to additional email addresses"""
        try:
            import smtplib
            from email.message import EmailMessage
            
            voice_config = email_config.get("voice", {})
            additional_emails = [
                voice_config.get("email1", ""),
                voice_config.get("email2", ""),
                voice_config.get("email3", "")
            ]
            
            success_count = 0
            for email in additional_emails:
                if email.strip():
                    try:
                        # Create email message
                        msg = EmailMessage()
                        email_body = f"""
SECURITY ALERT - Bluetooth Intrusion Detected

Device ID: {email_config.get('device_id', 'BT-IDS')}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Devices Detected: {device_count}

Device Details:
{device_list}

This is an automated alert from your Bluetooth Intrusion Detection System.
"""
                        msg.set_content(email_body)
                        msg["Subject"] = email_config.get("subject", "Security Alert")
                        msg["From"] = email_config["sender_email"]
                        msg["To"] = email.strip()
                        
                        # Send email
                        server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
                        server.starttls()
                        server.login(email_config["sender_email"], email_config["sender_password"])
                        server.send_message(msg)
                        server.quit()
                        
                        self.logger.info(f"📧 Additional email sent to {email}")
                        success_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"📧 Email failed to {email}: {e}")
            
            self.logger.info(f"📧 Additional emails completed: {success_count} emails sent")
            
        except Exception as e:
            self.logger.error(f"📧 Additional email system failed: {e}")
    
    def process_detections(self, found_devices):
        """Process detected devices and trigger alarms if needed"""
        current_time = datetime.now()
        
        if found_devices:
            # Devices detected
            if self.first_detection_time is None:
                self.first_detection_time = current_time
                self.logger.info(f"🔍 FIRST DETECTION: {len(found_devices)} device(s) found")
                self.log_event("FIRST_DETECTION", f"{len(found_devices)} devices")
                
                for mac, info in found_devices.items():
                    self.logger.info(f"   Device: {info['name']} ({mac}) - {info['signal']}dBm")
            
            self.detected_devices.update(found_devices)
            
            # Check if we should trigger alarm
            if not self.alarm_active:
                time_elapsed = (current_time - self.first_detection_time).total_seconds()
                self.logger.info(f"⏱️  Devices present for {time_elapsed:.1f}s (trigger at {self.trigger_threshold}s)")
                
                if time_elapsed >= self.trigger_threshold:
                    self.trigger_alarm(len(found_devices))
                    
        else:
            # No devices detected
            if self.first_detection_time is not None:
                self.logger.info("✅ No devices detected - clearing detection state")
                self.log_event("DETECTION_CLEARED", "No devices found")
                self.first_detection_time = None
                self.detected_devices = {}
                self.stop_alarm()
    
    async def monitoring_loop(self):
        """Main monitoring loop with armed state checking"""
        self.logger.info("🔥  Remote Site Bluetooth IDS Started")
        self.logger.info(f"⚙️  Configuration: {self.trigger_threshold}s trigger, {self.alarm_duration}s alarm duration")
        self.logger.info("👀 Monitoring for Bluetooth devices...")
        
        while self.running:
            try:
                # Check if system is armed
                if not self.is_armed():
                    # System is disarmed, clear any active detection state
                    if self.first_detection_time is not None:
                        self.logger.info("🔓 System disarmed - clearing detection state")
                        self.first_detection_time = None
                        self.detected_devices = {}
                        self.stop_alarm()
                    
                    await asyncio.sleep(self.scan_interval)
                    continue
                
                # System is armed, proceed with detection
                found_devices = await self.scan_devices()
                self.process_detections(found_devices)
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)
    
    def signal_handler(self, sig, frame):
        """Handle shutdown signals"""
        self.logger.info("Received shutdown signal...")
        self.shutdown()
    
    def shutdown(self):
        """Clean shutdown"""
        self.logger.info("🔥 Shutting down Remote Site IDS...")
        self.running = False
        self.stop_alarm()
        GPIO.cleanup()
        self.logger.info("Shutdown complete")
        sys.exit(0)

async def main():
    print("🔥  Remote Site Bluetooth Intrusion Detection")
    print("=" * 50)
    print("Mode: Respects web dashboard ARM/DISARM state")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    ids = RemoteSiteIDS()
    
    try:
        await ids.monitoring_loop()
    except KeyboardInterrupt:
        ids.shutdown()
    except Exception as e:
        ids.logger.error(f"Fatal error: {e}")
        ids.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
