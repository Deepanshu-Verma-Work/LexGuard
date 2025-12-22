import requests
import json

API_URL = "https://tzx11g582b.execute-api.us-east-1.amazonaws.com"

def test_termination_query():
    print(f"Testing termination query against {API_URL}...")
    
    query = "What is written about early termination?"
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
                for i, source in enumerate(data['sources']):
                    text = source['metadata'].get('text', '')
                    if "TERMINATION" in text.upper():
                         print(f"  [Match {i+1}] Contains 'TERMINATION'")
        else:
            print("Error:", res.text)
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_termination_query()
