"""v1 terminal prototype (Gemini): answers diabetes questions using only the documents in kb/."""
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# The key and model both come from .env.
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.getenv("MODEL", "gemini-3.8-flash")


def load_kb():
    """Read every .txt file in kb/ and wrap each in a named document tag."""
    docs = []
    for f in sorted(Path("kb").glob("*.txt")):
        docs.append(f'<document name="{f.stem}">\n{f.read_text(encoding="utf-8")}\n</document>')
    if not docs:
        raise SystemExit("No .txt files found in kb/. Run extract.py first.")
    return "\n\n".join(docs)


SYSTEM = f"""You are a support assistant for adults recently discharged from the hospital \
with a new diabetes diagnosis. You help them understand their diabetes between discharge \
and their first clinic follow-up.

Rules:
1. Answer only using the documents below. If they do not cover the question, say you are \
not sure and suggest contacting the care team.
2. Never recommend a medication dose or tell the patient to change one.
3. If the patient's personal action plan from their care team differs from these documents, \
the action plan wins. Remind them to follow it.
4. If the patient describes something that could be serious (very high or very low readings \
with symptoms, confusion, vomiting, trouble breathing), tell them to contact their care team \
now, or call 911 if it is an emergency.
5. If you need more context to answer well (for example, when they last ate or took insulin), \
ask one short question first.
6. Use plain language and short sentences. End each answer by naming the document it came from.

<documents>
{load_kb()}
</documents>
"""

CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM,
    max_output_tokens=600,
)


def main():
    history = []  # list of types.Content, alternating "user" and "model"
    total_in = 0
    total_out = 0

    print(f"Diabetes question helper (prototype). Model: {MODEL}")
    print("Type 'quit' to exit.\n")

    while True:
        user = input("You: ").strip()
        if user.lower() in {"quit", "exit"}:
            break
        if not user:
            continue

        history.append(types.Content(role="user", parts=[types.Part(text=user)]))
        response = client.models.generate_content(
            model=MODEL,
            contents=history,
            config=CONFIG,
        )
        text = response.text or "(no text returned, the reply may have been blocked)"
        history.append(types.Content(role="model", parts=[types.Part(text=text)]))

        usage = response.usage_metadata
        tin = (usage.prompt_token_count or 0) if usage else 0
        tout = (usage.candidates_token_count or 0) if usage else 0
        total_in += tin
        total_out += tout

        print(f"\nBot: {text}\n")
        print(f"[tokens this turn: in {tin}, out {tout}]\n")

    print(f"\nSession total: in {total_in}, out {total_out}")


if __name__ == "__main__":
    main()