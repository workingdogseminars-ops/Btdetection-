#!/usr/bin/env python3
import shutil

# Read the current file
with open('web_dashboard.py', 'r') as f:
    content = f.read()

# Add missing imports after the existing imports
import_addition = """import smtplib
from email.message import EmailMessage
"""

# Find where to insert imports (after the datetime import)
import_pos = content.find('from datetime import datetime\n') + len('from datetime import datetime\n')
new_content = content[:import_pos] + import_addition + content[import_pos:]

# Add voice routes before the final if __name__ == '__main__':
voice_routes = '''
@app.route('/voice')
@auth.login_required
def voice():
    """Voice call settings page"""
    # Load existing email config which will contain voice settings
    try:
        with open('email_config.json', 'r') as f:
            config = json.load(f)
    except:
        config = {}
    
    # Get voice settings or set defaults
    voice_config = config.get('voice', {
        'enabled': True,
        'phone1': '',
        'phone2': '',
        'phone3': '',
        'message': 'phone intrusion detected. Alarm island, alarm island'
    })
    
    return render_template('voice.html', voice_config=voice_config)

@app.route('/update_voice', methods=['POST'])
@auth.login_required
def update_voice():
    """Update voice call settings"""
    try:
        # Load existing config
        try:
            with open('email_config.json', 'r') as f:
                config = json.load(f)
        except:
            config = {}
        
        # Update voice settings
        config['voice'] = {
            'enabled': 'voice_enabled' in request.form,
            'phone1': request.form.get('phone1', '').strip(),
            'phone2': request.form.get('phone2', '').strip(),
            'phone3': request.form.get('phone3', '').strip(),
            'message': request.form.get('message', '')[:60]  # Limit to 60 chars
        }
        
        # Save config
        with open('email_config.json', 'w') as f:
            json.dump(config, f, indent=4)
        
        return redirect(url_for('voice'))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/test_voice', methods=['POST'])
@auth.login_required
def test_voice():
    """Test voice call functionality"""
    phone = request.json.get('phone', '')
    if not phone:
        return jsonify({'success': False, 'message': 'Phone number required'})
    
    try:
        # Load email config
        with open('email_config.json', 'r') as f:
            config = json.load(f)
        
        # Send test voice call
        msg = EmailMessage()
        msg.set_content('Test call from security system')
        msg['Subject'] = 'Voice Test'
        msg['From'] = config['sender_email']
        msg['To'] = f"{phone}@voice.clicksend.com"
        
        server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
        server.starttls()
        server.login(config['sender_email'], config['sender_password'])
        server.send_message(msg)
        server.quit()
        
        return jsonify({'success': True, 'message': 'Test call sent!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

'''

# Find where to insert the routes (before if __name__ == '__main__':)
main_pos = new_content.find("if __name__ == '__main__':")
final_content = new_content[:main_pos] + voice_routes + new_content[main_pos:]

# Backup original file
shutil.copy('web_dashboard.py', 'web_dashboard.py.backup')

# Write the new content
with open('web_dashboard.py', 'w') as f:
    f.write(final_content)

print("Voice routes added successfully!")
print("Backup saved as web_dashboard.py.backup")
