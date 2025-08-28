import re

# Read the current file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Find where to insert the new function (after send_email_alert function)
# Look for the end of send_email_alert function
pattern = r'(    def send_email_alert.*?self\.logger\.error\(f".*? Email failed: \{e\}"\))'
match = re.search(pattern, content, re.DOTALL)

if match:
    end_pos = match.end()
    
    # Add the voice call function
    voice_function = '''

    def send_voice_alerts(self, device_count, device_list):
        """Send voice call alerts when alarm triggers"""
        try:
            import smtplib
            import json
            from email.message import EmailMessage
            
            # Load email config (which contains voice settings)
            with open("/home/andrewdarr/intrusion/email_config.json", "r") as f:
                email_config = json.load(f)
            
            voice_config = email_config.get("voice", {})
            
            if not voice_config.get("enabled", False):
                self.logger.info("Voice calls disabled, skipping...")
                return
            
            # Get phone numbers and message
            phone_numbers = [
                voice_config.get("phone1", ""),
                voice_config.get("phone2", ""),
                voice_config.get("phone3", "")
            ]
            message = voice_config.get("message", "Security alert detected")[:60]
            
            success_count = 0
            for phone in phone_numbers:
                if phone.strip():  # Only call if phone number exists
                    try:
                        # Create email for ClickSend voice
                        msg = EmailMessage()
                        msg.set_content(message)
                        msg["Subject"] = "Voice Alert"
                        msg["From"] = email_config["sender_email"]
                        msg["To"] = f"{phone.strip()}@voice.clicksend.com"
                        
                        # Send voice call
                        server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
                        server.starttls()
                        server.login(email_config["sender_email"], email_config["sender_password"])
                        server.send_message(msg)
                        server.quit()
                        
                        self.logger.info(f"? Voice call sent to {phone}")
                        success_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"? Voice call failed to {phone}: {e}")
            
            self.logger.info(f"? Voice alerts completed: {success_count} calls sent")
            
        except Exception as e:
            self.logger.error(f"? Voice alert system failed: {e}")'''
    
    # Insert the function
    new_content = content[:end_pos] + voice_function + content[end_pos:]
    
    # Write back to file
    with open('remote_site_with_email.py', 'w') as f:
        f.write(new_content)
    
    print("Voice function added successfully!")
else:
    print("Could not find send_email_alert function to add voice calls after")
