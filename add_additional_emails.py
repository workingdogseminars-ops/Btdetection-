# Read the current detection file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Find the send_voice_alerts function and add email sending
old_function = '''            self.logger.info(f"? Voice alerts completed: {success_count} calls sent")
            
        except Exception as e:
            self.logger.error(f"? Voice alert system failed: {e}")'''

new_function = '''            self.logger.info(f"? Voice alerts completed: {success_count} calls sent")
            
            # Send additional email notifications
            self.send_additional_emails(device_count, device_list, email_config)
            
        except Exception as e:
            self.logger.error(f"? Voice alert system failed: {e}")
    
    def send_additional_emails(self, device_count, device_list, email_config):
        """Send alerts to additional email addresses"""
        try:
            voice_config = email_config.get("voice", {})
            additional_emails = [
                voice_config.get("email1", ""),
                voice_config.get("email2", ""),
                voice_config.get("email3", "")
            ]
            
            success_count = 0
            for email in additional_emails:
                if email.strip():  # Only send if email exists
                    try:
                        from datetime import datetime
                        
                        # Create email message
                        msg = EmailMessage()
                        email_body = f"""
SECURITY ALERT - Bluetooth Intrusion Detected

Device ID: {email_config.get('device_id', 'BT-IDS')}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Devices Detected: {device_count}

Device Details:
{device_list}

This is an automated alert from your Bluetooth Intrusion Detection System.
"""
                        msg.set_content(email_body)
                        msg["Subject"] = email_config.get("subject", "Security Alert")
                        msg["From"] = email_config["sender_email"]
                        msg["To"] = email.strip()
                        
                        # Send email
                        server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
                        server.starttls()
                        server.login(email_config["sender_email"], email_config["sender_password"])
                        server.send_message(msg)
                        server.quit()
                        
                        self.logger.info(f"? Additional email sent to {email}")
                        success_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"? Additional email failed to {email}: {e}")
            
            if success_count > 0:
                self.logger.info(f"? Additional emails completed: {success_count} emails sent")
                
        except Exception as e:
            self.logger.error(f"? Additional email system failed: {e}")'''

# Replace the function
new_content = content.replace(old_function, new_function)

# Write back to file
with open('remote_site_with_email.py', 'w') as f:
    f.write(new_content)

print("Additional email functionality added to detection system!")
