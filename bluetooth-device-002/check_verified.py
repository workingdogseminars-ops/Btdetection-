#!/usr/bin/env python3
import json
from twilio.rest import Client

with open('twilio_config.json', 'r') as f:
    config = json.load(f)

try:
    client = Client(config['account_sid'], config['auth_token'])
    
    print("? Checking verified numbers...")
    verified_numbers = client.outgoing_caller_ids.list()
    
    if verified_numbers:
        print("? Verified numbers:")
        for number in verified_numbers:
            print(f"   ? {number.phone_number}")
    else:
        print("? No verified numbers found")
    
    print(f"\n? Your number to verify: {config['your_phone']}")
    
except Exception as e:
    print(f"? Error: {e}")
