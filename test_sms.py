#!/usr/bin/env python3
import json
from twilio.rest import Client

with open('twilio_config.json', 'r') as f:
    config = json.load(f)

try:
    client = Client(config['account_sid'], config['auth_token'])
    
    message = client.messages.create(
        body="? SECURITY ALERT: Test SMS from your Bluetooth intrusion detection system!",
        from_=config['twilio_phone'],
        to=config['your_phone']
    )
    
    print(f"? SMS sent! Message SID: {message.sid}")
    print("Check your phone for the SMS")
    
except Exception as e:
    print(f"? SMS Error: {e}")

