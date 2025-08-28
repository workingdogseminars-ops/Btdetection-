#!/usr/bin/env python3
import json
import smtplib
from email.message import EmailMessage

try:
    with open("email_config.json", "r") as f:
        config = json.load(f)
    
    clicksend_email = f"{config['voice_phone_number']}@voice.clicksend.com"
    longer_message = config['voice_message']
    
    print(f"? Testing longer message to: {clicksend_email}")
    print(f"?? Message: '{longer_message}'")
    print(f"? Message length: {len(longer_message)} characters")
    
    msg = EmailMessage()
    msg.set_content(longer_message)
    msg["Subject"] = "Longer Voice Test"
    msg["From"] = config["sender_email"]
    msg["To"] = clicksend_email
    
    server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
    server.starttls()
    server.login(config["sender_email"], config["sender_password"])
    server.send_message(msg)
    server.quit()
    
    print("? Longer voice message sent to ClickSend!")
    print("? You should receive a call saying the longer message within 1-2 minutes")
    print("? This will test if ClickSend handles longer messages")
    
except Exception as e:
    print(f"? Error: {e}")
