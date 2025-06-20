from flask import Flask, request, jsonify
import openai
import os
import threading
import requests
import time
import re

app = Flask(__name__)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Use your actual Assistant ID here
ASSISTANT_ID = "asst_BKqfAhqCEgH5H1MG2kP5hfEP"


# ── Helper function to remove ChatGPT-style citations ─────────────────────────
def strip_citations(text):
    """Removes source-style markers like  """
    return re.sub(r'【\d+:\d+†.*?†】', '', text)


# ── Background thread to run assistant and post back to Slack ─────────────────
def handle_assistant_interaction(user_input, response_url):
    try:
        # 1. Create a thread
        thread = client.beta.threads.create()

        # 2. Add user's message to the thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # 3. Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )

        # 4. Poll until complete
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "cancelled"]:
                raise Exception(f"Assistant run {run_status.status}")
            time.sleep(1.5)

        # 5. Get the assistant’s response message
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        reply = next(
            (msg.content[0].text.value for msg in messages.data if msg.role == "assistant"),
            "⚠️ No reply from assistant."
        )

        # 6. Clean citations from the response
        cleaned_reply = strip_citations(reply)

    except Exception as e:
        print("Error with Assistant API:", e, flush=True)
        cleaned_reply = f"⚠️ Something went wrong: {e}"

    # 7. Send reply back to Slack
    try:
        requests.post(response_url, json={
            "response_type": "in_channel",
            "text": cleaned_reply
        })
    except Exception as post_err:
        print("Error posting to Slack:", post_err, flush=True)


# ── Slack events endpoint ─────────────────────────────────────────────────────
@app.route("/slack/events", methods=["POST"])
def slack_events():
    user_input = request.form.get("text", "")
    response_url = request.form.get("response_url", "")

    if not user_input:
        return jsonify({
            "response_type": "ephemeral",
            "text": "⚠️ Please include a question. Example: `/customgpt What's our bookkeeping workflow?`"
        }), 200

    thread = threading.Thread(target=handle_assistant_interaction, args=(user_input, response_url))
    thread.start()

    return jsonify({
        "response_type": "ephemeral",
        "text": "⏳ Thinking… I’ll post your answer here shortly!"
    }), 200


# ── Health check endpoint ─────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return "Firm360 Slack Assistant is running ✅", 200
