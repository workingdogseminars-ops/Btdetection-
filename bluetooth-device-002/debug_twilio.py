#!/usr/bin/env python3
import json
from twilio.rest import Client

with open('twilio_config.json', 'r') as f:
    config = json.load(f)

client = Client(config['account_sid'], config['auth_token'])

print("? All verified caller IDs:")
verified_numbers = client.outgoing_caller_ids.list()

for number in verified_numbers:
    print(f"Phone Number: '{number.phone_number}'")
    print(f"Friendly Name: '{number.friendly_name}'")
    print(f"Account SID: {number.account_sid}")
    print("---")

print(f"Config file has: '{config['your_phone']}'")
