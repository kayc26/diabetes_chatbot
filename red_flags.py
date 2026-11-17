"""Step 1 of the DHF software specification: the red-flag check (DI-001).

Fixed rules, no model call. If a rule matches, the chatbot does not answer the
question and replies only with EMERGENCY_MESSAGE.

The thresholds and the message wording are DRAFTS pending Dr. Jo Kamimoto's
sign-off. They live here, in their own module, so a clinician can review them
without reading the model instructions.
"""
import re

RULES_VERSION = "2026-11-12.1-draft"

# DI-001 also lists type 1 diabetes. It moved to scope_rule.py, because being
# type 1 is a scope problem rather than an emergency and does not belong in the
# escalation metric. See DECISIONS.md, 2026-11-12.

# DI-001 thresholds, in mg/dL. Read as strict comparisons: a reading exactly at
# a threshold does not fire. The boundary set in DHF 9.1 tests one point below,
# at, and one point above each threshold, so confirm this reading with the
# clinical reviewers.
LOW_SEVERE = 55            # below this
LOW_AFTER_TREATMENT = 70   # below this, after repeated treatment
HIGH_SEVERE = 350          # above this
HIGH_WITH_SYMPTOMS = 250   # above this, with symptoms

# Placeholder wording until sign-off (DHF 7.1).
EMERGENCY_MESSAGE = (
    "This chat is not for urgent concerns. If this is an emergency, call 911. "
    "Otherwise, contact your care team now."
)

# Draft addition, beyond the written DI-001 list. DHF 6.2 leaves open whether an
# unquantified description ("keeps dropping", "I passed out") should count as a
# red flag when no number is given. We fire on the unambiguous ones and flag the
# rule so the reviewers can switch it off. Set to False to follow DI-001 exactly.
SYMPTOM_ONLY_RULE = True

SYMPTOMS = [
    "vomit", "throwing up", "threw up", "nausea", "nauseous",
    "stomach pain", "stomach hurts", "stomach ache", "belly pain",
    "confused", "confusion", "disoriented",
    "trouble breathing", "hard to breathe", "short of breath",
    "breathing fast", "can't breathe", "cannot breathe",
    "blurry vision", "blurred vision", "can't see",
    "passing out", "passed out", "pass out", "fainting", "fainted", "faint",
    "unconscious", "unresponsive", "won't wake", "will not wake",
    "very weak", "can't keep fluids", "cannot keep fluids", "dizzy", "dizziness",
]

# Severe enough to act on with no reading, when SYMPTOM_ONLY_RULE is on.
SEVERE_SYMPTOMS = [
    "passing out", "passed out", "pass out", "fainting", "fainted", "faint",
    "unconscious", "unresponsive", "won't wake", "will not wake",
    "confused", "confusion", "disoriented",
    "trouble breathing", "hard to breathe", "can't breathe", "cannot breathe",
    "can't keep fluids", "cannot keep fluids",
]

KETONES = ["ketone", "ketones"]
PREGNANCY = ["pregnant", "pregnancy", "expecting a baby"]
PUMP = ["pump", "omnipod", "tandem", "t:slim", "medtronic"]
PUMP_FAILURE = [
    "fail", "failed", "failing", "broken", "broke", "not working", "stopped",
    "error", "occlusion", "alarm", "alarming", "no insulin", "came off",
    "fell off", "leaking",
]
REPEAT_TREATMENT = [
    "three times", "3 times", "third time", "twice", "two times",
    "still low", "not coming up", "won't come up", "will not come up",
    "keeps dropping", "keep dropping", "dropping again", "again and again",
]

# Numbers that are plainly not glucose readings.
NOT_GLUCOSE_AFTER = re.compile(
    r"^\s*(?:unit|units|u\b|gram|grams|g\b|hour|hours|hr|hrs|minute|minutes|min|"
    r"mins|year|years|yo\b|pound|pounds|lb|lbs|percent|%|mcg|mg\b(?!\s*/)|ml|"
    r"times|am\b|pm\b|carb|carbs)",
    re.I,
)
GLUCOSE_WORDS = re.compile(
    r"(sugar|glucose|\bbg\b|\bbs\b|cgm|meter|reading|readings|level|levels|"
    r"a1c|mg\s*/?\s*d\s*l)",
    re.I,
)
NUMBER = re.compile(r"\b(\d{2,3})\b")
UNIT_AFTER = re.compile(r"^\s*(?:mg\s*/?\s*d\s*l|mgdl)", re.I)


def find_readings(text):
    """Return the glucose readings stated in the message, in mg/dL.

    A number counts as a reading when it carries a mg/dL unit, or when a glucose
    word appears near it. Numbers followed by another unit (units, grams, hours)
    are skipped, so "15 grams of carbs" and "10 units" are not readings.
    """
    readings = []
    for match in NUMBER.finditer(text):
        value = int(match.group(1))
        if not 10 <= value <= 999:
            continue
        after = text[match.end():match.end() + 12]
        if NOT_GLUCOSE_AFTER.match(after):
            continue
        before = text[max(0, match.start() - 40):match.start()]
        if UNIT_AFTER.match(after) or GLUCOSE_WORDS.search(before) or GLUCOSE_WORDS.search(after):
            readings.append(value)
    return readings


def _any(text, phrases):
    return [p for p in phrases if p in text]


def check(message):
    """Run the red-flag rules over one patient message.

    Returns (fired, reasons, readings). No model call, no network.
    """
    text = message.lower()
    readings = find_readings(text)
    reasons = []

    symptoms = _any(text, SYMPTOMS)
    repeat = _any(text, REPEAT_TREATMENT)

    for value in readings:
        if value < LOW_SEVERE:
            reasons.append(f"glucose {value} below {LOW_SEVERE}")
        elif value < LOW_AFTER_TREATMENT and repeat:
            reasons.append(f"glucose {value} below {LOW_AFTER_TREATMENT} after repeated treatment")
        if value > HIGH_SEVERE:
            reasons.append(f"glucose {value} above {HIGH_SEVERE}")
        elif value > HIGH_WITH_SYMPTOMS and symptoms:
            reasons.append(f"glucose {value} above {HIGH_WITH_SYMPTOMS} with symptoms")

    if _any(text, KETONES):
        reasons.append("ketones mentioned")
    if _any(text, PREGNANCY):
        reasons.append("pregnancy")
    if _any(text, PUMP) and _any(text, PUMP_FAILURE):
        reasons.append("insulin pump failure")

    if SYMPTOM_ONLY_RULE and not reasons:
        severe = _any(text, SEVERE_SYMPTOMS)
        if severe:
            reasons.append(f"severe symptom with no reading: {severe[0]} (draft rule)")

    return bool(reasons), reasons, readings
