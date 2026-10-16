"""Flask routes for the study agent. llm.py owns the Sarvam API client."""

from flask import Flask, jsonify, render_template, request
from agent import StudyAgent

app = Flask(__name__)
agent = StudyAgent()


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/study")
def study():
    data = request.get_json(silent=True) or {}
    try:
        result = agent.study(
            message=data.get("message", ""),
            mode=data.get("mode", "auto"),
            session_id=data.get("session_id"),
        )
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("Study-agent request failed")
        return jsonify({"error": "AI request failed. Check the Flask terminal."}), 502


@app.post("/api/submit-quiz")
def submit_quiz():
    data = request.get_json(silent=True) or {}
    try:
        result = agent.grade_quiz(
            session_id=data.get("session_id"),
            answers=data.get("answers"),
        )
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("Quiz grading failed")
        return jsonify({"error": "Unable to grade the quiz."}), 500


if __name__ == "__main__":
    app.run(debug=True)  # Development only. Disable debug for deployment.
