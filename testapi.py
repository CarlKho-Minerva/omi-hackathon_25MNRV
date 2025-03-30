from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/webhook')
def webhook(payload: dict, uid: str): # Changed 'memory' to 'payload' for clarity
    print("Received UID:", uid)
    # print("Full Payload:", payload) # You can uncomment this to see the full structure again if needed

    extracted_texts = []
    # Check if the 'segments' key exists and is a list before iterating
    if 'segments' in payload and isinstance(payload.get('segments'), list):
        for segment in payload['segments']:
            # Check if the 'text' key exists in the segment dictionary
            if 'text' in segment and isinstance(segment.get('text'), str):
                extracted_texts.append(segment['text'])
            else:
                # Optional: Log if a segment doesn't have the expected text format
                print(f"Warning: Segment missing 'text' or not a string: {segment}")
    else:
        # Optional: Log if the payload doesn't have the expected 'segments' list
        print(f"Warning: Payload missing 'segments' or not a list: {payload}")


    # --- Now you have the text ---

    # 1. Print the list of texts extracted from this specific request
    print("Extracted Texts (list):", extracted_texts)

    # 2. Or, join them into a single string for this request
    full_text_from_this_request = " ".join(extracted_texts)
    print("Extracted Text (joined):", full_text_from_this_request)

    # --- You can now use 'full_text_from_this_request' or 'extracted_texts' ---
    # Example: Check if a certain keyword is present
    if "hello" in full_text_from_this_request.lower():
        return {"message": "Greeting detected!"}
    
    # --- Return the response ---
    return {"message": full_text_from_this_request}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)