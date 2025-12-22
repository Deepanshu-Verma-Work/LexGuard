import requests
import json

API_URL = "https://tzx11g582b.execute-api.us-east-1.amazonaws.com"

def verify_dynamic_upload():
    filename = "test_contract.pdf"
    content_type = "application/pdf" # Try matching standard
    
    print(f"1. Requesting Upload URL for {filename} ({content_type})...")
    try:
        url = f"{API_URL}/upload-url?filename={filename}&contentType={content_type}"
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        
        if res.status_code != 200:
            print("Error:", res.text)
            return

        data = res.json()
        upload_url = data.get('uploadUrl')
        print(f"Upload URL: {upload_url[:50]}...")
        
        print("\n2. Uploading content...")
        headers = {'Content-Type': content_type}
        upload_res = requests.put(upload_url, data=b"%PDF-1.5 Dummy Content", headers=headers)
        
        print(f"Upload Status: {upload_res.status_code}")
        if upload_res.status_code in [200, 204]:
             print("SUCCESS: Uploaded matching content type.")
        else:
             print("FAILED:", upload_res.text)

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    verify_dynamic_upload()
