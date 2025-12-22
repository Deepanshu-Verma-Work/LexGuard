import requests
import json

API_URL = "https://tzx11g582b.execute-api.us-east-1.amazonaws.com"

def verify_docs():
    print(f"GET {API_URL}/documents")
    try:
        res = requests.get(f"{API_URL}/documents")
        print(f"Status: {res.status_code}")
        print("Body:", json.dumps(res.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_docs()
