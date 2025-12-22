import requests
import json

API_URL = "https://tzx11g582b.execute-api.us-east-1.amazonaws.com"

def verify_audit():
    print(f"GET {API_URL}/audit")
    try:
        res = requests.get(f"{API_URL}/audit")
        print(f"Status: {res.status_code}")
        print("Body sample:", res.text[:200])
        parsed = res.json()
        print(f"Count: {len(parsed)}")
    except Exception as e:
        print(f"Error: {e}")
        try:
             print("Raw:", res.text)
        except: pass

if __name__ == "__main__":
    verify_audit()
