# Read the current detection file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Add MAC filtering setup to __init__ method
old_adapter = '''        # Setup Bluetooth adapter (Sena dongle preferred)
        self.bluetooth_adapter = self.setup_bluetooth_adapter()'''

new_adapter = '''        # Setup Bluetooth adapter (Sena dongle preferred)
        self.bluetooth_adapter = self.setup_bluetooth_adapter()
        
        # Get local Bluetooth MACs to ignore
        self.ignored_macs = self.get_local_bluetooth_macs()'''

# Replace in the content
new_content = content.replace(old_adapter, new_adapter)

# Write back to file
with open('remote_site_with_email.py', 'w') as f:
    f.write(new_content)

print("? MAC filtering setup added to __init__!")
