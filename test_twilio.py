#!/usr/bin/env python3
import json
from twilio.rest import Client

# Load config
with open('twilio_config.json', 'r') as f:
    config = json.load(f)

print(f"Testing call from {config['twilio_phone']} to {config['your_phone']}")

try:
    client = Client(config['account_sid'], config['auth_token'])
    
    call = client.calls.create(
        to=config['your_phone'],
        from_=config['twilio_phone'],
        twiml='<Response><Say voice="alice">This is a test call from your Bluetooth intrusion detection system. If you can hear this, the phone alerts are working correctly.</Say></Response>'
    )
    
    print(f"? Test call initiated! Call SID: {call.sid}")
    print("You should receive a call within 30 seconds")
    
except Exception as e:
    print(f"? Error: {e}")

