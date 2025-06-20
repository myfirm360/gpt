from flask import Flask, request, jsonify
import openai
import os
import threading
import requests
import time
import re

app = Flask(__name__)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ASSISTANT_ID = "asst_BKqfAhqCEgH5H1MG2kP5hfEP"

# ── Helper: clean citations + markdown for Slack ──────────────────────────────
def clean_for_slack(text: str) -> str:
    """
    • Remove ChatGPT/Assistants citations like  ,  , etc.
    • Convert **double-star** bold to *single-star* (Slack's mrkdwn).
    """
    text = re.sub(r"【[^】]+】", "", text)          # strip any 【…】 block
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)  # **bold** → *bold*
    return text.strip()

# ── Background worker ----------------------------------------------------------------
def handle_assistant_interaction(user_input: str, response_url: str):
    try:
        # 1  Create thread
        thread = client.beta.threads.create()

        # 2  User message
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input,
        )

        # 3  Run assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )

        # 4  Wait until done
        while True:
            status = client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            if status.status == "completed":
                break
            if status.status in {"failed", "cancelled"}:
                raise RuntimeError(f"Assistant run {status.status}")
            time.sleep(1.3)

        # 5  Fetch assistant response
        msgs = client.beta.threads.messages.list(thread_id=thread.id)
        raw_reply = next(
            (
                m.content[0].text.value
                for m in msgs.data
                if m.role == "assistant"
            ),
            "⚠️ No assistant reply.",
        )

        cleaned_reply = clean_for_slack(raw_reply)

    except Exception as exc:
        print("Assistant error:", exc, flush=True)
        cleaned_reply = f"⚠️ Something went wrong: {exc}"

    # 6  Post back to Slack
    try:
        requests.post(
            response_url,
            json={
                "response_type": "in_channel",
                "text": cleaned_reply,
                "mrkdwn": True,  # ensure Slack parses markdown
            },
            timeout=5,
        )
    except Exception as post_err:
        print("Slack post error:", post_err, flush=True)

# ── Slash-command endpoint ------------------------------------------------------------
@app.route("/slack/events", methods=["POST"])
def slack_events():
    user_input = request.form.get("text", "").strip()
    response_url = request.form.get("response_url", "")

    if not user_input:
        return jsonify(
            response_type="ephemeral",
            text="⚠️ Try `/customgpt your question …`",
        ), 200

    threading.Thread(
        target=handle_assistant_interaction, args=(user_input, response_url)
    ).start()

    return jsonify(
        response_type="ephemeral",
        text="⏳ Got it – I’ll post the answer here shortly!",
    ), 200

# ── Health check --------------------------------------------------
