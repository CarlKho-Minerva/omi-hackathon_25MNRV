import os
import json
import logging
import functions_framework # Google Cloud Functions framework
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from google.api_core.exceptions import GoogleAPICallError, NotFound
import openai
import httpx # Import httpx
import pytz 

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
        Analyze the following conversation transcript(s) from an entire day captured by the Omi Device V2. Your goal is to provide insights that are personalized, supportive, and encourage reflection and gratitude. Focus on extracting meaning and actionable observations *directly* from the user's interactions.

        Provide the following details in JSON format:

        1.  "daily_emoji": Suggest a single standard emoji that best represents the overall mood or primary theme of the user's day *as reflected in their conversations*.
        2.  "summary": A brief summary (2-4 sentences) capturing the essence of the user's day, highlighting key interactions, activities, or expressed feelings mentioned in the transcript. Make it feel personal *to the user*.
        3.  "gratitude_points": A JSON array of 2-3 specific strings highlighting positive moments, instances of connection, kindness received/given, or accomplishments *explicitly mentioned or clearly inferable from the conversations*. Phrase these as prompts for gratitude, referencing the specific context where possible (e.g., "Remember the supportive comment you received during the project discussion," "Appreciate the shared laugh about [topic]").
        4.  "learned_terms": A JSON array of objects. Identify unique jargon, technical terms, names, or concepts mentioned that the user might want a quick reminder of. For each, provide a brief definition/context *based on how it was used in the conversation*. Format: [{{"term": "...", "definition": "..."}}]. Limit to 3-5 key terms.
        5.  "little_things": A JSON array of objects. Identify small, potentially actionable observations based on preferences, desires, needs, or passing comments *mentioned by the user or others in the conversations*. Link the `mention` directly to a specific conversational context. The `suggested_action` should be a thoughtful, personalized suggestion for a small act of kindness, self-care, or remembrance inspired *by that specific moment*. **Since speaker diarization is unavailable, refer to others generally (e.g., "the person you spoke with about X," "someone mentioned...")**. Format: [{{"mention": "...", "suggested_action": "..."}}]. Limit to 2-4 items. The goal is to spread love.
        6.  "mentor_advice": Provide a single, constructive, concise, and hard-to-swallow but needed-to-hear piece of advice (1-2 sentences) rooted in specific patterns, challenges, or opportunities observed *in the user's interactions* throughout the day. Specifically cite that interaction. Focus on communication, well-being, goals, or relationships. Frame it supportively.
        7.  "action_items": A JSON array of strings, listing clear, granular, generous amount, concrete action items or tasks that were *explicitly stated* in the conversations as needing to be done *by the user*, or assigned to them. Do not include suggestions from 'little_things' here. Ensure these are direct obligations mentioned. Feel free to create multiple tasks, the user will curate these later, so dont forget the tiniest details.

        Transcript(s):
        "{transcript}"

        Return ONLY the valid JSON object. Ensure all keys are present, even if arrays are empty ([]).

        Example JSON format reflecting the enhanced requirements:
        {{
        "daily_emoji": "🤝",
        "summary": "Sounds like a day with collaborative moments, particularly around the project planning. You also shared a nice chat about food preferences later on.",
        "gratitude_points": [
            "Appreciate the moment someone agreed with your approach during the team sync.",
            "Be grateful for the shared enjoyment discussing different cuisines.",
            "Acknowledge your effort in articulating the project requirements clearly."
        ],
        "learned_terms": [
            {{"term": "Kanban Board", "definition": "Mentioned during the project sync; it's a visual tool for managing workflow."}},
            {{"term": "SOP", "definition": "Standard Operating Procedure; discussed in relation to process documentation."}}
        ],
        "little_things": [
            {{"mention": "In your conversation about spicy food, the person you were talking with mentioned loving egg tarts.", "suggested_action": "Consider picking up some egg tarts for them if you're near a bakery soon, as a thoughtful gesture."}},
            {{"mention": "You briefly mentioned needing to organize your desktop files during the morning chat.", "suggested_action": "Maybe take 10 minutes tomorrow to quickly tidy up those digital files?"}}
        ],
        "mentor_advice": "It's great you're connecting with colleagues! Remember to also schedule short breaks during busy days to maintain your energy and focus.",
        "action_items": [
            "Send the meeting minutes to the project team.",
            "Draft the initial SOP document by Friday."
            "Follow up with the person you spoke with about the Kanban Board setup.",

        ]
        }}
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": "You are an AI assistant analyzing daily conversation transcripts. Output structured JSON containing insightful summaries, actionable items (be detailed on the tasks, be succinct with the rest), learned concepts, and supportive advice."},
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

    # Check if a specific date was passed via query parameter
    explicit_date_str = request.args.get("date")

    if explicit_date_str:
        # Use the explicitly provided date (e.g., for testing past dates)
        target_date_str = explicit_date_str
        logging.info(f"Processing reflections for User ID: {user_id}, Using explicit Date: {target_date_str}")
    else:
        # No date provided (likely triggered by scheduler), calculate based on target timezone
        try:
            # Define the target timezone (e.g., Pacific Time)
            target_tz_name = "America/Los_Angeles" # Pacific Time zone
            target_tz = pytz.timezone(target_tz_name)

            # Get the current time in UTC
            now_utc = datetime.now(timezone.utc)

            # Convert current UTC time to the target timezone
            now_target_tz = now_utc.astimezone(target_tz)

            # --- Decide which day to process ---
            # If the job runs late at night (e.g., 9 PM PT), 'now_target_tz.date()' IS the day we want to process.
            # If the job runs early morning (e.g., 2 AM PT), 'now_target_tz.date()' is technically the *next* day,
            # so we actually want to process the day *before* 'now_target_tz.date()'.

            # Let's assume the scheduler runs EOD/Night (like 9 PM PT).
            # In this case, the date part of the current time in the target timezone IS the correct date to process.
            target_date = now_target_tz.date()

            # --- Alternative logic if running EARLY morning (e.g., 2 AM PT) ---
            # If you schedule the job for after midnight in your local time (e.g., 2 AM PT),
            # you want the *previous* day's data. Uncomment the next two lines in that case:
            # target_date = now_target_tz.date() - timedelta(days=1)
            # logging.info(f"Scheduler running early morning, processing previous day: {target_date.strftime('%Y-%m-%d')}")
            # --- End Alternative logic ---

            target_date_str = target_date.strftime('%Y-%m-%d')
            logging.info(f"Processing reflections for User ID: {user_id}, Calculated Target Date ({target_tz_name}): {target_date_str}")

        except Exception as e:
            logging.error(f"Error calculating target date: {e}. Falling back to UTC date.")
            # Fallback to UTC date on error, although this might process the wrong day
            target_date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            logging.warning(f"Processing reflections for User ID: {user_id}, Using UTC Date Fallback: {target_date_str}")

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