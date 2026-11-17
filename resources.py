"""The resource list behind DI-006: say when there is no approved answer and
point to the right place.

Deterministic lookup for the navigation questions the DHF names: refills,
supplies, classes, appointments and which line to call. Target: at least 90%
correct referral.

Phone numbers and portal names are placeholders until the clinic confirms them,
the same placeholders the screen designs use.
"""
RESOURCES_VERSION = "2026-11-12.1-draft"

CARE_TEAM = "your care team at [CARE TEAM PHONE]"
PORTAL = "MyChart"

# (name, keywords, reply). Checked in order, so put the specific ones first.
ROUTES = [
    (
        "refills",
        ["refill", "prescription", "pharmacy", "run out of insulin",
         "out of insulin", "ran out of my", "renew my"],
        f"I can't handle refills. For a refill, send a message in {PORTAL} or call "
        f"{CARE_TEAM}. Ask a few days before you run out, because a refill can take "
        "a couple of days.",
    ),
    (
        "supplies",
        ["supplies", "test strip", "strips", "lancet", "sensor", "pump supplies",
         "needles", "pen needle", "meter broke", "new meter"],
        f"I can't order supplies. Call {CARE_TEAM} or send a message in {PORTAL} and "
        "they can tell you how to get more.",
    ),
    (
        "appointments",
        ["appointment", "schedule", "reschedule", "book a visit", "follow-up visit",
         "follow up visit", "see the doctor", "cancel my visit"],
        f"I can't book appointments. To make or change one, call {CARE_TEAM} or use "
        f"{PORTAL}.",
    ),
    (
        "classes",
        ["class", "classes", "diabetes education", "educator", "dsmes",
         "nutritionist", "dietitian", "support group"],
        f"Diabetes education classes and visits with a dietitian are set up by your "
        f"clinic. Call {CARE_TEAM} or ask in {PORTAL} and they can refer you.",
    ),
    (
        "cost",
        ["insurance", "can't afford", "cannot afford", "too expensive", "copay",
         "cost of my", "help paying"],
        f"I can't help with costs or insurance. Call {CARE_TEAM}. They can look at "
        "lower cost options and assistance programs with you.",
    ),
    (
        "who to call",
        ["who do i call", "who should i call", "which line", "what number",
         "how do i reach", "how do i contact", "hotline"],
        f"For diabetes questions after discharge, call {CARE_TEAM}. If it is an "
        f"emergency, call 911. For anything that is not urgent, a message in {PORTAL} "
        "also reaches them.",
    ),
]

FALLBACK = (
    "I don't have an approved answer for that. Please ask {care_team}, or send a "
    "message in {portal}."
).format(care_team=CARE_TEAM, portal=PORTAL)

OFF_TOPIC = (
    "I can only help with questions about diabetes. You could ask me about blood "
    "sugar targets, what to eat, or how to treat a low."
)


def check(message):
    """Return (name, reply) for a navigation question, or (None, None)."""
    text = message.lower()
    for name, keywords, reply in ROUTES:
        if any(k in text for k in keywords):
            return name, reply
    return None, None
