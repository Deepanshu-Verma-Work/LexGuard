import boto3
import requests
import json
import time

# CONFIGURATION (Auto-detected from your previous context)
REGION = 'us-east-1'
API_URL = 'https://tzx11g582b.execute-api.us-east-1.amazonaws.com'
BUCKET_NAME = 'casechat-evidence-20251212210638293000000001' 
AUDIT_TABLE = 'CaseChat_Audit'

def test_api_health():
    print(f"1. Testing API Health ({API_URL})...")
    # Our API expects POST for chat or GET for upload.
    # Let's try to get an upload URL.
    try:
        response = requests.get(f"{API_URL}/upload-url?filename=test_verification_doc.pdf")
        if response.status_code == 200:
            print("   [PASS] API Responded with 200")
            data = response.json()
            if "uploadUrl" in data and "key" in data:
                print("   [PASS] Returned Upload URL")
                return data
            else:
                print(f"   [FAIL] Invalid format: {data}")
        else:
            print(f"   [FAIL] Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   [FAIL] Exception: {e}")
    return None

def test_s3_upload(upload_url):
    print("\n2. Testing S3 Upload via Presigned URL...")
    try:
        # Create a dummy PDF content
        dummy_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n..."
        
        response = requests.put(upload_url, data=dummy_content, headers={'Content-Type': 'application/pdf'})
        
        if response.status_code == 200:
            print("   [PASS] Upload Successful (200 OK)")
            return True
        else:
            print(f"   [FAIL] Upload Failed: {response.status_code}")
            print(f"   Reason: {response.text}")
            return False
    except Exception as e:
        print(f"   [FAIL] Upload Exception: {e}")
        return False

def verify_s3_object_exists(key):
    print(f"\n3. Verifying Object in S3 ({BUCKET_NAME}/{key})...")
    s3 = boto3.client('s3', region_name=REGION)
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=key)
        print("   [PASS] File found in S3")
        return True
    except Exception as e:
        print(f"   [FAIL] Object not found: {e}")
        return False

def verify_dynamodb_audit():
    print(f"\n4. Verifying DynamoDB Audit Log ({AUDIT_TABLE})...")
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(AUDIT_TABLE)
    
    # We scan specifically for the ingest action
    # In prod, query is better, but scan is fine for test
    try:
        # Give Lambda a moment to fire
        print("   Waiting 5s for Lambda to trigger...")
        time.sleep(5) 
        
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('action').eq('INGEST_START')
        )
        
        items = response.get('Items', [])
        if len(items) > 0:
            print(f"   [PASS] Found {len(items)} Audit Logs for INGEST_START")
            print(f"   Latest: {items[0]['details']}")
        else:
            print("   [FAIL] No Audit Logs found. Ingest Lambda may not have fired.")
            
    except Exception as e:
        print(f"   [FAIL] DynamoDB Check Failed: {e}")

if __name__ == "__main__":
    print(f"--- STARTING SYSTEM VERIFICATION ---\n")
    
    upload_data = test_api_health()
    
    if upload_data:
        success = test_s3_upload(upload_data['uploadUrl'])
        if success:
            exists = verify_s3_object_exists(upload_data['key'])
            if exists:
                verify_dynamodb_audit()
            else:
                print("   [CRITICAL] File uploaded but not found in S3. Check permissions/path.")
    
    print(f"\n--- VERIFICATION COMPLETE ---")
