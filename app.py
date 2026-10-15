
from sarvamai import SarvamAI
from flask import Flask, render_template, request
from dotenv import load_dotenv
import os

# Load API key
load_dotenv()

ApiKey = os.getenv("SARVAM_API_KEY")

# Initialize Sarvam client
client = SarvamAI(api_subscription_key=ApiKey)

# Initialize Flask
app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/ask')
def ask():
    question = request.args.get("question", "").strip()

    if not question:
        return "Please enter a question.", 400

    try:
        response = client.chat.completions(
            model="sarvam-105b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful AI study tutor. "
                        "Explain concepts clearly with examples."
                    )
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
        )

        answer = response.choices[0].message.content

        return answer or "No response generated."

    except Exception as e:
        print("Sarvam API Error:", str(e))
        return "Something went wrong. Check terminal.", 500


if __name__ == "__main__":
    app.run(debug=True)
