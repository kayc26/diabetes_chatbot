"""Which type of diabetes the patient has, asked once per chat.

Both type 1 and type 2 are in scope (team decision, 2026-11-12), and the
knowledge base holds documents for both. Almost every safety topic reads
differently by type: how much fast-acting carb treats a low on an AID system,
whether ketone checking applies, whether metformin or GLP-1 is relevant at all.
So the answer step cannot load documents until it knows which patient it is
talking to.

The chatbot asks once, on the first question that needs documents, and keeps the
answer for the rest of the chat. It also picks the type up for free if the
patient states it themselves.

In the deployed product MyChart would supply this and no one would be asked.
Collecting it in the chat is the proof-of-concept stand-in, and it is one of the
five fields DI-005's guided check-in collects anyway.
"""
import re

TYPE_VERSION = "2026-11-12.1-draft"

QUESTION = (
    "Before I answer, may I check one thing? Were you told you have type 1 or "
    "type 2 diabetes? If you are not sure, your care team can tell you."
)

REPROMPT = (
    "Sorry, I did not catch that. Please answer with 1 or 2. If you are not sure "
    "which type you have, your care team can tell you."
)

_T1 = r"type\s*-?\s*(?:1|one)\b"
_T2 = r"type\s*-?\s*(?:2|two)\b"

# Said about themselves, not about the topic or about someone else.
SELF_STATED = {
    "1": [
        rf"\bi\s+(?:have|got)\b[^.?!]{{0,15}}{_T1}",
        rf"\bi\s*'?\s*a?m\s+(?:a\s+)?{_T1}",
        rf"\bi\s*'?\s*a?m\b[^.?!]{{0,12}}{_T1}",
        rf"\bdiagnosed\s+with\b[^.?!]{{0,12}}{_T1}",
        rf"\bmy\s+{_T1}",
        r"\bi\s+(?:have|got)\b[^.?!]{0,15}\bt1d\b",
        r"\bi\s*'?\s*a?m\s+(?:a\s+)?t1d\b",
    ],
    "2": [
        rf"\bi\s+(?:have|got)\b[^.?!]{{0,15}}{_T2}",
        rf"\bi\s*'?\s*a?m\s+(?:a\s+)?{_T2}",
        rf"\bi\s*'?\s*a?m\b[^.?!]{{0,12}}{_T2}",
        rf"\bdiagnosed\s+with\b[^.?!]{{0,12}}{_T2}",
        rf"\bmy\s+{_T2}",
        r"\bi\s+(?:have|got)\b[^.?!]{0,15}\bt2d\b",
        r"\bi\s*'?\s*a?m\s+(?:a\s+)?t2d\b",
    ],
}

# A bare reply to the question above.
BARE = {
    "1": [r"^\s*(?:type\s*-?\s*)?(?:1|one|i)\s*\.?\s*$", r"^\s*t1d?\s*\.?\s*$"],
    "2": [r"^\s*(?:type\s*-?\s*)?(?:2|two|ii)\s*\.?\s*$", r"^\s*t2d?\s*\.?\s*$"],
}

# The message is about someone else, or about the topic rather than the patient.
NOT_THE_PATIENT = [
    "question", "difference", "friend", "mom", "mother", "dad", "father",
    "sister", "brother", "son", "daughter", "wife", "husband", "partner",
    "coworker", "neighbor", "handout", "guide", "article", "pamphlet",
]

_SELF = {k: [re.compile(p, re.I) for p in v] for k, v in SELF_STATED.items()}
_BARE = {k: [re.compile(p, re.I) for p in v] for k, v in BARE.items()}


def detect(message):
    """Return "1", "2" or None. No model call.

    A bare "2" counts, because it is an answer to QUESTION. A self-statement
    counts anywhere. Asking *about* a type does not: "what is the difference
    between type 1 and type 2?" returns None.
    """
    text = message.lower().strip()
    for kind, patterns in _BARE.items():
        if any(p.match(text) for p in patterns):
            return kind
    if any(word in text for word in NOT_THE_PATIENT):
        return None
    found = {k for k, patterns in _SELF.items() if any(p.search(text) for p in patterns)}
    return found.pop() if len(found) == 1 else None


def label(kind):
    return {"1": "type 1", "2": "type 2"}.get(kind, "unknown")
