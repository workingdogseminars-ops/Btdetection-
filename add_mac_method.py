# Read the current detection file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Find where to add the MAC filtering method (after setup_bluetooth_adapter)
adapter_method_end = content.find('            return "hci0"')
if adapter_method_end != -1:
    # Find the end of that method
    next_method = content.find('\n    def ', adapter_method_end)
    
    # Insert the MAC filtering method
    mac_method = '''
    def get_local_bluetooth_macs(self):
        """Get MAC addresses of local Bluetooth devices to ignore"""
        ignored_macs = set()
        try:
            import subprocess
            
            # Get MACs from both hci0 and hci1
            for hci in ['hci0', 'hci1']:
                result = subprocess.run(['hciconfig', hci], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.split('\\n')
                    for line in lines:
                        if 'BD Address:' in line:
                            mac = line.split('BD Address: ')[1].split(' ')[0]
                            ignored_macs.add(mac.upper())
                            self.logger.info(f"? Ignoring local device: {hci} ({mac})")
            
            return ignored_macs
            
        except Exception as e:
            self.logger.error(f"Error getting local MAC addresses: {e}")
            return set()

'''
    
    new_content = content[:next_method] + mac_method + content[next_method:]
    
    with open('remote_site_with_email.py', 'w') as f:
        f.write(new_content)
    
    print("? MAC filtering method added!")
else:
    print("? Could not find adapter method")
