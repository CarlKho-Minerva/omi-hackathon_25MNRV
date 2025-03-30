# Omi Integration App - Local Development Setup (FastAPI + Ngrok)

This project demonstrates how to set up a local development environment for creating Omi Integration Apps using webhooks (where Omi sends data to your app). It uses a Python FastAPI backend running on your local machine and Ngrok to expose that local server to the internet, allowing Omi's webhooks to reach it.

We cover two main webhook examples:
1.  **Real-Time Transcript Processor:** Processes speech live as it happens.
2.  **Memory Creation Trigger:** Processes the full conversation data after Omi saves it as a memory.

## Overview & Important Concepts

*   **Omi App Type:** External Integration (using Webhooks/Triggers)
*   **Backend:** Python with FastAPI framework
*   **Webhook Tunneling:** Ngrok
*   **Key Distinction: Webhooks vs. Integration Imports**
    *   **Webhooks (Triggers - Covered Here):** Omi *sends* data *to your app's endpoint* when specific events occur (e.g., new transcript segment, memory created, raw audio chunk ready). Your app *reacts* to incoming data. This requires setting up a webhook URL in Omi's Developer Settings or App Configuration.
    *   **Integration Imports (API Calls - *Not* Detailed Here):** *Your app* proactively *sends data to Omi* or *requests data from Omi* using Omi's official API (`api.omi.me`). Examples include creating conversations from external text, adding specific memories, or reading existing conversations/memories. This requires generating API keys within your Omi App's settings and making authenticated API calls *from* your backend. (See official Omi docs for "Import Integrations").

## Prerequisites

1.  **Python 3.x:** Check with `python --version` or `python3 --version`.
2.  **pip:** Python's package installer.
3.  **Omi Mobile App:** Installed on your device.
4.  **Ngrok Account:** Free account at [ngrok.com](https://ngrok.com/).
5.  **Ngrok Executable:** Installed via `brew install ngrok` (macOS) or downloaded from [ngrok.com/download](https://ngrok.com/download).
6.  **(Optional but Recommended) OpenAI Account & API Key:** Needed for the Memory Creation Trigger example if you want automatic story generation. Get keys from [platform.openai.com](https://platform.openai.com/).
7.  **Virtual Environment Tool (Recommended):** `venv`.
8.  **Basic Terminal/Command Line Knowledge.**

## Core Setup Steps (Common to Both Examples)

1.  **Create Project Directory & `cd` into it.**

2.  **Create & Activate Python Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate # macOS/Linux
    # venv\Scripts\activate # Windows
    ```

3.  **Install Dependencies:**
    Create a file named `requirements.txt`:
    ```txt
    fastapi
    uvicorn[standard]
    openai # Needed for the memory-testapi.py example
    requests # Good practice for potential future API calls
    ```
    Install:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Ngrok Authtoken:**
    *   Get your token from [dashboard.ngrok.com](https://dashboard.ngrok.com/) -> "Your Authtoken".
    *   Run: `ngrok config add-authtoken YOUR_NGROK_TOKEN`

## Example 1: Real-Time Transcript Processor (`realtime-testapi.py`)

This app receives live transcript segments and can react immediately (e.g., detect keywords).

1.  **Create `realtime-testapi.py`:**

    ```python
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi import FastAPI

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    @app.post('/webhook_realtime') # Using a specific path
    def webhook_realtime(payload: dict, uid: str):
        print("--- REALTIME ---")
        print("Received UID:", uid)

        extracted_texts = []
        if 'segments' in payload and isinstance(payload.get('segments'), list):
            for segment in payload['segments']:
                if 'text' in segment and isinstance(segment.get('text'), str):
                    extracted_texts.append(segment['text'])
                else:
                    print(f"Warning: Segment missing 'text' or not a string: {segment}")
        else:
            print(f"Warning: Payload missing 'segments' or not a list: {payload}")

        message_to_return = "Processed realtime segments." # Default message
        if extracted_texts:
            full_text_from_this_request = " ".join(extracted_texts)
            print("Extracted Text:", full_text_from_this_request)

            # --- YOUR REALTIME PROCESSING LOGIC ---
            if "cookie" in full_text_from_this_request.lower():
                print("!!! COOKIE DETECTED !!!")
                message_to_return = "Adam no cookies!" # Send notification back to Omi
            # --------------------------------------
        else:
            print("No text extracted in this payload.")

        print("--- END REALTIME ---")
        return {"message": message_to_return} # Return JSON for Omi notifications

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8000)
    ```

2.  **Running:**
    *   **Terminal 1:** `python realtime-testapi.py`
    *   **Terminal 2:** `ngrok http 8000` (Copy the `https://...` Forwarding URL)

3.  **Omi Configuration:**
    *   Create/Edit Omi App -> External Integration
    *   Trigger Type: **`Transcript Processor`**
    *   Webhook URL: `YOUR_NGROK_HTTPS_URL/webhook_realtime` (Use the path from the code!)
    *   Install the app.

4.  **Testing:** Talk to Omi. Watch Terminal 1 for transcript text. Say "cookie" to test the notification.

## Example 2: Memory Creation Trigger Test App (`memory-testapi.py`)

This app receives the full memory object after Omi saves a conversation. It extracts the transcript and optionally uses OpenAI to generate a story.

1.  **Create `memory-testapi.py`:**

    ```python
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi import FastAPI
    import os
    import openai
    import json # For pretty printing

    # --- OpenAI Client Setup ---
    openai_available = False
    try:
        # Reads OPENAI_API_KEY environment variable automatically
        client = openai.OpenAI()
        openai_available = True
        print("OpenAI client initialized successfully.")
    except Exception as e:
        print(f"Warning: Failed to initialize OpenAI client. Story generation disabled. Set OPENAI_API_KEY env var. Error: {e}")
    # -------------------------

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    @app.post('/webhook_memory') # Using a specific path
    def webhook_memory(payload: dict, uid: str):
        print("--- MEMORY ---")
        print("Received Memory Creation Trigger for UID:", uid)

        # Log the full payload for inspection
        print("Full Payload Received:")
        try:
            print(json.dumps(payload, indent=2))
        except Exception as e:
            print(f"(Could not pretty-print payload: {e})", payload)

        extracted_texts = []
        full_transcript = ""
        # Correctly parse the Memory Creation payload
        if 'transcript_segments' in payload and isinstance(payload.get('transcript_segments'), list):
            for segment in payload['transcript_segments']:
                if 'text' in segment and isinstance(segment.get('text'), str):
                    extracted_texts.append(segment['text'])
                else:
                    print(f"Warning: Memory segment missing 'text': {segment}")

            full_transcript = " ".join(extracted_texts)
            print("\nExtracted Full Transcript:", full_transcript)
        else:
            print("Warning: Payload missing 'transcript_segments'.")
            full_transcript = "Transcript could not be extracted."

        # Generate Funny Story using OpenAI
        generated_story = "Story generation skipped or failed."
        if openai_available and full_transcript and full_transcript != "Transcript could not be extracted.":
            try:
                print("\nGenerating funny story with OpenAI...")
                prompt = f"Based on the following transcript, invent a short, funny story (2-4 sentences):\n\nTranscript:\n\"{full_transcript}\"\n\nFunny Story:"
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150, temperature=0.8
                )
                if response.choices and response.choices[0].message:
                     generated_story = response.choices[0].message.content.strip()
                     print("Generated Story:", generated_story)
                else:
                    print("Warning: OpenAI response structure unexpected.")
                    generated_story = "Failed to parse story from OpenAI response."
            except Exception as e:
                print(f"Error calling OpenAI API: {e}")
                generated_story = f"Error generating story: {e}"
        else:
             print("Skipping story generation (OpenAI unavailable or transcript empty).")

        print("--- END MEMORY ---")
        # You can optionally return the story, but Memory Triggers don't usually expect a response body
        return {"message": "Memory payload received.", "generated_story_preview": generated_story[:50] + "..."}

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8000)
    ```

2.  **Set OpenAI API Key (Required for Story Generation):**
    *   In the terminal *before* running the script:
        ```bash
        export OPENAI_API_KEY='your_openai_api_key_here' # macOS/Linux
        # set OPENAI_API_KEY=your_openai_api_key_here # Windows CMD
        # $env:OPENAI_API_KEY = 'your_openai_api_key_here' # Windows PowerShell
        ```

3.  **Running:**
    *   **Terminal 1:** `python memory-testapi.py`
    *   **Terminal 2:** `ngrok http 8000` (Copy the `https://...` Forwarding URL)

4.  **Omi Configuration:**
    *   Create/Edit Omi App -> External Integration
    *   Trigger Type: **`Memory Creation Trigger`**
    *   Webhook URL: `YOUR_NGROK_HTTPS_URL/webhook_memory` (Use the path from the code!)
    *   Install the app.

5.  **Testing:** Have a conversation that Omi saves as a memory, OR use Developer Tools in Omi app -> Open a Memory -> 3-dot menu -> Developer Tools -> Trigger Memory Creation Webhook. Watch Terminal 1 for the full payload, transcript, and generated story.

## General Notes

*   **One App at a Time:** You can only have one URL set per trigger type (Realtime Transcript, Memory Creation, Realtime Audio) in Omi's Developer Settings *or* one URL per trigger type within a specific App's configuration. If running both examples, you might need two separate Omi Apps configured or switch the URL in Developer Settings. Using distinct paths (`/webhook_realtime`, `/webhook_memory`) in the code allows a *single* running server to handle *both*, but Omi needs to be told which endpoint to hit for which trigger.
*   **Ngrok URL Changes:** Free Ngrok URLs are temporary and change each time you restart `ngrok`. Remember to update the Webhook URL in your Omi App settings accordingly.
*   **Production:** This local setup is for development. For a reliable app, deploy your FastAPI code to a cloud server (AWS, GCP, Heroku, etc.).