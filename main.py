from flask import Flask, request, jsonify
import openai
import os
import threading
import requests
import time

app = Flask(__name__)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Your Assistant ID from OpenAI
ASSISTANT_ID = "asst_BKqfAhqCEgH5H1MG2kP5hfEP"

# ── Threaded processing to handle Slack & Assistant delay ─────────────────────
def handle_assistant_interaction(user_input, response_url):
    try:
        # Step 1: Create a thread
        thread = client.beta.threads.create()

        # Step 2: Add user's message to thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # Step 3: Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )

        # Step 4: Wait for completion
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "cancelled"]:
                raise Exception(f"Assistant run {run_status.status}")
            time.sleep(1.5)  # Polling delay

        # Step 5: Get the assistant’s reply
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        reply = next(
            (msg.content[0].text.value for msg in messages.data if msg.role == "assistant"),
            "⚠️ No reply from assistant."
        )

    except Exception as e:
        print("Error with Assistant API:", e)
        reply = f"⚠️ Something went wrong: {e}"

    # Step 6: Send response back to Slack
    requests.post(response_url, json={
        "response_type": "in_channel",
        "text": reply
    })


# ── Slack webhook endpoint ─────────────────────────────────────────────────────
@app.route("/slack/events", methods=["POST"])
def slack_events():
    user_input = request.form.get("text", "")
    response_url = request.form.get("response_url", "")

    if not user_input:
        return jsonify({
            "response_type": "ephemeral",
            "text": "⚠️ Please include a prompt. Try `/customgpt your question...`"
        }), 200

    # Run assistant response in a background thread
    thread = threading.Thread(target=handle_assistant_interaction, args=(user_input, response_url))
    thread.start()

    # Respond to Slack immediately to avoid timeout
    return jsonify({
        "response_type": "ephemeral",
        "text": "⏳ Thinking... I'll post the answer shortly!"
    }), 200


# ── Health check endpoint ──────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return "Slack Assistant is live!", 200
