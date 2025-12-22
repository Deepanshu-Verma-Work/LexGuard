import requests
import json

API_URL = "https://tzx11g582b.execute-api.us-east-1.amazonaws.com"

def test_general_query():
    query = "What are the insurance requirements?"
    print(f"Testing general query: '{query}' against {API_URL}...")
    
    payload = {"query": query}
    
    try:
        res = requests.post(f"{API_URL}/chat", json=payload)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print("\nResponse:")
            print(f"Answer: {data.get('answer')}")
            
            # Check sources if available
            if 'sources' in data:
                print(f"\nSources Found: {len(data['sources'])}")
        else:
            print("Error:", res.text)
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_general_query()
