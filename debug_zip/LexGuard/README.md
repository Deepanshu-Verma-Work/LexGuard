# CaseChat - Learning Guide & Setup

Welcome to **CaseChat**. This project is designed not just to be a powerful legal tech tool, but also a **learning platform** for you to master **Python**, **AWS Serverless**, and **Generative AI**.

This guide breaks down every component we are building, explaining *why* we built it and *how* the code works.

---

## 🏗️ Architecture Overview

We are building an **Event-Driven Architecture**.
1.  **Event:** A user uploads a file.
2.  **Trigger:** S3 tells Lambda "Hey, a new file is here!".
3.  **Action:** Lambda wakes up, reads the file, reads the text, and saves it.

### Tech Stack
*   **Frontend:** React (TypeScript) - The user interface.
*   **Backend:** Python (AWS Lambda) - The logic glue.
*   **Database:** DynamoDB (Fast metadata) + OpenSearch (Vector content).
*   **AI:** AWS Bedrock (Claude 3.5 Sonnet for smarts, Titan for embeddings).
*   **IaC:** Terraform - defines all the above as code.

---

## 🐍 Python Learning Section

We have two main Python scripts. Let's dissect them.

### 1. The Ingestion Worker (`backend/ingest/index.py`)
**Goal:** Turn a raw PDF into searchable "Vectors" and structured "Entities".

**Key Concept: The Handler**
Every Lambda function has a `handler(event, context)`.
*   `event`: A JSON object containing details about what happened (e.g., "File X was uploaded to Bucket Y").
*   `context`: Runtime info (e.g., how much time is left before timeout).

**Step-by-Step Code Explanation:**

```python
# We use boto3, the AWS SDK for Python. It's how we talk to AWS services.
import boto3

def handler(event, context):
    # 1. Parsing the Event
    # The event is a nested dictionary. We dig into it to find the bucket and filename.
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # 2. Downloading the File
    # Lambda has a temporary disk at /tmp. We save the file there to read it.
    s3.download_file(bucket, key, f"/tmp/{key}")

    # 3. OCR (Optical Character Recognition)
    # We send the bytes to AWS Textract. It returns blocks of text it sees in the image/pdf.
    response = textract.detect_document_text(...)

    # 4. Generative AI (Bedrock)
    # We construct a "Prompt" - a text instruction for the AI.
    prompt = "Extract the plaintiff and defendant from this text..."
    # We send this prompt to Claude (via Bedrock) and get a JSON response back.
    entities = bedrock.invoke_model(...)
    
    # 5. Vector Embeddings
    # Computers can't understand text meaning, but they understand numbers.
    # An "Embedding" turns text into a list of numbers (vector). 
    # Similar meanings have close numbers.
    vector = generate_embedding(full_text)
    
    # 6. Storage
    # We accept the risk of "Eventual Consistency" and store data in OpenSearch.
    oss.index(...)
```

### 2. The Query Engine (`backend/query/index.py`)
**Goal:** Find the answer to the user's question using the data we prepared.

**Key Concept: RAG (Retrieval-Augmented Generation)**
LLMs (like ChatGPT) don't know your private legal data. We fix this by:
1.  **Retrieving** relevant text chunks from our database.
2.  **Augmenting** the prompt with that text.
3.  **Generating** the answer.

**Step-by-Step Code Explanation:**

```python
def handler(event, context):
    query = json.loads(event['body'])['query']

    # 1. Embed the Query
    # We turn the user's question into numbers Use the SAME model as ingestion!
    query_vector = generate_embedding(query)

    # 2. k-NN Search (k-Nearest Neighbors)
    # We ask OpenSearch: "Find the 5 document chunks mathematically closest to this query vector."
    results = oss.search(body={
        "knn": { "vector": query_vector, "k": 5 }
    })

    # 3. Audit Logging (System Architect Best Practice)
    # We log who asked what. Important for legal compliance.
    dynamodb.put_item(Item={'user': '...', 'query': query})
    
    # 4. Constructing the Context
    # We paste the found text chunks into a big string.
    context_str = "\n".join(results)

    # 5. The Final Prompt
    # We tell Claude: "Answer based ONLY on this context: {context_str}"
    # This prevents "hallucinations" (making things up).
    answer = ask_claude(prompt)
    
    return answer
```

---

## 🚀 Setup & Deploy

### Prerequisites
You need **Node.js** (for frontend) and **Terraform** (for cloud infra) installed.

### 1. Build Infrastructure
This creates the Virtual Private Cloud, Databases, and Functions.
```bash
cd infra
terraform init   # Download plugins
terraform apply  # Create resources (Type 'yes' to confirm)
```

### 2. Deploy Frontend
This starts the React development server.
```bash
cd frontend
npm install
npm run dev
```

### 3. Test It
1.  Open the URL shown by `npm run dev`.
2.  Upload a PDF.
3.  Wait a few seconds (monitor the Lambda logs in AWS Console for the 'Ingest' function).
4.  Ask a question in the chat!
