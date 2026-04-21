#!/usr/bin/env python3
"""Test x-ui API to add client and check if it creates client_traffics entry."""

import requests
import json
import time
import sqlite3

# Configuration
BASE_URL = "http://89.44.76.190:2053/spFIOjQeKtBtdxWC11"
USERNAME = "admin"
PASSWORD = "admin"
INBOUND_ID = 1
DB_PATH = "/etc/x-ui/x-ui.db"

def login():
    """Login to x-ui and get session cookie."""
    url = f"{BASE_URL}/login"
    data = {"username": USERNAME, "password": PASSWORD}
    
    response = requests.post(url, data=data)
    print(f"Login status: {response.status_code}")
    
    if response.status_code == 200:
        cookie = response.cookies.get('3x-ui')
        print(f"Session cookie: {cookie[:50]}...")
        return cookie
    else:
        print(f"Login failed: {response.text}")
        return None

def add_client_via_api(cookie, email):
    """Add client via x-ui API."""
    url = f"{BASE_URL}/panel/api/inbounds/addClient"
    headers = {"Cookie": f"3x-ui={cookie}"}
    
    # Client configuration
    import uuid
    from datetime import datetime, timedelta
    
    client_uuid = str(uuid.uuid4())
    expiry_ts = int((datetime.utcnow() + timedelta(days=30)).timestamp() * 1000)
    
    client_data = {
        "id": client_uuid,
        "email": email,
        "flow": "xtls-rprx-vision",
        "enable": True,
        "expiryTime": expiry_ts,
        "totalGB": 0,
        "limitIp": 1,
    }
    
    payload = {
        "id": INBOUND_ID,
        "settings": json.dumps({"clients": [client_data]})
    }
    
    print(f"\n📤 Adding client via API: {email}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
    
    return response.status_code == 200, client_uuid

def check_client_traffics(email):
    """Check if client has entry in client_traffics table."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT email, up, down, enable FROM client_traffics WHERE email=?", (email,))
        row = cursor.fetchone()
        
        if row:
            print(f"\n✅ Client {email} HAS entry in client_traffics:")
            print(f"   Email: {row[0]}")
            print(f"   Upload: {row[1]} bytes")
            print(f"   Download: {row[2]} bytes")
            print(f"   Enabled: {row[3]}")
            return True
        else:
            print(f"\n❌ Client {email} DOES NOT have entry in client_traffics")
            return False
    finally:
        conn.close()

def main():
    """Test API client creation."""
    # Login
    cookie = login()
    if not cookie:
        return
    
    # Add client
    test_email = f"api_test_{int(time.time())}"
    success, uuid = add_client_via_api(cookie, test_email)
    
    if not success:
        print("\n❌ Failed to add client via API")
        return
    
    print(f"\n✅ Client added successfully!")
    print(f"   Email: {test_email}")
    print(f"   UUID: {uuid}")
    
    # Wait a bit for x-ui to process
    print("\n⏳ Waiting 2 seconds for x-ui to process...")
    time.sleep(2)
    
    # Check if client_traffics entry was created
    has_tracking = check_client_traffics(test_email)
    
    if has_tracking:
        print("\n✅ SUCCESS: API creates client_traffics entry automatically!")
    else:
        print("\n❌ PROBLEM: API does NOT create client_traffics entry!")
        print("   This is why bot-created clients don't have statistics.")

if __name__ == "__main__":
    main()
