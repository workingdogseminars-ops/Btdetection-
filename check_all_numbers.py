#!/usr/bin/env python3
import json
from twilio.rest import Client

with open('twilio_config.json', 'r') as f:
    config = json.load(f)

try:
    client = Client(config['account_sid'], config['auth_token'])
    
    print("? Incoming Phone Numbers (numbers you own):")
    incoming_numbers = client.incoming_phone_numbers.list()
    for number in incoming_numbers:
        print(f"   {number.phone_number} - {number.friendly_name}")
    
    print("\n? Outgoing Caller IDs (verified for outbound):")
    caller_ids = client.outgoing_caller_ids.list()
    for caller_id in caller_ids:
        print(f"   {caller_id.phone_number} - {caller_id.friendly_name}")
    
    print("\n? Account Trial Status:")
    account = client.api.accounts(config['account_sid']).fetch()
    print(f"   Type: {account.type}")
    print(f"   Status: {account.status}")
    
except Exception as e:
    print(f"? Error: {e}")
