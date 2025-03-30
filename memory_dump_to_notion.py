import os
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import openai
import uvicorn
from notion_client import Client as NotionClient
from notion_client.helpers import is_full_page # To check Notion API responses

# --- Configuration & Logging ---
load_dotenv() # Load variables from .env file
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- API Client Initialization ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

openai_client = None
openai_available = False
if OPENAI_API_KEY:
    try:
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        openai_available = True
        logging.info("OpenAI client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
else:
    logging.warning("OPENAI_API_KEY not found in environment. OpenAI processing disabled.")

notion_client = None
notion_available = False
if NOTION_API_KEY and NOTION_DATABASE_ID:
    try:
        notion_client = NotionClient(auth=NOTION_API_KEY)
        notion_available = True
        logging.info("Notion client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Notion client: {e}")
else:
    logging.warning("NOTION_API_KEY or NOTION_DATABASE_ID not found. Notion integration disabled.")

# --- FastAPI App Setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- Helper Functions ---

def extract_transcript(payload: dict) -> str:
    """Extracts and joins transcript text from memory payload."""
    full_transcript = ""
    if 'transcript_segments' in payload and isinstance(payload.get('transcript_segments'), list):
        texts = [
            segment['text'] for segment in payload['transcript_segments']
            if 'text' in segment and isinstance(segment.get('text'), str)
        ]
        full_transcript = " ".join(texts).strip() # Added strip()
    else:
        logging.warning("Payload missing 'transcript_segments' list.")
    return full_transcript

def process_transcript_with_openai(transcript: str) -> dict:
    """Uses OpenAI to generate title, summary, action items, category, and emoji."""
    if not openai_available or not transcript:
        logging.warning("Skipping OpenAI processing (unavailable or empty transcript).")
        return {
            "title": "Processing Failed / No Transcript",
            "summary": "Could not process transcript.",
            "action_items": [],
            "category": "Uncategorized",
            "emoji": "❓"
        }

    logging.info("Processing transcript with OpenAI...")
    prompt = f"""
    Analyze the following conversation transcript and provide the following details in JSON format:
    1.  "title": A concise and descriptive title (max 10 words).
    2.  "summary": A brief summary (2-4 sentences).
    3.  "action_items": A JSON array of strings for any action items or tasks mentioned. If none, infer potential next steps or return an empty array [].
    4.  "category": Suggest a single, relevant category (e.g., "Work Meeting", "Personal Catch-up", "Planning", "Ideas", "Support Call", "Shopping", "Travel").
    5.  "emoji": Suggest a single standard emoji that best represents the conversation.

    Transcript:
    "{transcript}"

    Return ONLY the JSON object. Example:
    {{
      "title": "Weekend Plan Discussion",
      "summary": "Discussed plans for the weekend hike.",
      "action_items": ["Check weather forecast", "Pack snacks"],
      "category": "Planning",
      "emoji": "⛰️"
    }}
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo-0125", # Good model for JSON
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": "You are an AI assistant skilled at analyzing transcripts and outputting structured JSON data."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400, temperature=0.5
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            content = response.choices[0].message.content.strip()
            logging.info(f"OpenAI Raw Response: {content}")
            try:
                processed_data = json.loads(content)
                # Validate keys and ensure action_items is a list
                if all(k in processed_data for k in ["title", "summary", "action_items", "category", "emoji"]):
                    if not isinstance(processed_data.get("action_items"), list):
                        processed_data["action_items"] = [] # Fix if not a list
                    logging.info(f"OpenAI Processed Data: {processed_data}")
                    return processed_data
                else:
                    raise ValueError("Missing keys in OpenAI JSON response")
            except json.JSONDecodeError as json_err:
                logging.error(f"Failed to parse JSON from OpenAI: {json_err}. Response: {content}")
                raise ValueError(f"Invalid JSON from OpenAI: {content}") from json_err
        else:
            raise ValueError("Unexpected OpenAI response structure")
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}")
        return {"title": "OpenAI Error", "summary": f"Error: {e}", "action_items": [], "category": "Error", "emoji": "❗️"}

# REPLACE the old create_notion_page_simple function with this one:
def create_notion_page_simple(database_id: str, omi_payload: dict, processed_data: dict, transcript: str):
    """Creates a Notion page with ONLY Title property, dumping all info into the body."""
    if not notion_available:
        logging.warning("Skipping Notion page creation (Notion client unavailable).")
        return None

    logging.info(f"Attempting to create Notion page in DB: {database_id}")

    # --- Get data for the page ---
    page_title = processed_data.get("title", "Untitled Omi Memory") # Get Title from OpenAI
    summary = processed_data.get("summary", "No summary available.")
    category = processed_data.get("category", "Uncategorized")
    action_items = processed_data.get("action_items", [])
    emoji = processed_data.get("emoji", "📄") # Get Emoji from OpenAI
    start_time_iso = omi_payload.get("started_at")
    end_time_iso = omi_payload.get("finished_at")
    geolocation = omi_payload.get("geolocation")
    location_str = f"Lat: {geolocation['latitude']}, Lon: {geolocation['longitude']}" if geolocation else "No location data"
    date_str = f"Started: {start_time_iso}" if start_time_iso else "No start date"
    if end_time_iso and end_time_iso != start_time_iso:
         date_str += f"\nEnded: {end_time_iso}"

    # --- Construct Notion Properties (ONLY THE TITLE PROPERTY) ---
    # Based on your screenshot, your Title property is called "Name".
    # If it's called something else, change "Name" below.
    properties = {
        "Name": {  # <<< This MUST match the name of your database's Title column
            "title": [{"type": "text", "text": {"content": page_title}}]
        }
        # NO OTHER PROPERTIES HERE!
    }

    # --- Construct Notion Page Body (Children Blocks) ---
    # We will put EVERYTHING else here.
    children_blocks = [
        # Summary Section
        {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Summary"}}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": summary}}]}},

        # Action Items Section
        {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Action Items"}}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "\n".join(f"- {item}" for item in action_items) if action_items else "None"}}]}}, # Format as bullet points

        # Details Section
        {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Details"}}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Category: {category}"}}]}}, # Category on its own line
        {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": date_str}}]}}, # Dates on their own line(s)
        {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Location: {location_str}"}}]}}, # Location on its own line

        # Transcript Section
        {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Full Transcript"}}]}},
        # Add transcript chunks below
    ]
    # Add transcript chunks
    max_block_length = 1990 # Notion's limit per block
    if transcript:
        start = 0
        while start < len(transcript):
            chunk = transcript[start:start+max_block_length]
            children_blocks.append({
                "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}
            })
            start += max_block_length
    else:
         # Add placeholder if no transcript
         children_blocks.append({
            "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "(No transcript extracted)"}}]}
        })

    # --- Call Notion API ---
    try:
        response = notion_client.pages.create(
            parent={"database_id": database_id},
            icon={"type": "emoji", "emoji": emoji}, # Set page icon using OpenAI emoji
            properties=properties,                # Pass ONLY the title property
            children=children_blocks                 # Pass everything else as page content
        )
        # Check if the response looks like a full page object
        if is_full_page(response):
             logging.info(f"Successfully created Notion page: ID={response['id']}, URL={response.get('url', 'N/A')}")
             return response
        else:
            # Log if the response doesn't seem right (might be partial)
            logging.error(f"Notion API might have returned partial or unexpected response: {response}")
            return None
    except Exception as e:
        # Log any error during the API call
        logging.error(f"Error creating Notion page: {e}")
        return None

# --- Webhook Endpoint ---
@app.post('/webhook') # Specific path for this endpoint
async def webhook_memory_dump(request: Request, uid: str):
    logging.info(f"--- MEMORY DUMP Trigger for UID: {uid} ---")
    try:
        payload = await request.json()
        logging.info(f"Received payload keys: {list(payload.keys())}")
    except Exception as e:
         logging.error(f"Error reading request body: {e}")
         raise HTTPException(status_code=400, detail="Could not read request body")

    full_transcript = extract_transcript(payload)
    processed_data = process_transcript_with_openai(full_transcript) # Will use defaults if transcript empty

    notion_page = create_notion_page_simple(
        database_id=NOTION_DATABASE_ID,
        omi_payload=payload,
        processed_data=processed_data,
        transcript=full_transcript
    )

    status = "Notion page created." if notion_page else "Failed to create Notion page."
    logging.info(f"--- Processing Finished for UID: {uid}. Status: {status} ---")
    return {"message": f"Memory received. {status}", "title_used": processed_data.get("title")}

# --- Main Execution ---
if __name__ == "__main__":
    if not all([OPENAI_API_KEY, NOTION_API_KEY, NOTION_DATABASE_ID]):
         logging.error("CRITICAL: Missing required environment variables (OPENAI_API_KEY, NOTION_API_KEY, NOTION_DATABASE_ID). Check .env file. Exiting.")
         exit(1)
    logging.info("Starting Uvicorn server...")
    uvicorn.run(app, host="127.0.0.1", port=8000) # Runs on http://127.0.0.1:8000