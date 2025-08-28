#!/usr/bin/env python3
import json
import smtplib
from email.message import EmailMessage
from datetime import datetime

try:
    # Load email config
    with open("email_config.json", "r") as f:
        config = json.load(f)
    
    print(f"? Testing ClickSend voice call to: {config.get('voice_phone_number', 'NOT SET')}")
    
    if not config.get('voice_call_enabled', False):
        print("? Voice calls are DISABLED in config!")
        print("Enable them in email_config.json first")
        exit()
    
    # Create voice message
    voice_email = f"{config['voice_phone_number']}@voice.clicksend.com"
    voice_message = config.get('voice_message', 'Test voice message from your security system')
    
    print(f"? Sending to: {voice_email}")
    print(f"?? Message: {voice_message}")
    
    msg = EmailMessage()
    msg.set_content(voice_message)
    msg["Subject"] = "Security Test Voice Call"
    msg["From"] = config["sender_email"]
    msg["To"] = voice_email
    
    # Send voice call email
    print("? Connecting to SMTP server...")
    server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
    server.starttls()
    server.login(config["sender_email"], config["sender_password"])
    
    print("? Sending voice call request...")
    server.send_message(msg)
    server.quit()
    
    print("? Voice call request sent to ClickSend!")
    print("? You should receive a call within 1-2 minutes")
    print("?? The voice will read your message aloud")
    
except FileNotFoundError:
    print("? email_config.json not found!")
except KeyError as e:
    print(f"? Missing config key: {e}")
except Exception as e:
    print(f"? Error: {e}")
