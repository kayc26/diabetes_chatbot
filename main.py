"""v1 terminal prototype: answers diabetes questions using only the documents in kb/."""
import os
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

# Model comes from .env (MODEL=...), with a fallback if it is not set.
MODEL = os.getenv("MODEL", "claude-haiku-5-5")


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


def main():
    history = []
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

        history.append({"role": "user", "content": user})
        reply = client.messages.create(
            model=MODEL,
            max_tokens=600,
            system=SYSTEM,
            messages=history,
        )
        text = reply.content[0].text
        history.append({"role": "assistant", "content": text})

        total_in += reply.usage.input_tokens
        total_out += reply.usage.output_tokens

        print(f"\nBot: {text}\n")
        print(f"[tokens this turn: in {reply.usage.input_tokens}, out {reply.usage.output_tokens}]\n")

    print(f"\nSession total: in {total_in}, out {total_out}")


if __name__ == "__main__":
    main()