import json
# FORCE_UPDATE_Fix_Syntax_V5_LexGuard_Resync
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

def load_history(session_id):
    if not session_id:
        return []
    try:
        response = history_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id),
            Limit=10, # Last 5 exchanges
            ScanIndexForward=False # Get latest first, but we will reverse it for prompt
        )
        items = response.get('Items', [])
        # Sort properly by timestamp ascending for context window
        items.sort(key=lambda x: x['timestamp'])
        return items
    except Exception as e:
        print(f"Error loading history: {e}")
        return []

def save_history(session_id, user_msg, assistant_msg):
    if not session_id:
        return
    timestamp = datetime.datetime.utcnow().isoformat()
    try:
        # Save User Message
        history_table.put_item(Item={
            'session_id': session_id,
            'timestamp': f"{timestamp}#USER",
            'role': 'user',
            'content': user_msg
        })
        # Save Assistant Message
        history_table.put_item(Item={
            'session_id': session_id,
            'timestamp': f"{timestamp}#AI", # Ensure unique sort key even if fast
            'role': 'assistant',
            'content': assistant_msg
        })
    except Exception as e:
        print(f"Error saving history: {e}")

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

def get_answer_from_bedrock(query, context, history=[], model_id='anthropic.claude-3-5-sonnet-20240620-v1:0'):
    # Format history string
    history_str = ""
    for msg in history:
        history_str += f"{msg['role'].upper()}: {msg['content']}\n"
    
    prompt = f"""
    Instruction: You are an expert legal researcher. 
    Your goal is to answer the user's question based on the provided Context.
    1. Read the Context carefully.
    2. If the context contains the answer, provide it in detail.
    3. If the context contains relevant clauses but not a direct answer, INFER the answer from those clauses.
    4. Do NOT refuse to answer unless the context is completely irrelevant.
    
    Context:
    {context}
    
    Previous Conversation:
    {history_str}
    
    User's Question: {query}
    
    Answer:
    """
    
    # Use Meta Llama 3 8B Instruct - Smarter & Less Restrictive
    try:
        print(f"Generating answer with Meta Llama 3...")
        
        # Format prompt with special tokens for Llama 3 Instruct if needed, 
        # but raw text often works. Let's wrap in standard Llama 3 instruct format headers if possible,
        # or just pass the instruction block.
        # Llama 3 Instruct Format: <|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n
        
        formatted_prompt = f"""<|begin_of_text|><|start_header_id|>user<|end_header_id|>

{prompt}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

        payload_llama = {
            "prompt": formatted_prompt,
            "max_gen_len": 1024,
            "temperature": 0.1,
            "top_p": 0.9
        }
        
        response = bedrock.invoke_model(
            modelId='meta.llama3-8b-instruct-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps(payload_llama)
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body['generation']
        
    except Exception as e:
        print(f"Titan Generation Failed: {e}")
        return "I encountered an error generating the response. Please try again."

# ... content omitted ...



def log_audit_event(user_id, action, resource, details):
    timestamp = datetime.datetime.utcnow().isoformat()
    # Create a cryptographic hash of the event for immutability
    event_str = f"{timestamp}|{user_id}|{action}|{resource}|{details}"
    event_hash = hashlib.sha256(event_str.encode()).hexdigest()
    
    try:
        audit_table.put_item(Item={
            'case_id': 'system_global', # Partition key, could be specific case
            'timestamp': timestamp,
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'details': details,
            'hash': event_hash
        })
    except Exception as e:
        print(f"AUDIT FAILURE: {e}")

def analyze_risk_scan(text):
    """
    Scans the document text for high-risk legal clauses using Llama 3.
    Returns a dict: { 'score': 'High'|'Medium'|'Low', 'flags': ['Flag 1', 'Flag 2'] }
    """
    try:
        print("DEBUG: Starting Risk Analysis Scan...")
        prompt = f"""
        Instruction: Act as a Senior Legal Risk Officer.
        Analyze the following legal document text for critical risks.
        Focus on:
        1. Unlimited Liability (High Risk)
        2. Missing Termination for Convenience (Medium Risk)
        3. Unilateral Indemnification (High Risk)
        4. Non-Compete Clauses > 2 Years (Medium Risk)
        
        Return ONLY a JSON object in this format:
        {{
            "score": "High" or "Medium" or "Low",
            "flags": ["Brief description of risk 1", "Brief description of risk 2"]
        }}
        
        Document Text (Truncated):
        {text[:12000]}
        
        JSON Response:
        """
        
        
        # Llama 3 Instruct Format
        formatted_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        
        payload = {
            "prompt": formatted_prompt,
            "max_gen_len": 512,
            "temperature": 0.1
        }
        
        response = bedrock.invoke_model(
            modelId='meta.llama3-8b-instruct-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response.get('body').read())
        raw_completion = response_body['generation'].strip()
        
        # Simple JSON extraction
        try:
            start = raw_completion.find('{')
            end = raw_completion.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = raw_completion[start:end]
                print(f"DEBUG: Parsed Risk JSON: {json_str}")
                return json.loads(json_str)
            else:
                print("DEBUG: Could not find JSON in risk response")
                return {"score": "Low", "flags": ["Analysis Inconclusive"]}
        except:
             return {"score": "Low", "flags": ["Analysis Parsing Error"]}
             
    except Exception as e:
        print(f"RISK ANALYSIS FAILED: {e}")
        return {"score": "Low", "flags": []}

def handler(event, context):
    try:
        print("DEBUG EVENT:", json.dumps(event), flush=True)
        print("DEBUG: VERSION 3.1 - LEXGUARD FIX")
        # Mock user identity for MVP (In prod, get from event.requestContext.authorizer)
        user_id = "alice@firm.com"
        
# ... (Moving to top level)
# This function was incorrectly placed inside handler
# Removing it from here. It will be re-added at top-level.        # ROUTE HANDLER
        path = event.get('path') or event.get('rawPath')
        method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
        route_key = event.get('routeKey')
        
        print(f"DEBUG ROUTING: Path={path}, Method={method}, RouteKey={route_key}", flush=True)
        
        # 1. TRIGGER FROM S3 (Ingestion)
        # Check if this is an S3 Event Notification (Lambda Trigger)
        if 'Records' in event and event['Records'][0].get('eventSource') == 'aws:s3':
             print("DEBUG: S3 Event Triggered - Starting Ingestion")
             try:
                 bucket = event['Records'][0]['s3']['bucket']['name']
                 key = event['Records'][0]['s3']['object']['key']
                 
                 # Get File
                 obj = s3_client.get_object(Bucket=bucket, Key=key)
                 file_content = obj['Body'].read()
                 
                 # Extract Text (Simple PDF/Text handler)
                 # Note: For production, we'd use a robust PDF parser. 
                 # For now, we assume if it's PDF, we might need pypdf, but let's stick to simple text for the generic handler 
                 # or assume text extraction happened elsewhere. 
                 # If binary PDF, we strictly need pypdf. 
                 # Let's import pypdf safely.
                 
                 text = ""
                 if key.lower().endswith('.pdf'):
                     try:
                         import io
                         from pypdf import PdfReader
                         pdf_file = io.BytesIO(file_content)
                         reader = PdfReader(pdf_file)
                         for page in reader.pages:
                             text += page.extract_text() + "\n"
                     except ImportError:
                         print("ERROR: pypdf not found. Indexing raw bytes as string.")
                         text = str(file_content[:10000])
                 else:
                     text = file_content.decode('utf-8', errors='ignore')
                     
                 print(f"DEBUG: Extracted {len(text)} chars from {key}")
                 
                 # 1. RISK ANALYSIS (New for Veritas)
                 risk_data = analyze_risk_scan(text)
                 print(f"DEBUG: Risk Score: {risk_data['score']}")
                 
                 # 2. EMBED & INDEX (Pinecone)
                 # Chunking (Simple overlap)
                 chunk_size = 1000
                 overlap = 200
                 chunks = []
                 for i in range(0, len(text), chunk_size - overlap):
                     chunks.append(text[i:i + chunk_size])
                     
                 # Embed (Batch or Loop)
                 index = get_pinecone_index()
                 vectors = []
                 
                 for i, chunk in enumerate(chunks[:200]): # Limit to 200 chunks for demo
                     emb = generate_embedding(chunk)
                     vec_id = f"{key}#{i}"
                     vectors.append({
                        "id": vec_id,
                        "values": emb,
                        "metadata": {
                            "text": chunk,
                            "doc_id": key,
                            "source": key
                        }
                     })
                     
                     if len(vectors) >= 20: # Batch upsert
                         index.upsert(vectors=vectors)
                         vectors = []
                         
                 if vectors:
                     index.upsert(vectors=vectors)
                     
                 # 3. SAVE METADATA (DynamoDB) with RISK
                 # Save to metadata table for the UI list
                 dynamodb.Table(os.environ.get('TABLE_NAME', 'CaseChat_Metadata')).put_item(Item={
                     'case_id': 'case_001', # Hardcoded Partition Key for Demo
                     'doc_id': key,
                     'timestamp': datetime.datetime.utcnow().isoformat(),
                     'status': 'Indexed',
                     'risk_score': risk_data.get('score', 'Low'),
                     'risk_flags': risk_data.get('flags', [])
                 })
                 
                 return {"statusCode": 200, "body": "Ingestion Complete"}
                 
             except Exception as e:
                 print(f"INGESTION ERROR: {e}")
                 return {"statusCode": 500, "body": str(e)}

        if (path == '/upload-url' and method == 'GET') or route_key == 'GET /upload-url':
             filename = event.get('queryStringParameters', {}).get('filename', 'evidence.pdf')
             content_type = event.get('queryStringParameters', {}).get('contentType', 'application/pdf')
             key = f"{filename}" 
             
             presigned_url = s3_client.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': BUCKET_NAME,
                    'Key': key,
                    'ContentType': content_type
                },
                ExpiresIn=300
            )
             
             return {
                "statusCode": 200,
                "body": json.dumps({"uploadUrl": presigned_url, "key": key})
             }

        if (path == '/documents' and method == 'GET') or route_key == 'GET /documents':
             print("DEBUG: Listing documents from Metadata Table (Veritas Mode)")
             # We should read from DynamoDB now to get the Risk Scores, not S3
             # But if table is empty, fallback to s3 list?
             # Let's stick to scanning the DynamoDB table we just wrote to.
             
             table_name = os.environ.get('TABLE_NAME', 'CaseChat_Metadata') # Ensure variable is set
             try:
                 md_table = dynamodb.Table(table_name)
                 response = md_table.scan()
                 items = response.get('Items', [])
                 
                 # Format for UI
                 documents = []
                 for item in items:
                     documents.append({
                         'id': item.get('doc_id'),
                         'name': item.get('doc_id'),
                         'date': item.get('timestamp'),
                         'status': item.get('status', 'Indexed'),
                         'risk_score': item.get('risk_score', 'Low'),
                         'risk_flags': item.get('risk_flags', [])
                     })
                     
                 return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps(documents, default=str)
                }
             except:
                  # Fallback to S3 list if DynamoDB fails or is empty for old docs
                 print("DEBUG: Fallback to S3 Listing")
                 response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
                 documents = []
                 if 'Contents' in response:
                     for obj in response['Contents']:
                         documents.append({
                             'id': obj['Key'],
                             'name': obj['Key'],
                             'date': obj['LastModified'].isoformat(),
                             'status': 'Indexed',
                             'risk_score': 'Low', # Default
                             'risk_flags': []
                         })
                 return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps(documents, default=str)
                }

        elif (path == '/audit' and method == 'GET') or route_key == 'GET /audit':
             print("DEBUG: Scanning Audit Table")
             response = audit_table.scan(Limit=20) 
             items = response.get('Items', [])
             
             # Sort by timestamp desc
             items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
             
             return {
                 "statusCode": 200,
                 "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                 "body": json.dumps(items, default=str)
             }
        
        # DEFAULT: CHAT HANDLER (POST)
        body_content = event.get('body')
        if body_content:
            body = json.loads(body_content)
            query = body.get('query')
            selected_doc_id = body.get('docId', None) # Support filtering
            session_id = body.get('sessionId', 'default-session')
        else:
             print("DEBUG: No Body found")
             return {"statusCode": 400, "body": "Missing query/body"}

        print(f"DEBUG: Processing query: {query} (Doc: {selected_doc_id}) Session: {session_id}")

        # AUDIT LOG: SEARCH_INIT
        log_audit_event(user_id, "SEARCH_QUERY", "vector_store", f"Query length: {len(query)}")
        
        # Load History
        history = load_history(session_id)
        
        # 1. Embed Query
        query_vector = generate_embedding(query)
        
        # 2. Search Pinecone
        index = get_pinecone_index()
        
        filter_dict = {}
        if selected_doc_id:
            filter_dict = {"doc_id": selected_doc_id}

        # Dynamic top_k strategy
        search_k = 10
        if "termination" in query.lower():
            print("DEBUG: Keyword 'termination' detected. Boosting top_k to 8 (Titan Optimized).")
            # Titan struggles with too much noise, 8 is better than 15
            search_k = 8

        results = index.query(
            vector=query_vector,
            top_k=search_k, 
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        # Extract text from metadata
        hits = []
        for match in results['matches']:
            # Convert Pinecone object to dict explicitly if needed, but usually .to_dict() or simple dict access works
            # Safest is to rebuild the dict to ensure serializability
            hit = {
                'id': match['id'],
                'score': float(match['score']),
                'metadata': match.get('metadata', {})
            }
            hits.append(hit)
        
        context_text = ""
        for hit in hits:
             context_text += hit['metadata'].get('text', '') + "\n\n"
        
        # TRUNCATION to prevent ValidationException (Titan limit ~42k chars)
        if len(context_text) > 35000:
            print(f"DEBUG: Context too long ({len(context_text)} chars). Truncating to 35000.")
            context_text = context_text[:35000] + "...(truncated)"
        
        print(f"DEBUG: Retrieved {len(context_text)} chars of context")
        
        # 3. Generate Answer
        # Switch to Claude 3 Haiku (Standard modern fast model)
        answer = get_answer_from_bedrock(query, context_text, history, model_id='anthropic.claude-3-haiku-20240307-v1:0')
        
        # Save History
        save_history(session_id, query, answer)

        # 4. Log to Audit
        log_audit_event(user_id, "SEARCH_QUERY", "query_engine", f"Query: {query[:50]}...")
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "answer": answer,
                "sources": hits,
                "sessionId": session_id
            })
        }
        
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return {"statusCode": 500, "body": str(e)}
