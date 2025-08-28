#!/usr/bin/env python3
import json
import smtplib
from email.message import EmailMessage

try:
    with open("email_config.json", "r") as f:
        config = json.load(f)
    
    clicksend_email = f"{config['voice_phone_number']}@voice.clicksend.com"
    
    print(f"? Sending to CORRECT ClickSend email: {clicksend_email}")
    print(f"?? Message: '{config['voice_message']}'")
    
    msg = EmailMessage()
    msg.set_content(config['voice_message'])
    msg["Subject"] = "Voice Test Correct Number"
    msg["From"] = config["sender_email"]
    msg["To"] = clicksend_email
    
    server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
    server.starttls()
    server.login(config["sender_email"], config["sender_password"])
    server.send_message(msg)
    server.quit()
    
    print("? Email sent to CORRECT ClickSend address!")
    print("? Should call 0409991376 within 1-2 minutes")
    
except Exception as e:
    print(f"? Error: {e}")
