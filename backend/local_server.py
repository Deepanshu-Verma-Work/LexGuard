import os
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from query.index import handler  # Import the Lambda handler

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for local development

# Helper to mimic Lambda Event
def create_lambda_event(path, method, body=None, query_params=None):
    return {
        "rawPath": path,
        "path": path,
        "httpMethod": method,
        "queryStringParameters": query_params or {},
        "body": json.dumps(body) if body else None,
        "requestContext": {
            "http": {
                "method": method
            }
        }
    }

# Wrapper function to invoke Lambda Handler
def invoke_lambda(path):
    method = request.method
    body = request.get_json(silent=True)
    query_params = request.args.to_dict()

    event = create_lambda_event(path, method, body, query_params)
    logger.info(f"Invoking Lambda for {method} {path}")
    
    response = handler(event, None)
    
    # Parse Lambda Response
    status_code = response.get('statusCode', 200)
    response_body = response.get('body', '{}')
    
    try:
        # Try to parse JSON body
        if isinstance(response_body, str):
            response_data = json.loads(response_body)
        else:
            response_data = response_body
    except json.JSONDecodeError:
        response_data = response_body
        
    return jsonify(response_data), status_code

@app.route('/upload-url', methods=['GET'])
def upload_url():
    return invoke_lambda('/upload-url')

@app.route('/documents', methods=['GET'])
def documents():
    return invoke_lambda('/documents')

@app.route('/chat', methods=['POST'])
def chat():
    return invoke_lambda('/chat')

@app.route('/audit', methods=['GET'])
def audit():
    return invoke_lambda('/audit')

if __name__ == '__main__':
    print("--- STARTING LOCAL PROXY SERVER (LexGuard) ---")
    print("Mapping: localhost:8000 -> backend/query/index.py")
    print("Ensure you have AWS_PROFILE or valid ~/.aws/credentials set.")
    app.run(port=8000, debug=True)
