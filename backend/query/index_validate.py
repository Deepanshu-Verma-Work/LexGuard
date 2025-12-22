
import json
import time
import os
import boto3
import datetime
import hashlib
from pinecone import Pinecone

bedrock = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')
audit_table = dynamodb.Table('CaseChat_Audit')
history_table = dynamodb.Table('CaseChat_History')
s3_client = boto3.client('s3')

BUCKET_NAME = os.environ.get('BUCKET_NAME')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_INDEX = os.environ.get('PINECONE_INDEX', 'casechat-index')

def get_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX)

def generate_embedding(text):
    # RATE LIMIT FIX
    time.sleep(1) 
    body = json.dumps({"inputText": text})
    response = bedrock.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        contentType='application/json',
        accept='application/json',
        body=body
    )
    response_body = json.loads(response.get('body').read())
    return response_body['embedding']

def analyze_risk_scan(text):
    try:
        prompt = f"""
        Instruction: Act as a Senior Legal Risk Officer.
        Analyze:
        {text[:12000]}
        
        Return JSON: {{ "score": "High"|"Medium"|"Low", "flags": ["Risk 1"] }}
        """
        fmt_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        
        response = bedrock.invoke_model(
            modelId='meta.llama3-8b-instruct-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({"prompt": fmt_prompt, "max_gen_len": 512})
        )
        res = json.loads(response.get('body').read())
        raw = res['generation'].strip()
        
        # Simple extraction
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start != -1 and end != -1:
            return json.loads(raw[start:end])
        return {"score": "Low", "flags": ["Parsing Error"]}
    except:
        return {"score": "Low", "flags": []}

def handler(event, context):
    print("DEBUG EVENT:", json.dumps(event))
    try:
        # S3 INGESTION
        if 'Records' in event and event['Records'][0].get('eventSource') == 'aws:s3':
             print("DEBUG: S3 Trigger")
             bucket = event['Records'][0]['s3']['bucket']['name']
             key = event['Records'][0]['s3']['object']['key']
             obj = s3_client.get_object(Bucket=bucket, Key=key)
             content = obj['Body'].read()
             
             text = ""
             if key.lower().endswith('.pdf'):
                 try:
                     import io
                     from pypdf import PdfReader
                     reader = PdfReader(io.BytesIO(content))
                     for page in reader.pages:
                         text += page.extract_text() + "\n"
                 except:
                     text = str(content[:5000])
             else:
                 text = content.decode('utf-8', errors='ignore')
                 
             print(f"DEBUG: Extracted {len(text)} chars")
             
             # Risk Scan
             risk = analyze_risk_scan(text)
             print(f"DEBUG: Risk Score: {risk['score']}")
             
             # Embed
             index = get_pinecone_index()
             chunks = [text[i:i+1000] for i in range(0, len(text), 800)]
             vectors = []
             for i, chunk in enumerate(chunks[:50]):
                 emb = generate_embedding(chunk)
                 vectors.append({
                    "id": f"{key}#{i}",
                    "values": emb,
                    "metadata": {"text": chunk, "doc_id": key}
                 })
                 if len(vectors) >= 10:
                     index.upsert(vectors=vectors)
                     vectors = []
                     
             if vectors: index.upsert(vectors=vectors)
             
             # Metadata
             dynamodb.Table(os.environ.get('TABLE_NAME', 'CaseChat_Metadata')).put_item(Item={
                 'case_id': 'case_001',
                 'doc_id': key,
                 'timestamp': datetime.datetime.utcnow().isoformat(),
                 'status': 'Indexed',
                 'risk_score': risk.get('score'),
                 'risk_flags': risk.get('flags')
             })
             
             return {"statusCode": 200, "body": "Done"}

        # API HANDLERS (Simplified)
        path = event.get('rawPath') or event.get('path')
        if path == '/documents':
             resp = dynamodb.Table(os.environ.get('TABLE_NAME', 'CaseChat_Metadata')).scan()
             items = []
             for i in resp.get('Items', []):
                 items.append({
                     'id': i['doc_id'],
                     'name': i['doc_id'],
                     'date': i['timestamp'],
                     'risk_score': i.get('risk_score', 'Low'),
                     'risk_flags': i.get('risk_flags', []),
                     'status': i.get('status')
                 })
             return {"statusCode": 200, "headers": {"Content-Type":"application/json", "Access-Control-Allow-Origin":"*"}, "body": json.dumps(items, default=str)}

        if path == '/upload-url':
             # Return dummy or real
             return {"statusCode": 200, "body": json.dumps({"error": "Use Frontend Direct Upload"})}
             
    except Exception as e:
        print(f"ERROR: {e}")
        return {"statusCode": 500, "body": str(e)}
