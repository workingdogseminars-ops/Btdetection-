#!/usr/bin/env python3
import requests

# Test with placeholder credentials
url = "https://voip.ms/api/v1/rest.php"
params = {
    'api_username': 'test',
    'api_password': 'test',
    'method': 'getBalance'
}

try:
    response = requests.get(url, params=params)
    print(f"API Response: {response.text}")
    
    if "invalid_credentials" in response.text.lower():
        print("? API is accessible - just need real credentials")
    elif "api_disabled" in response.text.lower():
        print("? API needs to be enabled")
    else:
        print("? Unexpected response")
        
except Exception as e:
    print(f"? Error: {e}")
