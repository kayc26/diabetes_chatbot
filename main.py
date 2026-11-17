"""Terminal prototype of the post-discharge diabetes chatbot.

Implements the three steps of DHF 7.1 in order, then the end-of-chat summary:

  [1] red-flag check (DI-001)  fixed rules, no model
  [2] dose check (DI-003)      fixed rules, no model
  [3] answer from the knowledge base (DI-002, DI-006, DI-007)
  [4] summary for the care team (DI-004)

Both type 1 and type 2 are in scope. Before the first answer that needs
documents, the chatbot asks which type the patient has and keeps it for the rest
of the chat, so only that patient's documents are loaded (patient_type.py).

Steps 1 and 2 run before any model call, so a recognised red flag or dose
request never reaches the model. See architecture.md.

Set PROVIDER in .env to "gemini" (default) or "groq". If Groq hits a rate limit
and GEMINI_API_KEY is set, the rest of the session falls back to Gemini.
"""
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

import audit
import dose_rule
import instructions
import readability
import red_flags
import patient_type
import resources
import summary as summary_module

load_dotenv()

PROVIDER = os.getenv("PROVIDER", "gemini").lower()
DEFAULT_MODELS = {"gemini": "gemini-3.8-flash", "groq": "openai/gpt-oss-120b"}
if PROVIDER not in DEFAULT_MODELS:
    raise SystemExit(f"Unknown PROVIDER '{PROVIDER}'. Use 'gemini' or 'groq'.")


def model_for(provider):
    return os.getenv(f"{provider.upper()}_MODEL", DEFAULT_MODELS[provider])


MODEL = model_for(PROVIDER)
ANSWER_MAX_TOKENS = 600
CLASSIFIER_MAX_TOKENS = 200
GEMINI_RETRY_WAITS = [2, 5, 10, None]
MAX_CATEGORIES = 2
ANSWER_HISTORY = 7
CLASSIFIER_HISTORY = 5

KB_DIR = Path("kb_curated")
KB_VERSION = "kb_curated@2026-11-12"

# Folder name in kb_curated/ -> description the classifier uses to pick it.
CATEGORIES = {
    "basics": "what diabetes is, how insulin and glucose work, what a new diagnosis means",
    "low_blood_sugar": "hypoglycemia, low readings, shaky/sweaty/dizzy, the 15-15 rule, glucagon",
    "high_blood_sugar": "hyperglycemia, high readings, thirst, frequent urination, blurry vision, ketones",
    "monitoring": "checking blood glucose, meters, CGMs, target range, time in range, patterns",
    "insulin_devices": "types of insulin, pens, pumps, AID systems (general information, not doses)",
    "food": "meals, carbs, the diabetes plate, portions, snacks, hunger, protein, eating on a budget, "
            "what to eat or drink, protein shakes, supplements",
    "sweeteners_and_liver": "sugar substitutes, artificial sweeteners, eating for liver health",
    "activity": "exercise, physical activity, staying safe while active",
    "daily_life": "sick days, stress, sleep, work, school, travel, insulin storage",
    "support": "emotional wellbeing, burnout, the healthcare team, diabetes education",
}
SPECIAL_LABELS = ["navigation", "greeting", "off_topic", "unsure"]

CLASSIFIER_SYSTEM = instructions.CLASSIFIER.format(
    categories="\n".join(f"- {name}: {desc}" for name, desc in CATEGORIES.items()),
    max_categories=MAX_CATEGORIES,
)


@dataclass
class Turn:
    """One patient message and everything the steps produced for it."""
    text: str = ""
    rule: str = ""            # red_flag | dose | ask_type | navigation | greeting | off_topic | unsure | answer
    patient_type: str = None
    reasons: list = field(default_factory=list)
    readings: list = field(default_factory=list)
    topics: list = field(default_factory=list)
    documents: list = field(default_factory=list)
    sources_cited: list = field(default_factory=list)
    grade: float = None
    used_model: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    seconds: float = 0.0


def load_category(name):
    """Return [(document name, type, body)] for kb_curated/<name>/.

    Each file opens with a `Source:` line and a `Type:` line. Type is "1", "2"
    or "both", and decides which patients the document is loaded for.
    """
    docs = []
    for f in sorted((KB_DIR / name).glob("*.txt")):
        head, _, body = f.read_text(encoding="utf-8").partition("\n\n")
        fields = {
            k.strip(): v.strip()
            for k, sep, v in (line.partition(":") for line in head.splitlines()) if sep
        }
        kind = fields.get("Type", "both")
        if kind not in {"1", "2", "both"}:
            raise SystemExit(f"{f}: Type must be 1, 2 or both, not {kind!r}")
        docs.append((fields.get("Source", f.stem), kind, body))
    return docs


def load_kb():
    missing = [c for c in ["always", *CATEGORIES] if not (KB_DIR / c).is_dir()]
    if missing:
        raise SystemExit(f"Missing folders in {KB_DIR}/: {', '.join(missing)}")
    return {c: load_category(c) for c in ["always", *CATEGORIES]}


KB = load_kb()


def documents_for(categories, ptype):
    """The documents in these folders that apply to this patient."""
    picked = []
    for category in ["always", *categories]:
        picked.extend(
            (name, body) for name, kind, body in KB[category] if kind in ("both", ptype)
        )
    return picked


def build_system(docs, ptype):
    tags = "\n\n".join(f'<document name="{name}">\n{body}</document>' for name, body in docs)
    note = (
        f"The patient has {patient_type.label(ptype)} diabetes. The documents below "
        "are the ones that apply to them, so answer for that type without hedging "
        "about the other one."
    )
    return f"{instructions.ANSWER}\n\n{note}\n\n<documents>\n{tags}\n</documents>\n"


def make_gemini(model):
    from google import genai
    from google.genai import errors, types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def ask(system, history, max_tokens):
        contents = [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part(text=m["content"])],
            )
            for m in history
        ]
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        )
        for wait in GEMINI_RETRY_WAITS:
            try:
                response = client.models.generate_content(model=model, contents=contents, config=config)
                break
            except errors.ServerError:
                if wait is None:
                    raise
                print(f"[Gemini is busy; retrying in {wait}s...]")
                time.sleep(wait)
        usage = response.usage_metadata
        tin = (usage.prompt_token_count or 0) if usage else 0
        tout = (usage.candidates_token_count or 0) if usage else 0
        return response.text or "", tin, tout

    return ask


def make_groq(model):
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def ask(system, history, max_tokens):
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}] + history,
            max_tokens=max_tokens,
            reasoning_effort="low",
        )
        usage = response.usage
        tin = usage.prompt_tokens if usage else 0
        tout = usage.completion_tokens if usage else 0
        return response.choices[0].message.content or "", tin, tout

    return ask


def classify(ask, history):
    """Return (labels, tokens_in, tokens_out) for the latest message."""
    reply, tin, tout = ask(CLASSIFIER_SYSTEM, history[-CLASSIFIER_HISTORY:], CLASSIFIER_MAX_TOKENS)
    words = [w.strip(" .\"'`*-").lower() for w in reply.replace("\n", ",").split(",")]
    for label in SPECIAL_LABELS:
        if label in words:
            return [label], tin, tout
    picked = [w for w in words if w in CATEGORIES]
    return list(dict.fromkeys(picked))[:MAX_CATEGORIES] or ["unsure"], tin, tout


def respond(ask, history, ptype=None):
    """Run the three steps over the latest message in history. Returns a Turn."""
    started = time.monotonic()
    message = history[-1]["content"]
    turn = Turn()

    # [1] Red-flag check (DI-001). No model call.
    fired, reasons, readings = red_flags.check(message)
    turn.readings = readings
    if fired:
        turn.text, turn.rule, turn.reasons = red_flags.EMERGENCY_MESSAGE, "red_flag", reasons
        return _finish(turn, started)

    # [2] Dose check (DI-003). No model call.
    fired, hits = dose_rule.check(message)
    if fired:
        turn.text, turn.rule, turn.reasons = dose_rule.NO_DOSE_REPLY, "dose", hits
        return _finish(turn, started)

    # [3] Answer from the knowledge base (DI-002, DI-006, DI-007).
    labels, tin, tout = classify(ask, history)
    turn.tokens_in, turn.tokens_out, turn.used_model = tin, tout, True

    if labels[0] in SPECIAL_LABELS:
        turn.rule = labels[0]
        if turn.rule in ("navigation", "unsure"):
            name, reply = resources.check(message)
            if reply:
                turn.reasons = [f"resource: {name}"]
                turn.text = reply
                return _finish(turn, started)
            if turn.rule == "navigation":
                turn.text = resources.FALLBACK
                return _finish(turn, started)
        text, tin2, tout2 = ask(instructions.NO_DOCUMENTS, history[-ANSWER_HISTORY:], ANSWER_MAX_TOKENS)
        turn.tokens_in += tin2
        turn.tokens_out += tout2
        turn.text = text or resources.FALLBACK
        return _finish(turn, started)

    # The answer step needs documents, and which documents depends on the
    # patient's type, so ask before loading anything.
    if ptype is None:
        turn.rule, turn.text = "ask_type", patient_type.QUESTION
        return _finish(turn, started)

    turn.rule, turn.topics, turn.patient_type = "answer", labels, ptype
    docs = documents_for(labels, ptype)
    turn.documents = [name for name, _ in docs]
    text, tin2, tout2 = ask(build_system(docs, ptype), history[-ANSWER_HISTORY:], ANSWER_MAX_TOKENS)
    turn.tokens_in += tin2
    turn.tokens_out += tout2
    turn.text = text or "(no text returned, the reply may have been blocked)"
    turn.sources_cited = [name for name in turn.documents if name in turn.text]
    return _finish(turn, started)


def _finish(turn, started):
    turn.grade = readability.grade(turn.text)
    turn.seconds = round(time.monotonic() - started, 2)
    return turn


def make_ask():
    if PROVIDER == "gemini":
        return make_gemini(MODEL)
    groq_ask = make_groq(MODEL)
    if not os.getenv("GEMINI_API_KEY"):
        return groq_ask
    return with_fallback(groq_ask)


def with_fallback(groq_ask):
    """Use Groq until it rate-limits, then switch to Gemini for the session."""
    from groq import RateLimitError

    state = {"ask": groq_ask}

    def ask(system, history, max_tokens):
        try:
            return state["ask"](system, history, max_tokens)
        except RateLimitError:
            gemini_model = model_for("gemini")
            print(f"[Groq rate limit reached; switching to gemini ({gemini_model}) for this session.]")
            state["ask"] = make_gemini(gemini_model)
            return state["ask"](system, history, max_tokens)

    return ask


def main():
    ask = make_ask()
    history = []
    ptype = None
    awaiting_type = False
    versions = {**audit.build_versions(), "knowledge_base": KB_VERSION, "model": MODEL}
    total_in = total_out = 0

    print(f"Diabetes question helper (prototype). Provider: {PROVIDER}, model: {MODEL}")
    print("Build: " + ", ".join(f"{k} {v}" for k, v in versions.items()))
    print("Type 'quit' to exit.\n")

    while True:
        user = input("You: ").strip()
        if user.lower() in {"quit", "exit"}:
            break
        if not user:
            continue

        history.append({"role": "user", "content": user})

        # Pick the patient's type up whenever they state it, and when it answers
        # our own question, drop the exchange and answer what they first asked.
        detected = patient_type.detect(user)
        if detected and ptype is None:
            ptype = detected
            if awaiting_type and len(history) >= 3:
                history.pop()   # their answer
                history.pop()   # the question we asked

        try:
            turn = respond(ask, history, ptype)
        except Exception as e:
            history.pop()
            print(f"\n[The service had a problem: {type(e).__name__}. Please try again in a minute.]")
            print(f"[details: {str(e)[:300]}]\n")
            continue

        awaiting_type = turn.rule == "ask_type"
        history.append({"role": "assistant", "content": turn.text})
        total_in += turn.tokens_in
        total_out += turn.tokens_out

        audit.log_turn({
            "versions": versions, "message": user, "rule": turn.rule,
            "patient_type": turn.patient_type,
            "reasons": turn.reasons, "readings": turn.readings, "topics": turn.topics,
            "documents_loaded": turn.documents, "sources_cited": turn.sources_cited,
            "reading_grade": turn.grade, "used_model": turn.used_model,
            "seconds": turn.seconds, "tokens_in": turn.tokens_in,
            "tokens_out": turn.tokens_out, "reply": turn.text,
        })

        grade = "n/a" if turn.grade is None else turn.grade
        flag = "" if turn.grade is None or turn.grade <= readability.TARGET_GRADE else "  <-- above 6th grade"
        print(f"\nBot: {turn.text}\n")
        print(f"[rule: {turn.rule} | {patient_type.label(ptype)} | "
              f"topics: {', '.join(turn.topics) or '-'} | "
              f"grade: {grade}{flag} | {turn.seconds}s | tokens in {turn.tokens_in}, out {turn.tokens_out}]\n")

    text, tin, tout = summary_module.write(ask, history)
    if text:
        total_in += tin
        total_out += tout
        print("\n--- Summary for the care team (DI-004) ---")
        print(text)
        audit.log_turn({"versions": versions, "rule": "summary", "reply": text,
                        "tokens_in": tin, "tokens_out": tout})

    print(f"\nSession total: in {total_in}, out {total_out}")


if __name__ == "__main__":
    main()
