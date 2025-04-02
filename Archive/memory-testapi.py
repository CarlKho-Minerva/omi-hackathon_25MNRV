from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import os
import openai # Import the openai library
import json # Import json for nice printing
from dotenv import load_dotenv # Import dotenv

# Load environment variables from .env file
load_dotenv()

# --- OpenAI Client Setup ---
# The client now uses the OPENAI_API_KEY from the .env file
try:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    openai_available = True
except Exception as e:
    print(f"Warning: Failed to initialize OpenAI client. Story generation disabled. Error: {e}")
    openai_available = False
# -------------------------
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
def webhook(payload: dict, uid: str):
    print("--------------------")
    print("Received Memory Creation Trigger for UID:", uid)

    # --- Print the Full Memory Payload (for inspection) ---
    print("Full Payload Received:")
    try:
        # Use json.dumps for pretty printing
        print(json.dumps(payload, indent=2))
    except Exception as e:
        print(f"(Could not pretty-print payload: {e})")
        print(payload) # Fallback to regular print
    # ------------------------------------------------------

    extracted_texts = []
    full_transcript = ""

    # --- Correctly parse the Memory Creation payload ---
    # Check if the 'transcript_segments' key exists and is a list
    if 'transcript_segments' in payload and isinstance(payload.get('transcript_segments'), list):
        for segment in payload['transcript_segments']:
            # Check if the 'text' key exists in the segment dictionary
            if 'text' in segment and isinstance(segment.get('text'), str):
                extracted_texts.append(segment['text'])
            else:
                print(f"Warning: Segment missing 'text' or not a string: {segment}")

        # Join all segments into one transcript string
        full_transcript = " ".join(extracted_texts)
        print("\nExtracted Full Transcript:", full_transcript)

    else:
        # Log if the payload doesn't have the expected 'transcript_segments' list
        print(f"Warning: Payload missing 'transcript_segments' or not a list.")
        full_transcript = "Transcript could not be extracted." # Set default


    # --- Generate Funny Story using OpenAI ---
    generated_story = "Could not generate story (OpenAI unavailable or transcript empty)."
    if openai_available and full_transcript and full_transcript != "Transcript could not be extracted.":
        try:
            print("\nAttempting to generate funny story...")
            prompt = f"""
            Based on the following conversation transcript, write a short, creative, and funny story (2-4 sentences).
            Do not just summarize. Invent a humorous scenario inspired by the transcript.

            Transcript:
            "{full_transcript}"

            Funny Story:
            """

            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # Or "gpt-4" if you have access
                messages=[
                    {"role": "system", "content": "You are a witty storyteller."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.8 # Adjust for more/less randomness
            )
            # Ensure response and choices are valid before accessing
            if response.choices and response.choices[0].message:
                 generated_story = response.choices[0].message.content.strip()
                 print("Generated Story:", generated_story)
            else:
                print("Warning: OpenAI response structure was unexpected.")
                generated_story = "Failed to parse story from OpenAI response."

        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            generated_story = f"Error generating story: {e}"
    elif not openai_available:
         print("Skipping story generation: OpenAI client not available.")
    else:
        print("Skipping story generation: Transcript was empty.")
    # -----------------------------------------

    print("--------------------")
    # --- Return the generated story (or error) as the message ---
    return {"message": generated_story}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)