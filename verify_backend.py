import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def verify_system():
    print("=== Odia AI Backend Verification ===")
    
    # 1. Health check
    print("\n[1/4] Checking System Health...")
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(json.dumps(r.json(), indent=2))
        if r.json()["status"] != "healthy":
            print("WARNING: System is degraded. Check service connectivity.")
    except Exception as e:
        print(f"FAILED: Could not reach health endpoint: {e}")
        return

    # 2. Registration & Login
    print("\n[2/4] Testing Auth Flow (Bcrypt Fix)...")
    email = f"tester_{int(time.time())}@odia.ai"
    reg_payload = {
        "name": "QA Tester",
        "email": email,
        "password": "SecurePassword123",
        "profession": "Software Quality"
    }
    
    try:
        # Register
        r_reg = requests.post(f"{BASE_URL}/api/auth/register", json=reg_payload)
        print(f"Registration Status: {r_reg.status_code}")
        
        # Login
        r_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": "SecurePassword123"
        })
        print(f"Login Status: {r_login.status_code}")
        token = r_login.json().get("access_token")
        
        if token:
            print("SUCCESS: JWT Token acquired.")
            headers = {"Authorization": f"Bearer {token}"}
            
            # 3. Profile & Upgrade
            print("\n[3/4] Testing Profile & Premium Upgrade...")
            r_me = requests.get(f"{BASE_URL}/api/user/me", headers=headers)
            print(f"Initial Profile: {r_me.json()}")
            
            # Attempt upgrade (Need premium_key.txt to have at least one key)
            # We'll mock the key search here or just check the endpoint exists
            print("Reading premium_key.txt for a valid key...")
            try:
                with open("premium_key.txt", "r") as f:
                    keys = [line.strip() for line in f.readlines() if line.strip()]
                    if keys:
                        test_key = keys[0]
                        print(f"Using test key: {test_key}")
                        r_up = requests.post(f"{BASE_URL}/api/user/upgrade", json={"premium_key": test_key}, headers=headers)
                        print(f"Upgrade Response: {r_up.json()}")
                        
                        # Verify profile changed
                        r_me_final = requests.get(f"{BASE_URL}/api/user/me", headers=headers)
                        print(f"Updated Profile: {r_me_final.json()}")
                    else:
                        print("SKIP: No keys found in premium_key.txt")
            except FileNotFoundError:
                print("SKIP: premium_key.txt not found")
                
            # 4. Document Limits Check
            print("\n[4/4] Testing Upload Logic Routing...")
            # We won't upload a real file yet to avoid clutter, but we verify the endpoint logic
            # This demonstrates the route is registered and protected.
            r_doc = requests.post(f"{BASE_URL}/api/document/upload", headers=headers)
            print(f"Document Endpoint reachable (Expected 422 if no file sent): {r_doc.status_code}")
            
        else:
            print("FAILED: Could not acquire login token.")
            
    except Exception as e:
        print(f"ERROR during verification: {e}")

if __name__ == "__main__":
    verify_system()
