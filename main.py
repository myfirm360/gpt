from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.form
    user_input = data.get("text")
    response_url = data.get("response_url")

    # Customize your system prompt here
    system_prompt = "You are a helpful assistant trained specifically to answer Firm360-related queries."

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    reply = completion.choices[0].message['content']

    return jsonify({
        "response_type": "in_channel",
        "text": reply
    })
