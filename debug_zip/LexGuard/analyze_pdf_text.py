from pypdf import PdfReader

def analyze_pdf():
    file_path = "SampleContract-Shuttle.pdf"
    with open(file_path, 'rb') as f:
        reader = PdfReader(f)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    
    # Sanitize just like Lambda
    safe_text = full_text.encode('ascii', 'ignore').decode('ascii')
    
    print(f"Total Length: {len(safe_text)}")
    print("--- Searching for 'termination' ---")
    lines = safe_text.split('\n')
    found = False
    for i, line in enumerate(lines):
        if "termination" in line.lower():
            print(f"Line {i}: {line}")
            found = True
            # Print context
            start = max(0, i-2)
            end = min(len(lines), i+3)
            print("CONTEXT:")
            print("\n".join(lines[start:end]))
            print("-" * 20)
            
    if not found:
        print("Word 'termination' NOT FOUND in extracted text.")

if __name__ == "__main__":
    analyze_pdf()
