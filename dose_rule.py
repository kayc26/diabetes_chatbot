"""Step 2 of the DHF software specification: the dose check (DI-003).

Fixed rule, no model call. Any request about a medication dose gets one
pre-written refusal that directs the patient to the care team.

Target: 0 dose recommendations across all scenarios, including the ten that
push for one.

Open item (DHF 6.2): the screen designs add a general line about insulin timing
after the refusal, while the browser test page returns only this fixed text. One
version has to be frozen before the bench test. This file holds the stricter
version, with no timing line.
"""
RULES_VERSION = "2026-11-12.1-draft"

NO_DOSE_REPLY = (
    "I can't tell you how much insulin or medicine to take. Your care team sets "
    "your dose. Please check your insulin plan or the label on your prescription. "
    "If you are not sure, call your care team or send a message in MyChart."
)

DOSE_PHRASES = [
    "how much insulin", "how much medicine", "how much medication",
    "how many units", "how much should i take", "how much do i take",
    "how much to take", "what dose", "what's my dose", "whats my dose",
    "correct dose", "correction dose", "right dose", "dose should i",
    "increase my dose", "decrease my dose", "lower my dose", "raise my dose",
    "increase my insulin", "decrease my insulin", "lower my insulin",
    "raise my insulin", "more insulin", "less insulin", "extra insulin",
    "extra units", "more units", "fewer units", "adjust my dose",
    "adjust my insulin", "change my dose", "change my insulin",
    "double my dose", "double my insulin", "skip my dose", "skip my insulin",
    "skip a dose", "take more", "take less", "up my dose", "cut my dose",
    "should i take another", "take another dose", "sliding scale",
]


def check(message):
    """Return (fired, reasons) for one patient message. No model call."""
    text = message.lower()
    hits = [p for p in DOSE_PHRASES if p in text]
    return bool(hits), hits
