import os
import boto3
import json
from pinecone import Pinecone

# HOST from Terraform output or hardcoded for debug
PINECONE_API_KEY = "pcsk_4hZwDu_dHfHj65h3qxykUyxHZ1TuYkL6qikDuovXabSWWdjw2SHWVUzqoMryBnQRCtt6g"
INDEX_NAME = "casechat-index"

def get_embedding(text):
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    response = bedrock.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({"inputText": text})
    )
    result = json.loads(response['body'].read())
    return result['embedding']

def debug_query(query):
    print(f"Querying for: '{query}'...")
    
    # 1. Embed
    vector = get_embedding(query)
    
    # 2. Search Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(INDEX_NAME)
    print(f"\nSearching for '{query}'...")
    results = index.query(
        vector=vector,
        top_k=50, # Deep search to find where the chunk is hiding
        include_metadata=True
    )
    
    print(f"\nFound {len(results['matches'])} matches:\n")

    for i, match in enumerate(results['matches']):
        text = match['metadata'].get('text', '')
        score = match['score']
        
        # Highlight interesting chunks
        prefix = ""
        if "TERMINATION" in text.upper():
            prefix = ">>> [FOUND TARGET?] "
            
        print(f"{prefix}--- Match {i+1} (Score: {score:.4f}) ---")
        if text:
            print(text[:200] + "...") 
        else:
            print("No text in metadata.")
        print()

if __name__ == "__main__":
    # debug_query("What must invoices include?")
    debug_query("What is written about early termination?")
