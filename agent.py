
import json
import re
import secrets

from llm import ask_llm


class StudyAgent:

    def __init__(self):
        # Store temporary user sessions
        self.sessions = {}

    def _get_session(self, session_id):

        if session_id not in self.sessions:
            session_id = secrets.token_urlsafe(24)

            self.sessions[session_id] = {
                "history": [],
                "quiz": None
            }

        return session_id, self.sessions[session_id]

    # Decide what the student wants
    def _choose_mode(self, message, mode):

        if mode in ("explain", "quiz", "notes"):
            return mode

        if mode != "auto":
            raise ValueError("Invalid study mode")

        text = message.lower()

        if re.search(r"\b(quiz|test|mcq)\b", text):
            return "quiz"

        if re.search(r"\b(notes?|summary|revision)\b", text):
            return "notes"

        return "explain"

    # Main study agent function
    def study(self, message, mode="auto", session_id=None):

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Please enter a question")

        message = message.strip()

        if len(message) > 1500:
            raise ValueError("Question is too long")

        session_id, session = self._get_session(session_id)

        mode = self._choose_mode(message, mode)

        # QUIZ MODE
        if mode == "quiz":

            quiz = self._make_quiz(message)

            # Keep correct answers on the backend
            session["quiz"] = quiz

            public_questions = []

            for i, q in enumerate(quiz["questions"]):
                public_questions.append({
                    "id": i,
                    "question": q["question"],
                    "options": q["options"]
                })

            return {
                "session_id": session_id,
                "mode": "quiz",
                "quiz": {
                    "title": quiz["title"],
                    "questions": public_questions
                }
            }

        # EXPLAIN MODE
        if mode == "explain":

            instructions = """
            You are a helpful AI Study Tutor.

            Explain concepts in simple language.
            Teach step by step.
            Provide practical examples.
            Include formulas when necessary.
            End with one practice question.
            """

        # NOTES MODE
        else:

            instructions = """
            You create accurate revision notes.

            Organize your response into:
            1. Key Idea
            2. Important Points
            3. Formulas
            4. Worked Example
            5. Quick Revision
            """

        history = session["history"][-6:]

        answer = ask_llm(
            message,
            system_prompt=instructions,
            history=history
        )

        session["history"] = (
            history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": answer[:4000]}
            ]
        )[-8:]

        return {
            "session_id": session_id,
            "mode": mode,
            "reply": answer
        }

    # Generate structured MCQ test
    def _make_quiz(self, topic):

        question_schema = {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "answer_index": {"type": "integer"},
                "explanation": {"type": "string"}
            },
            "required": [
                "question",
                "options",
                "answer_index",
                "explanation"
            ],
            "additionalProperties": False
        }

        quiz_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "study_quiz",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "questions": {
                            "type": "array",
                            "items": question_schema
                        }
                    },
                    "required": ["title", "questions"],
                    "additionalProperties": False
                }
            }
        }

        instructions = """
        You are an expert quiz generator.

        Create accurate multiple-choice questions.

        Return exactly one JSON object containing
        five questions.

        Every question must have:
        - A question
        - Four options
        - One correct answer
        - An explanation
        """

        prompt = f"""
        Create exactly 5 MCQs about: {topic}

        Each question must have 4 options.

        answer_index must be an integer:
        0, 1, 2, or 3.

        Ensure each question has exactly one
        correct option.

        Check answers for accuracy.
        """

        raw = ask_llm(
            prompt,
            system_prompt=instructions,
            response_format=quiz_format,
            max_tokens=3500
        )

        # Convert JSON string to Python dictionary

        try:
            quiz = json.loads(raw)
        
        except (json.JSONDecodeError, TypeError) as e:
            print("\n===== SARVAM RAW RESPONSE =====")
            print(repr(raw[:2000]))
            print("===============================")
            print("JSON ERROR:", str(e))
        
            raise RuntimeError(
                "AI returned invalid quiz JSON"
            ) from e

        # Validate quiz structure
        if not isinstance(quiz, dict):
            raise RuntimeError("Invalid quiz structure")

        questions = quiz.get("questions")

        if not isinstance(questions, list):
            raise RuntimeError("Missing quiz questions")

        if len(questions) != 5:
            raise RuntimeError("AI did not generate 5 questions")

        for q in questions:

            if not isinstance(q, dict):
                raise RuntimeError("Invalid question")

            options = q.get("options")
            index = q.get("answer_index")

            if not isinstance(q.get("question"), str) or not q["question"].strip():
                raise RuntimeError("Invalid question text")

            if (
                not isinstance(options, list)
                or len(options) != 4
                or not all(
                    isinstance(option, str) and option.strip()
                    for option in options
                )
            ):
                raise RuntimeError("Invalid question options")

            if type(index) is not int or index not in range(4):
                raise RuntimeError("Invalid correct answer index")

            if (
                not isinstance(q.get("explanation"), str)
                or not q["explanation"].strip()
            ):
                raise RuntimeError("Missing answer explanation")

        return {
            "title": str(quiz.get("title", "Practice Quiz")),
            "questions": questions
        }

    # Evaluate student answers
    def grade_quiz(self, session_id, answers):

        if session_id not in self.sessions:
            raise ValueError("Session expired")

        session = self.sessions[session_id]

        quiz = session.get("quiz")

        if quiz is None:
            raise ValueError("No active quiz")

        questions = quiz["questions"]

        if not isinstance(answers, list) or len(answers) != len(questions):
            raise ValueError("Please answer all questions")

        if any(
            type(answer) is not int or answer not in range(4)
            for answer in answers
        ):
            raise ValueError("Invalid answer selection")

        score = 0
        results = []

        for i, question in enumerate(questions):

            selected = answers[i]
            correct = question["answer_index"]

            is_correct = selected == correct

            if is_correct:
                score += 1

            results.append({
                "question": i + 1,
                "correct": is_correct,
                "correct_answer": question["options"][correct],
                "explanation": question["explanation"]
            })

        # Quiz completed
        session["quiz"] = None

        return {
            "score": score,
            "total": len(questions),
            "results": results
        }
