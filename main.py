from flask import Flask, request, jsonify
import openai
import os

# ── Flask app ──────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ── OpenAI client (v1+ SDK) ────────────────────────────────────────────────────
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")  # make sure this is set on Render
)

# ── Slack slash-command endpoint ───────────────────────────────────────────────
@app.route("/slack/events", methods=["POST"])
def slack_events() -> tuple:
    """Handle POST requests coming from Slack slash commands."""
    user_input: str = request.form.get("text", "")
    user_id: str = request.form.get("user_id", "unknown-user")

    # Graceful fallback if the command was sent with no text
    if not user_input.strip():
        return jsonify(
            response_type="ephemeral",
            text="⚠️ I didn’t catch that. Try `/customgpt your question…`",
        ), 200

    # System prompt – tweak to taste
    system_prompt = (
        "You are a helpful assistant trained specifically to answer "
        "Firm360-related queries for internal team members. "
        "Be concise and friendly."
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",                 # change if you prefer a different model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
        )

        reply: str = completion.choices[0].message.content

        return (
            jsonify(
                response_type="in_channel",  # visible to everyone in the channel
                text=reply,
            ),
            200,
        )

    except Exception as exc:
        # Log the exception for Render logs & return an ephemeral error to Slack
        print("OpenAI or server error:", exc, flush=True)
        return (
            jsonify(
                response_type="ephemeral",
                text=f"⚠️ Something went wrong: {exc}",
            ),
            200,
        )


# ── Health-check endpoint (optional) ───────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    """Simple ping endpoint so Render shows a page."""
    return "Slack GPT bot is live 🚀", 200
