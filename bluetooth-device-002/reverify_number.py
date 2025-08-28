#!/usr/bin/env python3
import json
from twilio.rest import Client

with open('twilio_config.json', 'r') as f:
    config = json.load(f)

try:
    client = Client(config['account_sid'], config['auth_token'])
    
    print("? Attempting to re-verify number through API...")
    
    # Create a new outgoing caller ID verification
    validation_request = client.validation_requests.create(
        phone_number=config['your_phone'],
        friendly_name='Security System'
    )
    
    print(f"? Verification request created!")
    print(f"Validation Code: {validation_request.validation_code}")
    print(f"Call your phone and enter this code: {validation_request.validation_code}")
    
except Exception as e:
    print(f"? Error: {e}")
    print("This might not be available in trial accounts")

