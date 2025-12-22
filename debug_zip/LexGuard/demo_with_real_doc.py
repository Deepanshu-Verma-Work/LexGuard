import requests
import json
import boto3
import time
import os

# CONFIG
API_URL = "https://tzx11g582b.execute-api.us-east-1.amazonaws.com" # From Terraform Output
FILE_PATH = "SampleContract-Shuttle.pdf"
USER_ID = "alice@firm.com"

def run_demo():
    print(f"--- DEMO: {FILE_PATH} ---")

    # 1. Get Presigned URL
    print("\n1. Requesting Upload URL...")
    try:
        res = requests.get(f"{API_URL}/upload-url", params={"filename": FILE_PATH})
        if res.status_code != 200:
            print(f"FAILED: {res.text}")
            return
        data = res.json()
        upload_url = data['uploadUrl']
        s3_key = data['key']
        print("   [OK] Got URL")
    except Exception as e:
        print(f"FAILED: {e}")
        return

    # 2. Upload File
    print("\n2. Uploading File to S3...")
    try:
        with open(FILE_PATH, 'rb') as f:
            res = requests.put(upload_url, data=f, headers={'Content-Type': 'application/pdf'})
            if res.status_code == 200:
                print("   [OK] Upload Successful")
            else:
                print(f"FAILED: {res.status_code} - {res.text}")
                return
    except Exception as e:
        print(f"FAILED: {e}")
        return

    # 3. Wait for Ingestion (Audit Log Trigger)
    print("\n3. Waiting for Ingestion (15s)...")
    time.sleep(15)

    # 4. Ask Questions
    questions = [
        "What is this document about?",
        "What must invoices include?",
        "Who are the parties involved?",
        "What is the termination clause?"
    ]

    for q in questions:
        print(f"\n4. Asking: '{q}'")
        try:
            res = requests.post(
                f"{API_URL}/chat",
                json={"query": q},
                headers={'Content-Type': 'application/json'}
            )
            if res.status_code == 200:
                answer = res.json().get('answer')
                print(f"   AI ANSWER: {answer}")
                print(f"   [OK] Success")
            else:
                print(f"FAILED: {res.status_code} - {res.text}")

        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    run_demo()
