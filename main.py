from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/slack/events", methods=["POST"])
def slack_events():
    # Slack sends data as x-www-form-urlencoded by default
    user_input = request.form.get("text", "")
    user_id = request.form.get("user_id", "unknown user")

    # Safety check in case input is missing
    if not user_input:
        return jsonify({
            "response_type": "ephemeral",
            "text": "Sorry, I didn’t catch that. Try `/customgpt [your question]`."
        })

    system_prompt = "You are a helpful assistant trained specifically to answer Firm360-related queries."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )

        reply = response.choices[0].message['content']

        return jsonify({
            "response_type": "in_channel",
            "text": reply
        })

    except Exception as e:
        return jsonify({
            "response_type": "ephemeral",
            "text": f"⚠️ Something went wrong: {str(e)}"
        })
