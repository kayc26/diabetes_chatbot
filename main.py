"""v1 terminal prototype: answers diabetes questions using only the curated documents in kb_curated/.

Each question is first sorted into one or two topic categories, and only those categories'
documents (plus kb_curated/always/) are sent to the model.

Set PROVIDER in .env to "gemini" (default) or "groq".
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("PROVIDER", "gemini").lower()
DEFAULT_MODELS = {"gemini": "gemini-3.8-flash", "groq": "openai/gpt-oss-120b"}
if PROVIDER not in DEFAULT_MODELS:
    raise SystemExit(f"Unknown PROVIDER '{PROVIDER}'. Use 'gemini' or 'groq'.")

# Each provider reads its own key and model from .env (e.g. GROQ_API_KEY, GROQ_MODEL).
MODEL = os.getenv(f"{PROVIDER.upper()}_MODEL", DEFAULT_MODELS[PROVIDER])
ANSWER_MAX_TOKENS = 600
CLASSIFIER_MAX_TOKENS = 200
MAX_CATEGORIES = 2
# Messages sent with each request. Odd, so the window always starts with a patient message.
ANSWER_HISTORY = 7
CLASSIFIER_HISTORY = 5

KB_DIR = Path("kb_curated")

# Folder name in kb_curated/ -> description the classifier uses to pick it.
CATEGORIES = {
    "basics": "what diabetes is, how insulin and glucose work, what a new diagnosis means",
    "low_blood_sugar": "hypoglycemia, low readings, shaky/sweaty/dizzy, confusion, fainting or "
                       "passing out, the 15-15 rule, glucagon",
    "high_blood_sugar": "hyperglycemia, high readings, thirst, frequent urination, blurry vision, "
                        "nausea or vomiting, ketones, DKA",
    "monitoring": "checking blood glucose, meters, CGMs, target range, time in range, patterns",
    "insulin_devices": "types of insulin, pens, pumps, AID systems (general information, not doses)",
    "food": "meals, carbs, the diabetes plate, portions, snacks, hunger, protein, eating on a budget, "
            "what to eat or drink, protein shakes, supplements",
    "sweeteners_and_liver": "sugar substitutes, artificial sweeteners, eating for liver health",
    "activity": "exercise, physical activity, staying safe while active",
    "daily_life": "sick days, stress, sleep, work, school, travel, insulin storage",
    "support": "emotional wellbeing, burnout, the healthcare team, diabetes education, finding information",
}

RULES = """You are a support assistant for adults recently discharged from the hospital \
with a new diabetes diagnosis. You help them understand their diabetes between discharge \
and their first clinic follow-up.

Rules:
1. Answer only using the documents below. Every fact, example, food, and number in your answer \
must appear in them. Do not add examples from your own knowledge, even common ones. If the \
documents name a general group (such as "fruits") without listing specific items, give what they \
say about the group and do not list items yourself. If the \
documents do not cover the question, say you are not sure and suggest contacting the care team.
2. Never recommend a medication dose or tell the patient to change one.
3. If the patient's personal action plan from their care team differs from these documents, \
the action plan wins. Remind them to follow it.
4. If the patient describes something that could be serious (very high or very low readings \
with symptoms, confusion, vomiting, trouble breathing), tell them to contact their care team \
now, or call 911 if it is an emergency.
5. If you need more context to answer well (for example, when they last ate or took insulin), \
ask one short question first.
6. Answer the specific question asked, directly, in the first sentence. Only bring in a general \
method (such as the Diabetes Plate) if the patient asks how to build a meal or the question cannot \
be answered without it.
7. If a "Team FAQs" document answers the question, base your answer on that FAQ answer, keep \
its facts and numbers, and add from the other documents only what the FAQ leaves out.
8. Use plain language and short sentences. End each answer by naming the document or documents \
you actually used, exactly as written in their name attribute. Skip this for greetings or small talk."""

CLASSIFIER_SYSTEM = f"""Sort the patient's latest message into topic categories for a diabetes \
help chatbot. Use the earlier messages to understand follow-up questions such as "what about at night?".

Categories:
{chr(10).join(f"- {name}: {desc}" for name, desc in CATEGORIES.items())}

Reply with only the category names, comma-separated, most relevant first, at most {MAX_CATEGORIES}. \
Usually one category is enough. Add a second only if the latest message clearly asks about two topics. \
Pick categories for the latest message, not for topics that came up earlier. \
If the patient describes feeling unwell (fainting, confusion, dizziness, weakness) without a \
reading that makes clear whether they are low or high, reply "low_blood_sugar, high_blood_sugar". \
Reply "none" if no category fits."""


def load_category(name):
    """Return every document in kb_curated/<name>/, each wrapped in a named document tag."""
    docs = []
    for f in sorted((KB_DIR / name).glob("*.txt")):
        source, _, body = f.read_text(encoding="utf-8").partition("\n\n")
        source = source.removeprefix("Source: ").strip()
        docs.append(f'<document name="{source}">\n{body}</document>')
    return docs


def load_kb():
    missing = [c for c in ["always", *CATEGORIES] if not (KB_DIR / c).is_dir()]
    if missing:
        raise SystemExit(f"Missing folders in {KB_DIR}/: {', '.join(missing)}")
    return {c: load_category(c) for c in ["always", *CATEGORIES]}


KB = load_kb()


def build_system(categories):
    docs = KB["always"] + [d for c in categories for d in KB[c]]
    return f"{RULES}\n\n<documents>\n" + "\n\n".join(docs) + "\n</documents>\n"


def make_gemini():
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def ask(system, history, max_tokens):
        # Gemini calls the assistant role "model".
        contents = [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part(text=m["content"])],
            )
            for m in history
        ]
        config = types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens)
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)
        usage = response.usage_metadata
        tin = (usage.prompt_token_count or 0) if usage else 0
        tout = (usage.candidates_token_count or 0) if usage else 0
        return response.text or "", tin, tout

    return ask


def make_groq():
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def ask(system, history, max_tokens):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system}] + history,
            max_tokens=max_tokens,
            # Keeps gpt-oss from spending the small token budget on hidden reasoning.
            reasoning_effort="low",
        )
        usage = response.usage
        tin = usage.prompt_tokens if usage else 0
        tout = usage.completion_tokens if usage else 0
        return response.choices[0].message.content or "", tin, tout

    return ask


def classify(ask, history):
    """Return up to MAX_CATEGORIES category names for the latest message, plus token counts."""
    reply, tin, tout = ask(CLASSIFIER_SYSTEM, history[-CLASSIFIER_HISTORY:], CLASSIFIER_MAX_TOKENS)
    words = [w.strip(" .\"'`*-").lower() for w in reply.replace("\n", ",").split(",")]
    picked = [w for w in words if w in CATEGORIES]
    return list(dict.fromkeys(picked))[:MAX_CATEGORIES], tin, tout


def respond(ask, history):
    """Answer the latest message in history. Returns (text, categories, tokens_in, tokens_out)."""
    categories, cin, cout = classify(ask, history)
    text, tin, tout = ask(build_system(categories), history[-ANSWER_HISTORY:], ANSWER_MAX_TOKENS)
    text = text or "(no text returned, the reply may have been blocked)"
    return text, categories, cin + tin, cout + tout


def make_ask():
    return make_gemini() if PROVIDER == "gemini" else make_groq()


def main():
    ask = make_ask()
    history = []  # list of {"role": "user" | "assistant", "content": str}
    total_in = 0
    total_out = 0

    print(f"Diabetes question helper (prototype). Provider: {PROVIDER}, model: {MODEL}")
    print("Type 'quit' to exit.\n")

    while True:
        user = input("You: ").strip()
        if user.lower() in {"quit", "exit"}:
            break
        if not user:
            continue

        history.append({"role": "user", "content": user})
        try:
            text, categories, tin, tout = respond(ask, history)
        except Exception as e:
            history.pop()  # keep history alternating so the patient can simply ask again
            print(f"\n[The service had a problem: {type(e).__name__}. Please try again in a minute.]")
            print(f"[details: {str(e)[:300]}]\n")
            continue

        history.append({"role": "assistant", "content": text})

        total_in += tin
        total_out += tout

        print(f"\nBot: {text}\n")
        print(f"[topics: {', '.join(categories) or 'none'} | tokens this turn: in {tin}, out {tout}]\n")

    print(f"\nSession total: in {total_in}, out {total_out}")


if __name__ == "__main__":
    main()
