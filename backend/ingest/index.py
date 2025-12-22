import json
import os
import boto3
import urllib.parse
import datetime
import hashlib
from pinecone import Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')
# textract = boto3.client('textract') # Removing Textract due to subscription issue
audit_table = dynamodb.Table('CaseChat_Audit')

TABLE_NAME = os.environ.get('TABLE_NAME')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_INDEX = os.environ.get('PINECONE_INDEX', 'casechat-index')

def get_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX)

def extract_entities(text_chunk):
    prompt = f"""
    Human: Extract the following entities from the text below:
    - Plaintiff (Name)
    - Defendant (Name)
    - Date of Incident (YYYY-MM-DD)
    - Key Legal Terms (comma separated)
    
    Format the output as JSON only.
    
    Text: {text_chunk[:2000]}
    
    Assistant:
    """
    
    # Titan Text Payload
    payload_titan = {
        "inputText": f"System: Extract entities as JSON.\n\n{prompt}",
        "textGenerationConfig": {
            "maxTokenCount": 512,
            "stopSequences": [],
            "temperature": 0,
            "topP": 1
        }
    }
    
    # Fallback to Titan Text Express (Available)
    response = bedrock.invoke_model(
        modelId='amazon.titan-text-express-v1',
        body=json.dumps(payload_titan)
    )
    
    response_body = json.loads(response.get('body').read())
    return response_body['results'][0]['outputText']

def generate_embedding(text):
    body = json.dumps({"inputText": text})
    response = bedrock.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        contentType='application/json',
        accept='application/json',
        body=body
    )
    response_body = json.loads(response.get('body').read())
    return response_body['embedding']

def log_audit_event(action, resource, details):
    timestamp = datetime.datetime.utcnow().isoformat()
    event_str = f"{timestamp}|system_ingest|{action}|{resource}|{details}"
    event_hash = hashlib.sha256(event_str.encode()).hexdigest()
    
    audit_table.put_item(Item={
        'log_id': event_hash,
        'case_id': 'system_global',
        'timestamp': timestamp,
        'user_id': 'system_ingest_bot',
        'action': action,
        'resource': resource,
        'details': details,
        'hash': event_hash
    })

def handler(event, context):
    print("VERSION: CHUNKING_V2")
    print("Received event: " + json.dumps(event))
    
    # Get the object from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    try:
        log_audit_event("INGEST_START", key, "Started processing document")
        
        # 1. Download File (In real prod, stream it or use Textract S3 direct)
        file_path = f"/tmp/{key.split('/')[-1]}"
        s3.download_file(bucket, key, file_path)
        
        # 2. Extract Text (Switched to pypdf for reliability/cost)
        # 2. Extract Text
        full_text = ""
        if key.lower().endswith('.pdf'):
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        safe_text = text.encode('ascii', 'ignore').decode('ascii')
                        full_text += safe_text + "\n"
        elif key.lower().endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                full_text = f.read()
        else:
            print(f"Skipping unsupported file: {key}")
            return "Skipped"
        
        print(f"DEBUG: Extracted {len(full_text)} chars using PyPDF (Sanitized)")
        
        # 3. Entity Extraction (GenAI) - SKIP for now to unblock vectors
        # entities_json = extract_entities(full_text)
        entities_json = "{}"
        
        # 4. Save Metadata to DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item={
            'case_id': 'default-case', # Placeholder
            'doc_id': key,
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'status': 'Indexed',
            'text_preview': full_text[:100],
            'extracted_entities': entities_json
        })
        
        # 5. Vectors (Chunking)
        index = get_pinecone_index() # Initialize Pinecone Index
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_text(full_text)
        print(f"DEBUG: Split into {len(chunks)} chunks")
        
        vectors_to_upsert = []
        for i, chunk in enumerate(chunks):
            embedding = generate_embedding(chunk)
            vector_id = f"{key}#{i}"
            vectors_to_upsert.append({
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'text': chunk,
                    'case_id': 'default-case',
                    'doc_id': key
                }
            })
            
            # Batch upsert every 100 chunks
            if len(vectors_to_upsert) >= 100:
                index.upsert(vectors=vectors_to_upsert)
                vectors_to_upsert = []
                
        # Remainder
        if vectors_to_upsert:
            index.upsert(vectors=vectors_to_upsert)
        
        return "Success"
        
    except Exception as e:
        print(e)
        raise e
