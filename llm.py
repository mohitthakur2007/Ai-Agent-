
import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

API_KEY = os.getenv("SARVAM_API_KEY")

if not API_KEY:
    raise ValueError("SARVAM_API_KEY not found in .env")

client = SarvamAI(api_subscription_key=API_KEY)

MODEL = "sarvam-105b"

SYSTEM_PROMPT = """
You are a helpful AI Study Assistant.
Explain concepts clearly, provide examples,
and help students learn step by step.
"""


def ask_llm(
    prompt,
    system_prompt=SYSTEM_PROMPT,
    history=None,
    response_format=None,
    max_tokens=3500
):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    if history:
        messages.extend(history)

    messages.append({
        "role": "user",
        "content": prompt
    })

    options = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens
    }

    # Optional structured JSON output
    if response_format is not None:
        options["response_format"] = response_format

    response = client.chat.completions(**options)

    choice = response.choices[0]
    answer = choice.message.content

    if not answer or not answer.strip():
        raise RuntimeError(
            f"Empty LLM response. Finish reason: {choice.finish_reason}"
        )

    return answer
