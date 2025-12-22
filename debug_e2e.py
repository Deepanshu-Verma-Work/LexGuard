import requests
import json
import time

API_URL = "https://ejmtxwc2m0.execute-api.us-east-1.amazonaws.com"

def test_upload_and_query():
    print("=== 1. Get Presigned URL ===")
    filename = "test_case.txt"
    res = requests.get(f"{API_URL}/upload-url?filename={filename}&contentType=text/plain")
    if res.status_code != 200:
        print(f"FAILED to get upload URL: {res.text}")
        return
    data = res.json()
    upload_url = data['uploadURL']
    print(f"Got URL: {upload_url[:50]}...")

    print("\n=== 2. Upload File to S3 ===")
    txt_content = "This is a critical evidence document regarding the lawsuit. The defendant is guilty of negligence."
    
    headers = {"Content-Type": "text/plain"}
    upload_res = requests.put(upload_url, data=txt_content, headers=headers)
    if upload_res.status_code == 200:
        print("Upload SUCCESS")
    else:
        print(f"Upload FAILED: {upload_res.status_code} {upload_res.text}")
        return

    print("\n=== 3. Wait for Ingestion (10s) ===")
    time.sleep(10)

    print("\n=== 4. Check Documents List ===")
    docs_res = requests.get(f"{API_URL}/documents")
    print(f"Documents: {docs_res.text}")

    print("\n=== 5. Test Chat Query ===")
    chat_payload = {
        "query": "What is this document about?",
        "session_id": "test-session-local"
    }
    chat_res = requests.post(f"{API_URL}/chat", json=chat_payload)
    print(f"Chat Response: {chat_res.text}")

if __name__ == "__main__":
    test_upload_and_query()
