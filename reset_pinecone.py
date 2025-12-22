import os
import time
from pinecone import Pinecone, ServerlessSpec

PINECONE_API_KEY = "pcsk_4hZwDu_dHfHj65h3qxykUyxHZ1TuYkL6qikDuovXabSWWdjw2SHWVUzqoMryBnQRCtt6g"
INDEX_NAME = "casechat-index"

def reset_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    
    # 1. List Indexes
    indexes = pc.list_indexes().names()
    print(f"Current Indexes: {list(indexes)}")
    
    # 2. Delete if exists
    if INDEX_NAME in indexes:
        print(f"Deleting {INDEX_NAME} (Incorrect Dimension)...")
        pc.delete_index(INDEX_NAME)
        time.sleep(5) # Wait for deletion
    
    # 3. Create new with 1536 (Titan Embeddings)
    print(f"Creating {INDEX_NAME} with Dimension=1536...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=1536, # Amazon Titan Text Embeddings v1
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )
    print("Index Reset Complete.")

if __name__ == "__main__":
    reset_index()
