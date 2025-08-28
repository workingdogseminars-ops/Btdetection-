# Read the current detection file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Find the __init__ method and add the adapter setup
old_init = '''        # Setup logging first
        self.setup_logging()'''

new_init = '''        # Setup logging first
        self.setup_logging()
        
        # Setup Bluetooth adapter (Sena dongle preferred)
        self.bluetooth_adapter = self.setup_bluetooth_adapter()'''

# Replace in the content
new_content = content.replace(old_init, new_init)

# Write back to file
with open('remote_site_with_email.py', 'w') as f:
    f.write(new_content)

print("? __init__ method updated to use Bluetooth adapter!")
