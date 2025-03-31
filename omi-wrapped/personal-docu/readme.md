run ngrok https 8080 or whatever uvicorn's port is in main.py then paste that in omi app

https://aistudio.google.com/prompts/15aZzCpMc7jUS60GQdR7GGM2rs3ggZDd3

# Firestore Setup
firestore: https://console.cloud.google.com/firestore/databases/-default-/data/panel/raw_memories/ckVQW3MVAoenlOdYhHLt5K3zPpW2_2025-03-31?authuser=1&invt=AbthxQ&project=omi-mentor-hackathon
woo
![alt text](image.png)

# Cloud Functions - WOOOO
https://console.cloud.google.com/functions/details/us-west2/daily-reflection-processor?project=omi-mentor-hackathon
todo:
multiple user support for
```
IMPORTANT: Find the line user_id = request.args.get("uid", os.environ.get("TARGET_USER_ID", "YOUR_DEFAULT_TEST_USER_ID")) near the start of the daily_process_memories function. Replace "YOUR_DEFAULT_TEST_USER_ID" with your actual Omi User ID (e.g., ckVQW3MVAoenlOdYhHLt5K3zPpW2) for testing purposes. Later, you could remove this default and rely only on environment variables or request parameters if supporting multiple users.
```

(venv) ➜  omi-wrapped git:(feat-DailyProcessing) ✗ cd '/Users/cvk/Downloads/[CODE] Local Projects/omi-hackathon_25MNRV/omi
-wrapped/daily-reflection-processor'
(venv) ➜  daily-reflection-processor git:(feat-DailyProcessing) ✗ functions-framework --target daily_process_memories --port 8081 --debug
2025-03-31 15:12:17,414 - INFO - Starting application
2025-03-31 15:12:18,262 - INFO - OpenAI client initialized.
2025-03-31 15:12:18,262 - INFO - Firestore and OpenAI clients initialized successfully.
 * Serving Flask app 'daily_process_memories'
 * Debug mode: on
2025-03-31 15:12:18,286 - INFO - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8081
 * Running on http://192.168.4.79:8081
2025-03-31 15:12:18,286 - INFO - Press CTRL+C to quit
2025-03-31 15:12:18,291 - INFO -  * Restarting with watchdog (fsevents)
2025-03-31 15:12:18,585 - INFO - Starting application
2025-03-31 15:12:19,189 - INFO - OpenAI client initialized.
2025-03-31 15:12:19,189 - INFO - Firestore and OpenAI clients initialized successfully.
2025-03-31 15:12:19,201 - WARNING -  * Debugger is active!
2025-03-31 15:12:19,208 - INFO -  * Debugger PIN: 281-279-233
2025-03-31 15:12:23,457 - INFO - Daily processing function triggered.
2025-03-31 15:12:23,457 - WARNING - Using default test user ID. Set TARGET_USER_ID env var or pass 'uid' query param.
2025-03-31 15:12:23,457 - INFO - Processing reflections for User ID: ckVQW3MVAoenlOdYhHLt5K3zPpW2, Date: 2025-03-31
2025-03-31 15:12:24,005 - INFO - Found 4 memories. Aggregated transcript length: 8687
2025-03-31 15:12:24,005 - INFO - Processing transcript (8687 chars) with OpenAI...
2025-03-31 15:12:29,026 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-31 15:12:29,032 - INFO - OpenAI Raw Response: {
    "daily_emoji": "🍜",
    "summary": "A day filled with social interactions, food exploration, and casual conversations. The day involved trying new dishes, discussing work-related topics, and sharing personal experiences.",
    "gratitude_points": ["Appreciation for friends trying new food recommendations together.", "Acknowledgment of caring gestures and support received throughout the day."],
    "learned_terms": [
        {"term": "Firestore", "definition": "Google's cloud-hosted NoSQL database that stores data in documents and collections."},
        {"term": "Podcast mode", "definition": "Listening to content in an audio format similar to a podcast."},
        {"term": "Capstone project", "definition": "A final project that integrates the skills and knowledge acquired during a course or program."},
        {"term": "Site reliability", "definition": "Ensuring that a website or service is consistently available and performs well for users."}
    ],
    "little_things": [
        {"mention": "Preference for rice at every meal", "suggested_action": "Explore diversifying meal options to include more variety."},
        {"mention": "Enjoyment of spicy food", "suggested_action": "Experiment with different spice levels and flavors in cooking."},
        {"mention": "Desire for coffee after a food coma", "suggested_action": "Consider having coffee as a post-meal pick-me-up for energy."}
    ],
    "mentor_advice": "Balance your meal choices to include a variety of nutrients and flavors for a more well-rounded diet. Remember to take breaks and enjoy the process of trying new things, both in food and in work.",
    "action_items": ["Follow up on the pending offer letter status.", "Consider participating in multiple credit courses to maximize learning opportunities."]
}
2025-03-31 15:12:29,032 - INFO - OpenAI processing successful.
2025-03-31 15:12:29,111 - INFO - Successfully saved processed reflection to Firestore doc: ckVQW3MVAoenlOdYhHLt5K3zPpW2_2025-03-31
2025-03-31 15:12:29,111 - INFO - Daily processing completed successfully.
2025-03-31 15:12:29,112 - INFO - 127.0.0.1 - - [31/Mar/2025 15:12:29] "GET / HTTP/1.1" 200 -

# Cloud SCheduler