import requests
import json
import uuid
import time

API_URL = "https://tzx11g582b.execute-api.us-east-1.amazonaws.com"
SESSION_ID = f"test-session-{uuid.uuid4()}"

def test_memory():
    print(f"Testing Memory with Session ID: {SESSION_ID}")
    
    # Turn 1: Set Context
    query1 = "My name is Alice. I am a lawyer."
    print(f"\n[Turn 1] User: {query1}")
    res1 = requests.post(f"{API_URL}/chat", json={"query": query1, "sessionId": SESSION_ID})
    print(f"[Turn 1] AI: {res1.json().get('answer')}")
    
    time.sleep(1) # Ensure DynamoDB consistency (store before read)
    
    # Turn 2: Ask based on context
    query2 = "What is my name and profession?"
    print(f"\n[Turn 2] User: {query2}")
    res2 = requests.post(f"{API_URL}/chat", json={"query": query2, "sessionId": SESSION_ID})
    answer2 = res2.json().get('answer')
    print(f"[Turn 2] AI: {answer2}")
    
    if "Alice" in answer2 and "lawyer" in answer2.lower():
        print("\nSUCCESS: Memory verified!")
    else:
        print("\nFAILURE: Memory not working.")

if __name__ == "__main__":
    test_memory()
