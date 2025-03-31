import os
import json
import logging
import functions_framework # Google Cloud Functions framework
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from google.api_core.exceptions import GoogleAPICallError, NotFound
import openai
import httpx # Import httpx

from dotenv import load_dotenv

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Load environment variables from .env file ---
load_dotenv()

# --- Environment Variables (Read at Function Startup) ---
# These MUST be set when deploying the function
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# We'll get User ID from request for testing, or could be env var for single user
# TARGET_USER_ID = os.environ.get("TARGET_USER_ID") # Optional: For single-user focus

# --- Flush stdout for better logging in containerized environments ---
logging.info("Starting application")
import sys
sys.stdout.flush()

# --- API Client Initialization ---
firestore_client = None
openai_client = None
clients_initialized = False

try:
    # Initialize Firestore client (uses ADC automatically on GCP)
    firestore_client = firestore.Client()

    # Initialize OpenAI client
    if OPENAI_API_KEY:
        # Explicitly create an httpx client.
        # If you need proxies, configure them here: http_client = httpx.Client(proxies={...})
        http_client = httpx.Client()
        openai_client = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            http_client=http_client # Pass the explicit client
        )
        logging.info("OpenAI client initialized.")
    else:
        logging.error("OPENAI_API_KEY environment variable not set!")

    if firestore_client and openai_client:
         clients_initialized = True
         logging.info("Firestore and OpenAI clients initialized successfully.")
    else:
        logging.error("One or more clients failed to initialize.")

except Exception as e:
    logging.error(f"Fatal error during client initialization: {e}")
    clients_initialized = False # Ensure flag is False

# --- Helper: OpenAI Processing ---
def process_transcript_with_openai(transcript: str) -> dict:
    """Uses OpenAI to generate structured reflection data from transcript."""
    default_error_response = {
        "daily_emoji": "⚠️", "summary": "AI Processing Failed", "gratitude_points": [],
        "learned_terms": [], "little_things": [], "mentor_advice": "Could not generate advice.",
        "action_items": []
    }

    if not openai_client or not transcript:
        logging.warning("Skipping OpenAI processing (client unavailable or empty transcript).")
        return default_error_response

    logging.info(f"Processing transcript ({len(transcript)} chars) with OpenAI...")
    prompt = f"""
    Analyze the following conversation transcript(s) from an entire day and provide the following details in JSON format:
    1.  "daily_emoji": Suggest a single standard emoji that best represents the overall day's mood or primary theme.
    2.  "summary": A brief summary (2-4 sentences) capturing the essence or main activities of the day based on the conversations.
    3.  "gratitude_points": A JSON array of 2-3 specific strings highlighting positive moments, interactions, or accomplishments mentioned that the user could be grateful for.
    4.  "learned_terms": A JSON array of objects. Identify unique jargon, technical terms, names, or concepts mentioned. For each, provide a brief definition/context suitable for a quick reminder. Format: [{{"term": "...", "definition": "..."}}]. Limit to 3-5 key terms.
    5.  "little_things": A JSON array of objects. Identify small, potentially actionable observations or mentions about preferences, desires, or needs of the user or others mentioned (e.g., someone liking donuts, needing milk). Format: [{{"mention": "...", "suggested_action": "..."}}]. Limit to 2-4 items. Generate a concise 'suggested_action' for each.
    6.  "mentor_advice": Provide a single, constructive, and concise piece of advice (1-2 sentences) based on the day's conversations, focusing on communication, productivity, goals, or well-being. Be supportive but direct.
    7.  "action_items": A JSON array of strings, listing clear, concrete action items or tasks explicitly mentioned for the user or assigned to them. Do not include the 'suggested_action' from 'little_things' here.

    Transcript(s):
    "{transcript}"

    Return ONLY the valid JSON object. Ensure all keys are present, even if arrays are empty ([]).
    Example JSON format:
    {{
      "daily_emoji": "🚀",
      "summary": "Productive day focused on project X planning and a helpful chat with Sarah.",
      "gratitude_points": ["Completed the difficult report.", "Received positive feedback from the team."],
      "learned_terms": [{{"term": "OKR", "definition": "Objectives and Key Results - goal-setting framework."}}],
      "little_things": [{{"mention": "User mentioned needing coffee.", "suggested_action": "Add coffee to shopping list."}}],
      "mentor_advice": "Consider delegating the documentation task to free up time for strategic planning.",
      "action_items": ["Email Alex the final document by EOD.", "Schedule follow-up meeting."]
    }}
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo-0125", # Or gpt-4 if preferred/available
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": "You are an AI assistant analyzing daily conversation transcripts. Output structured JSON containing insightful summaries, actionable items, learned concepts, and supportive advice."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000, # Increase if summaries/lists get truncated
            temperature=0.6 # Balanced temperature
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            content = response.choices[0].message.content.strip()
            logging.info(f"OpenAI Raw Response: {content}")
            try:
                processed_data = json.loads(content)
                # Basic validation (check if all keys exist)
                required_keys = ["daily_emoji", "summary", "gratitude_points", "learned_terms", "little_things", "mentor_advice", "action_items"]
                if all(k in processed_data for k in required_keys):
                     # Further validation/cleaning (ensure arrays are lists)
                    for key in ["gratitude_points", "learned_terms", "little_things", "action_items"]:
                        if not isinstance(processed_data.get(key), list):
                            logging.warning(f"OpenAI response for '{key}' was not a list, correcting to empty list.")
                            processed_data[key] = []
                    logging.info("OpenAI processing successful.")
                    return processed_data
                else:
                    missing_keys = [k for k in required_keys if k not in processed_data]
                    logging.error(f"OpenAI response missing required JSON keys: {missing_keys}")
                    return default_error_response
            except json.JSONDecodeError as json_err:
                logging.error(f"Failed to parse JSON from OpenAI: {json_err}. Response: {content}")
                return default_error_response
        else:
            logging.error("OpenAI response structure was unexpected or empty.")
            return default_error_response
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}")
        return default_error_response

# --- Cloud Function Entry Point ---
@functions_framework.http # Decorator to make this an HTTP-triggered function
def daily_process_memories(request):
    """HTTP Cloud Function to process daily memories."""
    logging.info("Daily processing function triggered.")

    if not clients_initialized:
         logging.error("Clients not initialized. Aborting function.")
         # Return 500 Internal Server Error
         return ("Server configuration error", 500)

    # --- Determine Target User and Date ---
    # For testing, allow passing UID via request, fallback to env var or hardcoded
    user_id = request.args.get("uid", os.environ.get("TARGET_USER_ID", "ckVQW3MVAoenlOdYhHLt5K3zPpW2")) # <<< REPLACE DEFAULT
    if user_id == "ckVQW3MVAoenlOdYhHLt5K3zPpW2":
         logging.warning("Using default test user ID. Set TARGET_USER_ID env var or pass 'uid' query param.")

    # Get date (default to yesterday, assuming job runs early morning, or today if run at night)
    # Let's assume it runs EOD/night for "today's" reflection
    target_date_str = request.args.get("date", datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    logging.info(f"Processing reflections for User ID: {user_id}, Date: {target_date_str}")

    # --- Read Raw Memories from Firestore ---
    full_day_transcript = ""
    try:
        doc_id = f"{user_id}_{target_date_str}"
        doc_ref = firestore_client.collection('raw_memories').document(doc_id)
        doc_snapshot = doc_ref.get()

        if doc_snapshot.exists:
            data = doc_snapshot.to_dict()
            memories = data.get("memories", [])
            if memories:
                # Aggregate transcripts, maybe sort by start time first if needed
                # For simplicity, just join them
                all_texts = [m.get("transcript", "") for m in memories if m.get("transcript")]
                full_day_transcript = "\n\n---\n\n".join(all_texts) # Join with separators
                logging.info(f"Found {len(memories)} memories. Aggregated transcript length: {len(full_day_transcript)}")
            else:
                logging.info(f"Document {doc_id} exists but has no 'memories' array or it's empty.")
        else:
            logging.info(f"No raw memory document found for {doc_id}.")
            # Return success, as there's nothing to process
            return (f"No data found for {user_id} on {target_date_str}", 200)

    except GoogleAPICallError as e:
        logging.error(f"Firestore API error reading raw_memories for {doc_id}: {e}")
        return ("Error reading data from database", 500)
    except Exception as e:
        logging.error(f"Unexpected error reading raw_memories for {doc_id}: {e}")
        return ("Internal server error during data read", 500)

    # --- Process with OpenAI ---
    if not full_day_transcript:
         logging.info("Transcript is empty after aggregation. Nothing to process with OpenAI.")
         processed_data = {"message": "No transcript content found for the day."} # Indicate nothing to process
         # Still save a record? Optional. Let's just return for now.
         return (f"No transcript content found for {user_id} on {target_date_str}", 200)
    else:
         processed_data = process_transcript_with_openai(full_day_transcript)

    # --- Write Processed Results to Firestore ---
    try:
        processed_doc_id = f"{user_id}_{target_date_str}"
        processed_doc_ref = firestore_client.collection('daily_reflections').document(processed_doc_id)

        # Add processing timestamp
        processed_data_to_save = processed_data.copy() # Avoid modifying original dict if reused
        processed_data_to_save["processed_at"] = firestore.SERVER_TIMESTAMP

        processed_doc_ref.set(processed_data_to_save)
        logging.info(f"Successfully saved processed reflection to Firestore doc: {processed_doc_id}")

    except GoogleAPICallError as e:
        logging.error(f"Firestore API error writing daily_reflections for {processed_doc_id}: {e}")
        # We processed but couldn't save, return an error
        return ("Error saving processed data", 500)
    except Exception as e:
        logging.error(f"Unexpected error writing daily_reflections for {processed_doc_id}: {e}")
        return ("Internal server error during data save", 500)

    # --- Return Success ---
    logging.info("Daily processing completed successfully.")
    return ("Processing complete", 200) # HTTP Success