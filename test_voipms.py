#!/usr/bin/env python3
import json
import requests

# Load config
with open('voipms_config.json', 'r') as f:
    config = json.load(f)

print(f"Testing VoIP.ms call to {config['to_number']}")

try:
    # VoIP.ms API call
    url = "https://voip.ms/api/v1/rest.php"
    
    params = {
        'api_username': config['username'],
        'api_password': config['api_password'],
        'method': 'sendSMS',  # We'll start with SMS test first
        'did': config['from_caller_id'],
        'dst': config['to_number'],
        'message': 'Test from your security system!'
    }
    
    response = requests.get(url, params=params)
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")
