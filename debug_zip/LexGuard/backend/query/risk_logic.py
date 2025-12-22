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
        {text[:15000]}
        
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
