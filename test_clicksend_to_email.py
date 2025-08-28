#!/usr/bin/env python3
import json
import smtplib
from email.message import EmailMessage

try:
    with open("email_config.json", "r") as f:
        config = json.load(f)
    
    # Send to your normal email first to see if it works
    normal_email = config["recipient_email"]
    clicksend_email = f"{config['voice_phone_number']}@voice.clicksend.com"
    short_message = config['voice_message']
    
    print(f"? Testing by sending to your normal email: {normal_email}")
    print(f"?? Message: '{short_message}'")
    print(f"? ClickSend address would be: {clicksend_email}")
    
    msg = EmailMessage()
    msg.set_content(f"This message would go to ClickSend: {clicksend_email}\n\nMessage: {short_message}")
    msg["Subject"] = "ClickSend Test - Check This Email"
    msg["From"] = config["sender_email"]
    msg["To"] = normal_email  # Send to your normal email instead
    
    server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
    server.starttls()
    server.login(config["sender_email"], config["sender_password"])
    server.send_message(msg)
    server.quit()
    
    print("? Test email sent to your normal email!")
    print("? Check your email to confirm the system is working")
    
except Exception as e:
    print(f"? Error: {e}")
