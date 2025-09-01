#!/usr/bin/env python3
import subprocess
import time
import json
from datetime import datetime
from collections import defaultdict

class WiFiStabilityMonitor:
    def __init__(self):
        self.device_history = defaultdict(list)  # MAC -> list of timestamps
        self.name_to_macs = defaultdict(set)     # Network name -> set of MACs
        self.scan_count = 0
        
    def scan_wifi(self):
        """Scan for WiFi devices"""
        try:
            result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], 
                                  capture_output=True, text=True, timeout=30)
            return result.stdout
        except Exception as e:
            print(f"Scan error: {e}")
            return ""
    
    def parse_scan(self, scan_output):
        """Parse scan results into devices"""
        devices = {}
        lines = scan_output.split('\n')
        current_mac = None
        current_name = "Unknown"
        current_signal = None
        
        for line in lines:
            line = line.strip()
            if 'Address:' in line:
                current_mac = line.split('Address: ')[1].strip().upper()
            elif 'ESSID:' in line and current_mac:
                current_name = line.split('ESSID:')[1].strip().strip('"')
                if not current_name:
                    current_name = "Hidden"
            elif 'Signal level=' in line:
                try:
                    signal_part = line.split('Signal level=')[1].split()[0]
                    current_signal = int(signal_part.replace('dBm', ''))
                except:
                    current_signal = -100
                    
                if current_mac:
                    devices[current_mac] = {
                        'name': current_name,
                        'signal': current_signal,
                        'timestamp': datetime.now()
                    }
                    
        return devices
    
    def analyze_stability(self):
        """Analyze MAC address stability patterns"""
        print(f"\n{'='*60}")
        print(f"WiFi MAC ADDRESS STABILITY ANALYSIS")
        print(f"{'='*60}")
        print(f"Total scans performed: {self.scan_count}")
        print(f"Unique MAC addresses seen: {len(self.device_history)}")
        
        # Group by network name to see MAC changes
        print(f"\nNETWORK NAME ANALYSIS:")
        print(f"{'Network Name':<25} | {'MAC Count'} | {'MAC Addresses'}")
        print("-" * 80)
        
        for name, macs in self.name_to_macs.items():
            mac_list = ', '.join(list(macs)[:2])  # Show first 2 MACs
            if len(macs) > 2:
                mac_list += f"... (+{len(macs)-2} more)"
            print(f"{name[:24]:<25} | {len(macs):>9} | {mac_list}")
        
        # Stability categories
        stable_devices = []
        one_time_devices = []
        changing_devices = []
        
        for mac, timestamps in self.device_history.items():
            if len(timestamps) >= 3:
                stable_devices.append((mac, len(timestamps)))
            elif len(timestamps) == 1:
                one_time_devices.append(mac)
        
        for name, macs in self.name_to_macs.items():
            if len(macs) > 1 and name not in ["Unknown", "Hidden", ""]:
                changing_devices.append((name, len(macs)))
        
        print(f"\nSTABILITY SUMMARY:")
        print(f"Stable devices (3+ detections): {len(stable_devices)}")
        print(f"One-time devices: {len(one_time_devices)}")
        print(f"Networks with changing MACs: {len(changing_devices)}")
    
    def run_monitoring(self, duration_minutes=10, scan_interval=30):
        """Run monitoring for specified duration"""
        total_scans = duration_minutes
        
        print(f"WiFi MAC Stability Test")
        print(f"Duration: {duration_minutes} minutes (1 scan per minute)")
        print("=" * 50)
        
        for scan_num in range(total_scans):
            self.scan_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"\nScan {scan_num + 1}/{total_scans} at {timestamp}")
            
            # Perform scan
            scan_data = self.scan_wifi()
            devices = self.parse_scan(scan_data)
            
            print(f"Found {len(devices)} devices:")
            
            # Track devices
            new_devices = 0
            for mac, info in devices.items():
                self.device_history[mac].append(info['timestamp'])
                
                if info['name']:
                    self.name_to_macs[info['name']].add(mac)
                
                if len(self.device_history[mac]) == 1:
                    new_devices += 1
                    status = "NEW"
                else:
                    status = f"x{len(self.device_history[mac])}"
                
                print(f"  {status:>4} | {mac} | {info['signal']:>4}dBm | {info['name'][:25]}")
            
            print(f"New MACs this scan: {new_devices}")
            
            if scan_num < total_scans - 1:
                time.sleep(scan_interval)
        
        self.analyze_stability()

if __name__ == "__main__":
    monitor = WiFiStabilityMonitor()
    
    print("Starting WiFi MAC stability test...")
    print("This will scan every 30 seconds for 10 minutes")
    print("Press Ctrl+C to stop early and see results")
    
    try:
        monitor.run_monitoring(duration_minutes=10, scan_interval=30)
    except KeyboardInterrupt:
        print("\n\nTest stopped by user")
        monitor.analyze_stability()
