#!/usr/bin/env python3
import json
from twilio.rest import Client

with open('twilio_config.json', 'r') as f:
    config = json.load(f)

try:
    client = Client(config['account_sid'], config['auth_token'])
    
    # Use a simpler approach with TwiML URL
    call = client.calls.create(
        to=config['your_phone'],
        from_=config['twilio_phone'],
        url='http://demo.twilio.com/docs/voice.xml'  # Twilio's demo TwiML
    )
    
    print(f"? Simple call initiated! Call SID: {call.sid}")
    
except Exception as e:
    print(f"? Error: {e}")

