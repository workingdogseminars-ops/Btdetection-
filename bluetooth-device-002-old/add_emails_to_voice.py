# Read the current web_dashboard.py file
with open('web_dashboard.py', 'r') as f:
    content = f.read()

# Find the voice config defaults and add email fields
old_voice_config = '''    voice_config = config.get('voice', {
        'enabled': True,
        'phone1': '',
        'phone2': '',
        'phone3': '',
        'message': 'phone intrusion detected. Alarm island, alarm island'
    })'''

new_voice_config = '''    voice_config = config.get('voice', {
        'enabled': True,
        'phone1': '',
        'phone2': '',
        'phone3': '',
        'message': 'phone intrusion detected. Alarm island, alarm island',
        'email1': '',
        'email2': '',
        'email3': ''
    })'''

# Replace the voice config
updated_content = content.replace(old_voice_config, new_voice_config)

# Find the update_voice route and add email handling
old_update = '''        config['voice'] = {
            'enabled': 'voice_enabled' in request.form,
            'phone1': request.form.get('phone1', '').strip(),
            'phone2': request.form.get('phone2', '').strip(),
            'phone3': request.form.get('phone3', '').strip(),
            'message': request.form.get('message', '')[:60]  # Limit to 60 chars
        }'''

new_update = '''        config['voice'] = {
            'enabled': 'voice_enabled' in request.form,
            'phone1': request.form.get('phone1', '').strip(),
            'phone2': request.form.get('phone2', '').strip(),
            'phone3': request.form.get('phone3', '').strip(),
            'message': request.form.get('message', '')[:60],  # Limit to 60 chars
            'email1': request.form.get('email1', '').strip(),
            'email2': request.form.get('email2', '').strip(),
            'email3': request.form.get('email3', '').strip()
        }'''

# Replace the update function
final_content = updated_content.replace(old_update, new_update)

# Write back to file
with open('web_dashboard.py', 'w') as f:
    f.write(final_content)

print("Email fields added to voice configuration!")
