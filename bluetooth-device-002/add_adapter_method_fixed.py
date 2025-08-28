# Read the current detection file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Find the end of __init__ method by looking for the next method definition
init_start = content.find('def __init__(self):')
if init_start != -1:
    # Find the next method after __init__
    next_method = content.find('\n    def ', init_start + 20)
    
    if next_method != -1:
        # Insert the new method before the next method
        new_method = '''
    def setup_bluetooth_adapter(self):
        """Setup Bluetooth adapter - prefer Sena dongle, fallback to built-in"""
        try:
            import subprocess
            
            # Check if Sena dongle (hci1) is available and UP
            result = subprocess.run(['hciconfig', 'hci1'], capture_output=True, text=True)
            if result.returncode == 0 and 'UP RUNNING' in result.stdout:
                self.logger.info("? Using Sena UD-100 dongle (hci1) for extended range detection")
                return "hci1"
            else:
                self.logger.info("? Using built-in Bluetooth (hci0) for detection")
                return "hci0"
                
        except Exception as e:
            self.logger.error(f"Bluetooth adapter setup failed: {e}")
            return "hci0"

'''
        
        new_content = content[:next_method] + new_method + content[next_method:]
        
        with open('remote_site_with_email.py', 'w') as f:
            f.write(new_content)
        
        print("? Bluetooth adapter setup method added!")
    else:
        print("? Could not find next method after __init__")
else:
    print("? Could not find __init__ method")
