# Read the current detection file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Find the BleakScanner.discover call and update it to use the adapter
old_scanner = '''            devices = await BleakScanner.discover(
                timeout=self.scan_duration
            )'''

new_scanner = '''            devices = await BleakScanner.discover(
                timeout=self.scan_duration,
                adapter=self.bluetooth_adapter
            )'''

# Replace in the content
new_content = content.replace(old_scanner, new_scanner)

# Write back to file
with open('remote_site_with_email.py', 'w') as f:
    f.write(new_content)

print("? Scanner updated to use selected Bluetooth adapter!")
