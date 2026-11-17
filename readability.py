"""Reading-level measurement for DI-007: every response at or below 6th grade.

Flesch-Kincaid grade level, computed here rather than asserted in the prompt, so
every response carries a measured grade into the audit log and the test report.
No third-party dependency, so the number is reproducible with the build.
"""
import re

TARGET_GRADE = 6.0

_SENTENCE = re.compile(r"[.!?\n]+")
_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_VOWELS = "aeiouy"


def count_syllables(word):
    word = word.lower().strip("'’-")
    if not word:
        return 0
    count, previous_was_vowel = 0, False
    for char in word:
        is_vowel = char in _VOWELS
        if is_vowel and not previous_was_vowel:
            count += 1
        previous_was_vowel = is_vowel
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(count, 1)


def grade(text):
    """Flesch-Kincaid grade level. Returns None for text with no words.

    Non-Latin scripts have no syllable rule here, so they return None rather
    than a misleading number.
    """
    sentences = [s for s in _SENTENCE.split(text) if s.strip()]
    words = _WORD.findall(text)
    if not words or not sentences:
        return None
    if len(words) < 0.4 * len(re.findall(r"\S+", text)):
        return None
    syllables = sum(count_syllables(w) for w in words)
    score = (
        0.39 * (len(words) / len(sentences))
        + 11.8 * (syllables / len(words))
        - 15.59
    )
    return round(score, 1)
