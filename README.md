# Omi Integration App - Local Development Setup (FastAPI + Ngrok)

This project demonstrates how to set up a local development environment for creating an Omi Integration App, specifically a **Real-Time Transcript Processor**. It uses a Python FastAPI backend running on your local machine and Ngrok to expose that local server to the internet, allowing Omi's webhooks to reach it.

## Overview

*   **Omi App Type:** External Integration - Real-Time Transcript Processor
*   **Backend:** Python with FastAPI framework
*   **Webhook Tunneling:** Ngrok
*   **Purpose:** Receive real-time transcript segments from the Omi app, process them locally (in this example, just print the extracted text).

## Prerequisites

1.  **Python 3.x:** Make sure Python 3 is installed. Check with `python --version` or `python3 --version`.
2.  **pip:** Python's package installer (usually comes with Python).
3.  **Omi Mobile App:** Installed on your phone/device.
4.  **Ngrok Account:** Sign up for a free account at [ngrok.com](https://ngrok.com/).
5.  **Ngrok Executable:**
    *   **macOS (using Homebrew):** `brew install ngrok`
    *   **Other OS / Manual:** Download from [ngrok.com/download](https://ngrok.com/download) and place the executable somewhere in your PATH or project directory.
6.  **Virtual Environment Tool (Recommended):** `venv` (built into Python 3).
7.  **Basic Terminal/Command Line Knowledge.**

## Setup Steps

1.  **Create Project Directory:**
    ```bash
    mkdir omi-local-dev
    cd omi-local-dev
    ```

2.  **Create Python Virtual Environment:**
    ```bash
    python3 -m venv venv
    # or on Windows: python -m venv venv
    ```

3.  **Activate Virtual Environment:**
    *   **macOS/Linux:** `source venv/bin/activate`
    *   **Windows (Git Bash):** `source venv/Scripts/activate`
    *   **Windows (CMD/PowerShell):** `venv\Scripts\activate`
    (You should see `(venv)` at the beginning of your terminal prompt)

4.  **Install Dependencies:**
    Create a file named `requirements.txt` with the following content:
    ```txt
    fastapi
    uvicorn[standard]
    ```
    Then install them:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Create FastAPI App File:**
    Create a file named `testapi.py` (or your preferred name) with the following Python code:

    ```python
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi import FastAPI

    app = FastAPI()

    # Add CORS middleware (Good practice, though maybe not strictly needed for webhook)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # Allows all origins
        allow_credentials=True,
        allow_methods=["*"], # Allows all methods
        allow_headers=["*"], # Allows all headers
    )

    @app.post('/webhook') # Important: Listens on the /webhook path
    def webhook(payload: dict, uid: str):
        print("--------------------") # Separator for clarity
        print("Received UID:", uid)
        # print("Full Payload:", payload) # Uncomment to see the full raw data

        extracted_texts = []
        # Safely extract text from segments
        if 'segments' in payload and isinstance(payload.get('segments'), list):
            for segment in payload['segments']:
                if 'text' in segment and isinstance(segment.get('text'), str):
                    extracted_texts.append(segment['text'])
                else:
                    print(f"Warning: Segment missing 'text' or not a string: {segment}")
        else:
            # Handle cases where it might be a Memory Creation payload or malformed
            print(f"Warning: Payload might not be Real-Time Transcript format (missing 'segments'): {list(payload.keys())}")


        if extracted_texts:
            # Join text chunks received in *this* specific webhook call
            full_text_from_this_request = " ".join(extracted_texts)
            print("Extracted Text:", full_text_from_this_request)

            # --- YOUR PROCESSING LOGIC GOES HERE ---
            # Example:
            # if "keyword" in full_text_from_this_request.lower():
            #     print("Keyword detected!")
            # ----------------------------------------

        else:
            print("No text extracted in this payload.")

        print("--------------------") # Separator
        # Return success response to Omi
        return {"message": "we got it"}

    if __name__ == "__main__":
        import uvicorn
        # Runs the app locally on host 127.0.0.1 (localhost) and port 8000
        uvicorn.run(app, host="127.0.0.1", port=8000)
    ```

6.  **Configure Ngrok Authtoken:**
    *   Log in to your Ngrok Dashboard ([dashboard.ngrok.com](https://dashboard.ngrok.com/)).
    *   Go to "Your Authtoken" on the left sidebar.
    *   Copy your authtoken.
    *   Run the following command in your terminal, replacing `YOUR_NGROK_TOKEN` with the actual token:
        ```bash
        ngrok config add-authtoken YOUR_NGROK_TOKEN
        ```

## Running the Application

You need two terminals open: one for the FastAPI server, one for Ngrok. Make sure your virtual environment is activated in both (or at least the one running the Python script).

1.  **Terminal 1: Start FastAPI Server:**
    ```bash
    python testapi.py
    ```
    You should see output indicating Uvicorn is running on `http://127.0.0.1:8000`. Keep this terminal running.

2.  **Terminal 2: Start Ngrok Tunnel:**
    ```bash
    ngrok http 8000
    ```
    Ngrok will start and display session information. **Crucially, find the `Forwarding` line that provides an `https://...` URL.** It will look something like `https://<random-string>.ngrok-free.app`. **Copy this HTTPS URL.** Keep this terminal running.

## Omi App Configuration

1.  Open the Omi mobile app.
2.  Navigate to `Explore` -> `Create an App` (or find your existing app to edit).
3.  Fill in the app details (Name, Description, Category, Logo).
4.  Select **Capability:** `External Integration`.
5.  Choose **Trigger Type:** `Real-Time Transcript Processor`.
6.  In the **Webhook URL** field, paste the **full Ngrok HTTPS URL** you copied, **making sure to add `/webhook` to the end**.
    *   **Example:** `https://<random-string>.ngrok-free.app/webhook`
7.  Fill in any other optional fields (Auth URL, Setup Instructions, etc.) if needed, but they aren't required for this basic setup.
8.  `Submit` or `Save` the app configuration.
9.  Make sure the app is **Installed** in your Omi app.

## Testing

1.  Ensure both the `python testapi.py` process and the `ngrok http 8000` process are running in their respective terminals.
2.  Start talking to Omi (ensure the wearable is connected and capturing audio).
3.  Watch the terminal where `python testapi.py` is running. You should see output like:
    ```
    --------------------
    Received UID: <some_user_id>
    Extracted Text: Hello testing one two three.
    --------------------
    ```
4.  You can also watch the Ngrok terminal (`ngrok http 8000`) and see `POST /webhook 200 OK` lines appearing as requests come in successfully.

## Important Notes

*   **Dynamic Ngrok URL:** If you are using a free Ngrok account, the public URL (`https://<random-string>.ngrok-free.app`) **will change every time you stop and restart Ngrok**. You will need to copy the *new* URL and update the "Webhook URL" in your Omi app configuration each time you restart the tunnel.
*   **Development Only:** This setup is **strictly for development and testing**. Your local computer must be on, connected to the internet, and running both the Python script and Ngrok for it to work. It's not suitable for a production app that needs to be available reliably.
*   **Production:** For a production app, you would deploy the FastAPI application to a cloud server (like AWS EC2, Google Cloud Run, Heroku, DigitalOcean App Platform, etc.) which has a stable public IP address or domain name.

## Next Steps

*   Add actual logic inside the `webhook` function in `testapi.py` to process the `full_text_from_this_request`.
*   Store data in a database.
*   Call external APIs based on the transcript content.
*   Implement error handling.