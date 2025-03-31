
import os
import logging
import json
from datetime import datetime, timezone # Use timezone-aware datetimes
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore # Import Firestore
from google.api_core.exceptions import GoogleAPICallError # For Firestore error handling

# --- Configuration & Logging ---
# No .env needed here IF running on Cloud Run with service account permissions
# But good practice locally or if keys needed later
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Firestore Client Initialization ---
firestore_client = None
try:
    # When running on GCP (Cloud Run, Functions), Application Default Credentials
    # are automatically used if the service account has permissions.
    # No explicit key file needed in that environment.
    firestore_client = firestore.Client()
    logging.info("Firestore client initialized successfully (using Application Default Credentials).")
    firestore_available = True
except Exception as e:
    logging.error(f"Failed to initialize Firestore client: {e}. Firestore operations disabled.")
    firestore_available = False

# --- FastAPI App Setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- Background Task Function for Firestore ---
async def save_to_firestore_background(uid: str, memory_data: dict):
    """Saves the extracted memory data to Firestore in the background."""
    if not firestore_available:
        logging.error(f"Firestore client not available. Cannot save data for UID {uid}, Memory ID {memory_data.get('memory_id')}")
        return

    try:
        # Determine date string for document ID
        event_time_str = memory_data.get("finished_at") or memory_data.get("started_at")
        if event_time_str:
            event_dt = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
        else:
            event_dt = datetime.now(timezone.utc)

        date_str = event_dt.strftime('%Y-%m-%d')
        doc_id = f"{uid}_{date_str}"
        doc_ref = firestore_client.collection('raw_memories').document(doc_id)

        # Prepare the memory object WITHOUT server timestamp inside
        started_ts = None
        finished_ts = None
        try:
            if memory_data.get("started_at"):
                started_dt = datetime.fromisoformat(memory_data["started_at"].replace('Z', '+00:00'))
                if started_dt.tzinfo is None:
                   started_dt = started_dt.replace(tzinfo=timezone.utc)
                started_ts = started_dt
            if memory_data.get("finished_at"):
                finished_dt = datetime.fromisoformat(memory_data["finished_at"].replace('Z', '+00:00'))
                if finished_dt.tzinfo is None:
                    finished_dt = finished_dt.replace(tzinfo=timezone.utc)
                finished_ts = finished_dt
        except ValueError as e:
            logging.warning(f"Could not parse start/end timestamps for memory {memory_data.get('memory_id')}: {e}")

        # This object only contains data, NO commands like SERVER_TIMESTAMP
        memory_entry_data = {
            "memory_id": memory_data.get("memory_id", "UNKNOWN"),
            "transcript": memory_data.get("transcript", ""),
            "started_at": started_ts, # Firestore Timestamp (datetime object)
            "finished_at": finished_ts, # Firestore Timestamp (datetime object)
            "geolocation": memory_data.get("geolocation"), # Map or Null
            # webhook_received_at removed from here
        }

        logging.info(f"Attempting to save memory {memory_entry_data['memory_id']} to Firestore doc: {doc_id}")

        # --- Corrected Update Operation ---
        # Use ArrayUnion for the 'memories' array
        # Set a separate field 'last_webhook_update' using SERVER_TIMESTAMP
        update_data = {
            "memories": firestore.ArrayUnion([memory_entry_data]),
            "last_webhook_update": firestore.SERVER_TIMESTAMP # Set timestamp on the main document
        }
        doc_ref.set(update_data, merge=True) # merge=True creates doc/fields if they don't exist

        logging.info(f"Successfully updated Firestore doc: {doc_id} for memory {memory_entry_data['memory_id']}")

    except GoogleAPICallError as e:
        logging.error(f"Firestore API error saving data for UID {uid}, Memory ID {memory_data.get('memory_id')}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error saving data for UID {uid}, Memory ID {memory_data.get('memory_id')}: {e}")

# --- Webhook Endpoint ---
print("DEBUG: Defining endpoint @app.post('/memory_webhook')") # <<< ADD THIS LINE

@app.post('/memory_webhook') # Changed path slightly for clarity
async def memory_webhook_receiver(request: Request, background_tasks: BackgroundTasks, uid: str):
    """Receives memory creation webhook, extracts data, and queues Firestore save."""
    logging.info(f"--- Memory Webhook Received for UID: {uid} ---")
    try:
        payload = await request.json()
        logging.info(f"Received payload keys: {list(payload.keys())}")
        # You might want to log the payload structure initially for debugging:
        logging.debug(json.dumps(payload, indent=2))

    except Exception as e:
         logging.error(f"Error reading request body: {e}")
         raise HTTPException(status_code=400, detail="Could not read request body")

    # Extract necessary data
    memory_id = payload.get("id", "UNKNOWN_" + datetime.now(timezone.utc).isoformat()) # Use Omi ID if available
    started_at = payload.get("started_at")
    finished_at = payload.get("finished_at")
    geolocation = payload.get("geolocation") # This might be null

    # Extract full transcript
    transcript = ""
    if 'transcript_segments' in payload and isinstance(payload.get('transcript_segments'), list):
        texts = [
            segment['text'] for segment in payload['transcript_segments']
            if 'text' in segment and isinstance(segment.get('text'), str)
        ]
        transcript = " ".join(texts).strip()
    else:
        logging.warning(f"Payload for memory {memory_id} missing 'transcript_segments' list.")

    if not transcript:
         logging.warning(f"Transcript is empty for memory {memory_id}. Still saving metadata.")

    # Prepare data dictionary for background task
    memory_data_to_save = {
        "memory_id": memory_id,
        "transcript": transcript,
        "started_at": started_at,
        "finished_at": finished_at,
        "geolocation": geolocation,
    }

    # Add the Firestore saving task to run in the background
    # This allows us to return a response to Omi quickly
    background_tasks.add_task(save_to_firestore_background, uid, memory_data_to_save)

    logging.info(f"Queued memory {memory_id} for Firestore save. Returning 200 OK to Omi.")
    # Return a simple success message immediately
    return {"message": "Memory received and queued for processing."}

# --- Root Endpoint for Health Check ---
@app.get("/")
def read_root():
    return {"Status": "Omi Webhook Collector is running!"}

# --- Main Execution (for local testing) ---
if __name__ == "__main__":
    import uvicorn
    logging.info("Starting Uvicorn server locally...")
    # Use port 8080 locally to match Cloud Run/Dockerfile expectation
    uvicorn.run(app, host="127.0.0.1", port=8080)