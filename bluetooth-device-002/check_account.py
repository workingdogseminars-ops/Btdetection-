#!/usr/bin/env python3
import json
from twilio.rest import Client

with open('twilio_config.json', 'r') as f:
    config = json.load(f)

try:
    client = Client(config['account_sid'], config['auth_token'])
    
    # Check account status
    account = client.api.accounts(config['account_sid']).fetch()
    print(f"Account Status: {account.status}")
    print(f"Account Type: {account.type}")
    
    # Check balance
    balance = client.balance.fetch()
    print(f"Balance: {balance.balance} {balance.currency}")
    
except Exception as e:
    print(f"Error: {e}")
