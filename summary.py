"""The end-of-chat summary for the care team (DI-004).

Target: at least 90% of summaries include every reading, symptom and question in
the transcript. The readings are collected by the same parser the red-flag check
uses, so the numbers in the summary do not depend on the model reading them back
correctly. The model writes the prose around them.
"""
import instructions
import red_flags

SUMMARY_MAX_TOKENS = 400


def readings_in(history):
    """Every glucose reading the patient stated, in the order they said them."""
    found = []
    for message in history:
        if message["role"] == "user":
            found.extend(red_flags.find_readings(message["content"].lower()))
    return found


# Wider than red_flags.SYMPTOMS on purpose. The red-flag list holds only the
# symptoms that fire DI-001. A summary has to carry every symptom the patient
# mentioned, including mild ones (DI-004).
REPORTED_SYMPTOMS = red_flags.SYMPTOMS + [
    "shaky", "shaking", "sweaty", "sweating", "clammy", "hungry", "tired",
    "exhausted", "thirsty", "headache", "blurry", "weak", "numb", "tingling",
    "cramp", "itchy", "sore", "peeing a lot", "urinating a lot", "swollen",
    "rash", "fever", "chills", "cough", "heart racing", "anxious",
]


def symptoms_in(history):
    found = []
    for message in history:
        if message["role"] != "user":
            continue
        text = message["content"].lower()
        for symptom in REPORTED_SYMPTOMS:
            if symptom in text and symptom not in found:
                found.append(symptom)
    return found


def write(ask, history):
    """Return (text, tokens_in, tokens_out). Returns ("", 0, 0) for an empty chat."""
    patient_turns = [m for m in history if m["role"] == "user"]
    if not patient_turns:
        return "", 0, 0

    readings = readings_in(history)
    symptoms = symptoms_in(history)
    checked = (
        "\n\nDetected by the rules, include all of these:\n"
        f"Readings: {', '.join(str(r) for r in readings) or 'none'}\n"
        f"Symptom words: {', '.join(symptoms) or 'none'}"
    )
    text, tin, tout = ask(instructions.SUMMARY + checked, history, SUMMARY_MAX_TOKENS)
    return text or "", tin, tout
