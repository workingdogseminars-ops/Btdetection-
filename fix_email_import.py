# Read the current detection file
with open('remote_site_with_email.py', 'r') as f:
    content = f.read()

# Find the send_additional_emails function and fix the import
old_function = '''    def send_additional_emails(self, device_count, device_list, email_config):
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
                        msg = EmailMessage()'''

new_function = '''    def send_additional_emails(self, device_count, device_list, email_config):
        """Send alerts to additional email addresses"""
        try:
            import smtplib
            from email.message import EmailMessage
            from datetime import datetime
            
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
                        # Create email message
                        msg = EmailMessage()'''

# Replace the function
new_content = content.replace(old_function, new_function)

# Write back to file
with open('remote_site_with_email.py', 'w') as f:
    f.write(new_content)

print("Import issue fixed for additional emails!")
