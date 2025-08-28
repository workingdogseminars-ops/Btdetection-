# Read the current detection file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Replace hciconfig with full path
old_cmd = "['hciconfig', 'hci1']"
new_cmd = "['/usr/bin/hciconfig', 'hci1']"

new_content = content.replace(old_cmd, new_cmd)

# Also fix the other hciconfig calls
old_cmd2 = "['hciconfig', hci]"
new_cmd2 = "['/usr/bin/hciconfig', hci]"

new_content = new_content.replace(old_cmd2, new_cmd2)

# Write back to file
with open('remote_site_with_email.py', 'w') as f:
    f.write(new_content)

print("? Fixed hciconfig path issues!")
