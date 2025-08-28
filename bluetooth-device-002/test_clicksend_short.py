#!/usr/bin/env python3
import json
import smtplib
from email.message import EmailMessage

try:
    with open("email_config.json", "r") as f:
        config = json.load(f)
    
    clicksend_email = f"{config['voice_phone_number']}@voice.clicksend.com"
    short_message = config['voice_message']
    
    print(f"? Testing ClickSend voice to: {clicksend_email}")
    print(f"?? Short message: '{short_message}'")
    
    msg = EmailMessage()
    msg.set_content(short_message)
    msg["Subject"] = "Voice Test"
    msg["From"] = config["sender_email"]
    msg["To"] = clicksend_email
    
    server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
    server.starttls()
    server.login(config["sender_email"], config["sender_password"])
    server.send_message(msg)
    server.quit()
    
    print("? Short voice message sent to ClickSend!")
    print("? You should receive a call saying 'alarm island alarm island' within 1-2 minutes")
    
except Exception as e:
    print(f"? Error: {e}")
