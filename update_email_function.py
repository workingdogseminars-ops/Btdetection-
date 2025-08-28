#!/usr/bin/env python3

# This will show you the updated send_email_alert function
# You'll need to replace it in your remote_site_with_email.py

def send_email_alert(self, device_count, device_list):
    """Send email alert and voice call"""
    try:
        import smtplib
        import json
        from email.message import EmailMessage
        from datetime import datetime
        
        # Load email config
        with open("/home/andrewdarr/intrusion/email_config.json", "r") as f:
            email_config = json.load(f)
        
        if not email_config.get("email_enabled", False):
            return
        
        # 1. Send regular email alert
        msg = EmailMessage()
        
        body = f"""? SECURITY ALERT ?

INTRUSION DETECTED at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Number of devices detected: {device_count}
Device ID: {email_config.get("device_id", "Unknown Device")}

Device details:
{device_list}

System Status: ARMED and TRIGGERED
Relay: ACTIVATED
"""
        
        msg.set_content(body)
        msg["Subject"] = email_config["subject"]
        msg["From"] = email_config["sender_email"]
        msg["To"] = email_config["recipient_email"]
        
        # Send regular email
        server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
        server.starttls()
        server.login(email_config["sender_email"], email_config["sender_password"])
        server.send_message(msg)
        server.quit()
        
        self.logger.info("? Email alert sent!")
        
        # 2. Send voice call via ClickSend (if enabled)
        if email_config.get("voice_call_enabled", False):
            voice_email = f"{email_config['voice_phone_number']}@voice.clicksend.com"
            
            voice_msg = EmailMessage()
            voice_msg.set_content(email_config.get("voice_message", 
                "Security Alert! Intrusion detected at your property. Please check your system immediately."))
            voice_msg["Subject"] = "Security Alert Voice Message"
            voice_msg["From"] = email_config["sender_email"]
            voice_msg["To"] = voice_email
            
            # Send voice call email
            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
            server.starttls()
            server.login(email_config["sender_email"], email_config["sender_password"])
            server.send_message(voice_msg)
            server.quit()
            
            self.logger.info(f"? Voice call sent to {email_config['voice_phone_number']}!")
        
    except Exception as e:
        self.logger.error(f"? Email/Voice alert failed: {e}")

print("Updated function above - copy this into your remote_site_with_email.py")
