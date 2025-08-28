#!/usr/bin/env python3
import json
import smtplib
from email.message import EmailMessage
from datetime import datetime

try:
    # Load email config
    with open("email_config.json", "r") as f:
        config = json.load(f)
    
    print(f"? Testing email from: {config['sender_email']}")
    print(f"? Sending to: {config['recipient_email']}")
    print(f"? SMTP Server: {config['smtp_server']}:{config['smtp_port']}")
    print(f"? Email enabled: {config.get('email_enabled', False)}")
    
    if not config.get('email_enabled', False):
        print("? Email is DISABLED in config!")
        exit()
    
    # Create test message
    msg = EmailMessage()
    msg.set_content(f"""? Manual Email Test

This is a test email sent manually from your Bluetooth IDS.

Time: {datetime.now()}
From: Raspberry Pi Security System
Status: Email system working correctly!
""")
    
    msg["Subject"] = "? Manual Test - " + config.get("subject", "Security Alert")
    msg["From"] = config["sender_email"]
    msg["To"] = config["recipient_email"]
    
    # Send email
    print("? Connecting to SMTP server...")
    server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
    
    print("? Starting TLS...")
    server.starttls()
    
    print("? Logging in...")
    server.login(config["sender_email"], config["sender_password"])
    
    print("? Sending message...")
    server.send_message(msg)
    server.quit()
    
    print("? Email sent successfully!")
    
except FileNotFoundError:
    print("? email_config.json not found!")
except KeyError as e:
    print(f"? Missing config key: {e}")
except smtplib.SMTPAuthenticationError:
    print("? SMTP Authentication failed - check email/password")
except smtplib.SMTPConnectError:
    print("? Cannot connect to SMTP server")
except Exception as e:
    print(f"? Error: {e}")
