#!/usr/bin/env python3
import json
from twilio.rest import Client

with open('twilio_config.json', 'r') as f:
    config = json.load(f)

try:
    client = Client(config['account_sid'], config['auth_token'])
    
    # Try calling your Twilio number instead
    call = client.calls.create(
        to=config['twilio_phone'],  # Call TO your Twilio number
        from_=config['your_phone'], # FROM your verified number
        twiml='<Response><Say>This is a reverse test call.</Say></Response>'
    )
    
    print(f"? Reverse call initiated! Call SID: {call.sid}")
    
except Exception as e:
    print(f"? Error: {e}")

