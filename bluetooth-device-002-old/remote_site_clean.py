#!/usr/bin/env python3
"""
Remote Site Bluetooth Intrusion Detection - Clean Version
Simple mode: Any Bluetooth detection = Alarm after 45 seconds
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

import RPi.GPIO as GPIO
from bleak import BleakScanner

class RemoteSiteIDS:
    def __init__(self):
        # Configuration
        self.trigger_threshold = 45
        self.scan_duration = 5
        self.scan_interval = 3
        self.relay_pin = 18
        self.relay_active_high = True
        self.alarm_duration = 300
        
        # Setup logging first
        self.setup_logging()
        
        # Get Pi's MAC
        self.pi_bluetooth_mac = self.get_pi_mac()
        
        # State tracking
        self.first_detection_time = None
        self.alarm_active = False
        self.running = True
        self.detected_devices = {}
        
        # Setup GPIO
        self.setup_gpio()
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('remote_ids.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_pi_mac(self):
        try:
            result = subprocess.run(['hciconfig', 'hci0'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'BD Address:' in line:
                    mac = line.split('BD Address: ')[1].split()[0].upper()
                    self.logger.info(f"Pi's Bluetooth MAC: {mac} (will be ignored)")
                    return mac
        except Exception as e:
            self.logger.error(f"Could not get Pi MAC: {e}")
        return None
    
    def setup_gpio(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.relay_pin, GPIO.OUT)
            GPIO.output(self.relay_pin, not self.relay_active_high)
            self.logger.info(f"GPIO setup complete - Pin {self.relay_pin} ready")
        except Exception as e:
            self.logger.error(f"GPIO setup failed: {e}")
    
    def log_event(self, event_type, details=""):
        try:
            file_exists = os.path.exists('remote_detections.csv')
            with open('remote_detections.csv', 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Timestamp', 'Event', 'Details'])
                writer.writerow([datetime.now().isoformat(), event_type, details])
        except Exception as e:
            self.logger.error(f"Logging error: {e}")
    
    def trigger_alarm(self, device_count):
        if self.alarm_active:
            return
        
        self.alarm_active = True
        
        try:
            GPIO.output(self.relay_pin, self.relay_active_high)
            self.logger.warning(f"? ALARM TRIGGERED! {device_count} device(s) detected for {self.trigger_threshold}+ seconds")
            self.log_event("ALARM_TRIGGERED", f"{device_count} devices detected")
            
            # Auto-off timer
            def auto_off():
                time.sleep(self.alarm_duration)
                self.stop_alarm()
            
            import threading
            threading.Thread(target=auto_off, daemon=True).start()
            
        except Exception as e:
            self.logger.error(f"Alarm trigger error: {e}")
    
    def stop_alarm(self):
        if self.alarm_active:
            try:
                GPIO.output(self.relay_pin, not self.relay_active_high)
                self.alarm_active = False
                self.logger.info("Alarm stopped")
                self.log_event("ALARM_STOPPED", "Auto-off timer")
            except Exception as e:
                self.logger.error(f"Error stopping alarm: {e}")
        else:
            self.alarm_active = False
    
    async def scan_devices(self):
        try:
            devices = await BleakScanner.discover(
                timeout=self.scan_duration,
                return_adv=True
            )
            
            found_devices = {}
            for mac_address, (device, adv_data) in devices.items():
                mac = mac_address.upper()
                
                # Skip Pi's own MAC
                if mac == self.pi_bluetooth_mac:
                    continue
                
                name = device.name or "Unknown"
                rssi = adv_data.rssi
                
                found_devices[mac] = {
                    'name': name,
                    'signal': rssi,
                    'timestamp': datetime.now()
                }
            
            return found_devices
            
        except Exception as e:
            self.logger.error(f"Scan error: {e}")
            return {}
    
    def process_detections(self, found_devices):
        current_time = datetime.now()
        
        if found_devices:
            # Devices detected
            if self.first_detection_time is None:
                self.first_detection_time = current_time
                self.logger.info(f"? FIRST DETECTION: {len(found_devices)} device(s) found")
                self.log_event("FIRST_DETECTION", f"{len(found_devices)} devices")
                
                for mac, info in found_devices.items():
                    self.logger.info(f"   Device: {info['name']} ({mac}) - {info['signal']}dBm")
            
            self.detected_devices.update(found_devices)
            
            # Check if we should trigger alarm
            if not self.alarm_active:
                time_elapsed = (current_time - self.first_detection_time).total_seconds()
                self.logger.info(f"??  Devices present for {time_elapsed:.1f}s (trigger at {self.trigger_threshold}s)")
                
                if time_elapsed >= self.trigger_threshold:
                    self.trigger_alarm(len(found_devices))
                    
        else:
            # No devices detected
            if self.first_detection_time is not None:
                self.logger.info("? No devices detected - clearing detection state")
                self.log_event("DETECTION_CLEARED", "No devices found")
                self.first_detection_time = None
                self.detected_devices = {}
    
    async def monitoring_loop(self):
        self.logger.info("??  Remote Site Bluetooth IDS Started")
        self.logger.info(f"??  Configuration: {self.trigger_threshold}s trigger, {self.alarm_duration}s alarm duration")
        self.logger.info("? Monitoring for ANY Bluetooth devices...")
        
        while self.running:
            try:
                found_devices = await self.scan_devices()
                self.process_detections(found_devices)
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)
    
    def signal_handler(self, sig, frame):
        self.logger.info("Received shutdown signal...")
        self.shutdown()
    
    def shutdown(self):
        self.logger.info("? Shutting down Remote Site IDS...")
        self.running = False
        self.stop_alarm()
        GPIO.cleanup()
        self.logger.info("Shutdown complete")
        sys.exit(0)

async def main():
    print("??  Remote Site Bluetooth Intrusion Detection")
    print("=" * 50)
    print("Mode: ANY Bluetooth device = Alarm after 45 seconds")
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
