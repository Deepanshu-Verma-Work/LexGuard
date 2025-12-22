import requests
import json

API_URL = "https://tzx11g582b.execute-api.us-east-1.amazonaws.com"

def verify_upload():
    print(f"1. Requesting Upload URL from {API_URL}/upload-url...")
    try:
        res = requests.get(f"{API_URL}/upload-url?filename=test_upload.txt")
        print(f"Status: {res.status_code}")
        if res.status_code != 200:
            print("Error:", res.text)
            return

        data = res.json()
        upload_url = data.get('uploadUrl')
        key = data.get('key')
        print(f"Upload URL: {upload_url[:50]}...")
        print(f"Key: {key}")
        
        print("\n2. Uploading dummy content to S3...")
        headers = {'Content-Type': 'application/pdf'} # Simulating PDF upload as per App.tsx
        # Note: In App.tsx it sends 'application/pdf' content-type for PUT too.
        # Ensure 'ContentType': 'application/pdf' was set in presigned url params in backend.
        
        upload_res = requests.put(upload_url, data=b"Dummy PDF content", headers=headers)
        print(f"Upload Status: {upload_res.status_code}")
        if upload_res.status_code not in [200, 204]:
             print("Upload Failed:", upload_res.text)
        else:
             print("Upload SUCCESS")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    verify_upload()
