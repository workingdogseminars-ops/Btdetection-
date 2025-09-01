# Read the current detection file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Find the device processing loop and add MAC filtering
# Look for where devices are processed
old_processing = '''            for device in devices:
                mac = device.address
                name = device.name or "Unknown Device"'''

new_processing = '''            for device in devices:
                mac = device.address
                name = device.name or "Unknown Device"
                
                # Skip local Bluetooth devices
                if mac.upper() in self.ignored_macs:
                    continue'''

# Replace in the content
new_content = content.replace(old_processing, new_processing)

# Write back to file
with open('remote_site_with_email.py', 'w') as f:
    f.write(new_content)

print("? Device filtering updated to ignore local Bluetooth MACs!")
