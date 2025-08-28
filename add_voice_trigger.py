# Read the current file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Find the line with send_email_alert and add voice call after it
old_text = '''                self.send_email_alert(device_count, device_list)
            except Exception as e:
                self.logger.error(f"Email failed: {e}")'''

new_text = '''                self.send_email_alert(device_count, device_list)
                # Send voice call alerts
                self.send_voice_alerts(device_count, device_list)
            except Exception as e:
                self.logger.error(f"Email failed: {e}")'''

# Replace the text
new_content = content.replace(old_text, new_text)

# Write back to file
with open('remote_site_with_email.py', 'w') as f:
    f.write(new_content)

print("Voice call trigger added successfully!")
