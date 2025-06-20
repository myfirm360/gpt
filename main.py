from flask import Flask, request, jsonify
import openai
import os
import threading
import requests

# ── Setup ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── Background Thread: Sends GPT response to Slack after initial reply ───────
def process_and_respond(user_input, response_url):
    system_prompt = (
        "You are a helpful assistant trained specifically to answer "
        "Firm360-related queries for internal team members. Be concise and friendly."
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",  # Faster, avoids timeouts
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
        )

        reply = completion.choices[0].message.content

    except Exception as e:
        reply = f"⚠️ Sorry, something went wrong: {e}"

    # Send the response back to Slack via the response_url
    payload = {
        "response_type": "in_channel",
        "text": reply
    }

    try:
        requests.post(response_url, json=payload)
    except Exception as post_err:
        print("Error posting back to Slack:", post_err)

# ── Slack Slash Command Endpoint ──────────────────────────────────────────────
@app.route("/slack/events", methods=["POST"])
def slack_events():
    user_input = request.form.get("text", "")
    response_url = request.form.get("response_url", "")

    if not user_input:
        return jsonify({
            "response_type": "ephemeral",
            "text": "⚠️ I didn’t catch that. Try `/customgpt your question…`"
        }), 200

    # Start background thread
    thread = threading.Thread(target=process_and_respond, args=(user_input, response_url))
    thread.start()

    # Immediate response to avoid timeout
    return jsonify({
        "response_type": "ephemeral",
        "text": "⏳ Thinking… I'll post the answer here shortly!"
    }), 200

# ── Optional health check ─────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return "Slack GPT bot is running ✅", 200
