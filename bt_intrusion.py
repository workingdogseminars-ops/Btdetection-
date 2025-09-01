#!/usr/bin/env python3
"""
Modern Bluetooth Intrusion Detection System using Bleak
Handles MAC randomization and auto-learning baseline devices
"""

import asyncio
import json
import csv
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Set, Optional
import signal
import sys
import os
from dataclasses import dataclass, asdict
from collections import defaultdict

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("Warning: RPi.GPIO not available. GPIO functionality disabled.")

from bleak import BleakScanner

@dataclass
class DeviceInfo:
    """Information about a detected device"""
    mac: str
    name: str
    first_seen: datetime
    last_seen: datetime
    signal_strength: int
    detection_count: int = 1
    triggered: bool = False
    is_baseline: bool = False

class ModernBluetoothIDS:
    def __init__(self, config_file="bt_ids_config.json"):
        self.config_file = config_file
        self.load_config()

    def get_device_pattern(self, mac):
        """Get device pattern - simplified version"""
        return {"mac": mac, "seen_count": 1}

    def is_device_suspicious(self, device_info):
        """Check if device is suspicious - simplified version"""
        return not device_info.is_baseline
        
        # Device tracking
        self.detected_devices: Dict[str, DeviceInfo] = {}
        self.baseline_devices: Set[str] = set()  # Known device patterns
        self.device_patterns: Dict[str, int] = defaultdict(int)  # Name patterns
        
        # Learning mode
        self.learning_mode = False
        self.learning_start_time = None
        
        # System state
        self.running = True
        self.alarm_active = False
        
        # Setup components
        self.setup_logging()
        if GPIO_AVAILABLE:
            self.setup_gpio()
        
        # Load saved data
        self.load_baseline_devices()
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_config(self):
        """Load configuration with smart defaults"""
        default_config = {
            "learning_duration": 120,    # 2 minutes baseline learning
            "scan_duration": 10,         # seconds per scan
            "scan_interval": 5,          # seconds between scans
            "trigger_threshold": 30,     # seconds before alarm
            "confidence_threshold": 3,   # detections needed for confidence
            "signal_threshold": -80,     # minimum signal strength (dBm)
            "relay_pin": 18,
            "relay_active_high": True,
            "alarm_duration": 300,       # 5 minutes
            "log_file": "detections.csv",
            "baseline_file": "baseline_devices.json",
            "auto_learn_quiet_time": 1800,  # 30 min quiet period for learning
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Error loading config: {e}")
        
        # Save current config
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        for key, value in default_config.items():
            setattr(self, key, value)
    
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bt_ids.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_gpio(self):
        """Setup GPIO for relay"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.relay_pin, GPIO.OUT)
            GPIO.output(self.relay_pin, not self.relay_active_high)
            self.logger.info(f"GPIO setup complete on pin {self.relay_pin}")
        except Exception as e:
            self.logger.error(f"GPIO setup failed: {e}")
    
    def load_baseline_devices(self):
        """Load baseline devices from previous learning"""
        if os.path.exists(self.baseline_file):
            try:
                with open(self.baseline_file, 'r') as f:
                    data = json.load(f)
                    self.baseline_devices = set(data.get('devices', []))
                    self.device_patterns = defaultdict(int, data.get('patterns', {}))
                self.logger.info(f"Loaded {len(self.baseline_devices)} baseline devices")
            except Exception as e:
                self.logger.error(f"Error loading baseline: {e}")
    
    def save_baseline_devices(self):
        """Save baseline devices for future runs"""
        try:
            data = {
                'devices': list(self.baseline_devices),
                'patterns': dict(self.device_patterns),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.baseline_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info("Baseline devices saved")
        except Exception as e:
            self.logger.error(f"Error saving baseline: {e}")
    
    async def scan_devices(self) -> Dict[str, DeviceInfo]:
        """Scan for Bluetooth devices using Bleak"""
        try:
            self.logger.debug("Starting BLE scan...")
            
            devices = await BleakScanner.discover(
                timeout=self.scan_duration,
                return_adv=True
            )
            
            found_devices = {}
            current_time = datetime.now()
            
            for device, adv_data in devices.items():
                # Handle both string MAC addresses and device objects
                if isinstance(device, str):
                    mac = device.upper()
                    name = getattr(adv_data, 'local_name', None) or "Unknown"
                else:
                    mac = device.address.upper()
                    name = device.name or "Unknown"
    
                rssi = adv_data.rssi if hasattr(adv_data, 'rssi') else -100
                
                # Create or update device info
                if mac in self.detected_devices:
                    device_info = self.detected_devices[mac]
                    device_info.last_seen = current_time
                    device_info.signal_strength = rssi
                    device_info.detection_count += 1
                else:
                    device_info = DeviceInfo(
                        mac=mac,
                        name=name,
                        first_seen=current_time,
                        last_seen=current_time,
                        signal_strength=rssi,
                        is_baseline=self.learning_mode
                    )
                
                found_devices[mac] = device_info
            
            self.logger.debug(f"Found {len(found_devices)} devices")
            return found_devices
            
        except Exception as e:
            self.logger.error(f"Scan error: {e}")
            return {}
    
    def log_event(self, device: DeviceInfo, event_type: str):
        """Log event to CSV"""
        try:
            file_exists = os.path.exists(self.log_file)
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        'Timestamp', 'MAC', 'Device Name', 'Event',
                        'Signal Strength', 'Detection Count', 'Learning Mode'
                    ])
                writer.writerow([
                    datetime.now().isoformat(),
                    device.mac,
                    device.name,
                    event_type,
                    device.signal_strength,
                    device.detection_count,
                    self.learning_mode
                ])
        except Exception as e:
            self.logger.error(f"Logging error: {e}")
    
    def start_learning_mode(self):
        """Start baseline learning mode"""
        self.learning_mode = True
        self.learning_start_time = datetime.now()
        self.logger.info(f"Starting {self.learning_duration}s baseline learning mode...")
        print(f"LEARNING MODE: Scanning for {self.learning_duration} seconds to establish baseline...")
    
    def stop_learning_mode(self):
        """Stop learning mode and save baseline"""
        self.learning_mode = False
        
        # Add all detected devices to baseline
        for mac, device in self.detected_devices.items():
            if device.is_baseline:
                self.baseline_devices.add(mac)
                pattern = self.get_device_pattern(device.name)
                self.device_patterns[pattern] += 1
        
        self.save_baseline_devices()
        self.logger.info(f"Learning complete. {len(self.baseline_devices)} baseline devices saved")
        print(f"LEARNING COMPLETE: {len(self.baseline_devices)} devices now in baseline")
    
    async def process_devices(self, found_devices: Dict[str, DeviceInfo]):
        """Process detected devices"""
        current_time = datetime.now()
        
        # Update device tracking
        for mac, device in found_devices.items():
            self.detected_devices[mac] = device
            
            # Log new devices
            if device.detection_count == 1:
                event_type = "BASELINE_DEVICE" if self.learning_mode else "NEW_DEVICE"
                self.log_event(device, event_type)
                status = "baseline" if self.learning_mode else "monitoring"
                self.logger.info(f"New device: {device.name} ({mac}) - {status}")
            
            # Check for alarm trigger (only when not learning)
            if not self.learning_mode and not device.triggered:
                time_present = (current_time - device.first_seen).total_seconds()
                
                if time_present >= self.trigger_threshold and self.is_device_suspicious(device):
                    device.triggered = True
                    self.trigger_alarm(device)
                    self.log_event(device, "ALARM_TRIGGERED")
        
        # Clean up old devices
        devices_to_remove = []
        for mac, device in self.detected_devices.items():
            if mac not in found_devices:
                time_since_seen = (current_time - device.last_seen).total_seconds()
                if time_since_seen > self.scan_interval * 5:  # Gone for 5 scan cycles
                    if device.triggered:
                        self.log_event(device, "DEVICE_LEFT")
                        self.logger.info(f"Device left: {device.name} ({mac})")
                    devices_to_remove.append(mac)
        
        for mac in devices_to_remove:
            del self.detected_devices[mac]
    
    async def monitoring_loop(self):
        """Main monitoring loop"""
        self.logger.info("Starting Bluetooth monitoring...")
        
        # Check if we should start in learning mode
        if not os.path.exists(self.baseline_file) or len(self.baseline_devices) == 0:
            self.start_learning_mode()
        
        while self.running:
            try:
                # Check if learning time is up
                if self.learning_mode and self.learning_start_time:
                    elapsed = (datetime.now() - self.learning_start_time).total_seconds()
                    if elapsed >= self.learning_duration:
                        self.stop_learning_mode()
                
                # Scan for devices
                found_devices = await self.scan_devices()
                
                # Process devices
                await self.process_devices(found_devices)
                
                # Wait before next scan
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)
    
    def print_status(self):
        """Print current system status"""
        print(f"\n{'='*50}")
        print(f"Bluetooth IDS STATUS")
        print(f"{'='*50}")
        print(f"Learning Mode: {'ACTIVE' if self.learning_mode else 'INACTIVE'}")
        print(f"Alarm Status:  {'TRIGGERED' if self.alarm_active else 'NORMAL'}")
        print(f"Baseline Devices: {len(self.baseline_devices)}")
        print(f"Currently Detected: {len(self.detected_devices)}")
        
        if self.detected_devices:
            print(f"\nDETECTED DEVICES:")
            for mac, device in self.detected_devices.items():
                status = "LEARNING" if self.learning_mode else ("TRIGGERED" if device.triggered else "MONITORING")
                age = (datetime.now() - device.first_seen).total_seconds()
                print(f"  {status} {device.name[:20]:<20} | {mac} | {age:>3.0f}s | {device.signal_strength}dBm")
        
        if self.learning_mode and self.learning_start_time:
            remaining = self.learning_duration - (datetime.now() - self.learning_start_time).total_seconds()
            print(f"\nLearning time remaining: {remaining:.0f} seconds")
        
        print(f"{'='*50}\n")
    
    def signal_handler(self, sig, frame):
        """Handle shutdown signals"""
        self.logger.info("Received shutdown signal...")
        self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down Bluetooth IDS...")
        self.running = False
        
        if self.learning_mode:
            self.stop_learning_mode()
        
        self.stop_alarm()
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        
        self.logger.info("Shutdown complete")
        sys.exit(0)

async def main():
    """Main function"""
    print("Modern Bluetooth Intrusion Detection System")
    print("=" * 50)
    
    ids = ModernBluetoothIDS()
    
    try:
        # Start monitoring
        await ids.monitoring_loop()
    except KeyboardInterrupt:
        ids.shutdown()
    except Exception as e:
        ids.logger.error(f"Fatal error: {e}")
        ids.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
