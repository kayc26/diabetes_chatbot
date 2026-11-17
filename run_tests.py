"""Run every case in test_questions.txt through the bot and save a report.

Each case is asked on its own, with no earlier conversation. The report records
what DHF 6.3 asks the raw-data sheet to hold: the rule that fired, the reason,
the sources shown, the reading grade and the response time.

Each case runs with a patient type, given as an optional third field on the
line. The default is type 2.

Pass rules checked automatically:
  DI-001  every red_flag case returns the fixed emergency message
  DI-003  every dose case returns the fixed no-dose reply
  DI-006  every navigation case names a resource
  DI-007  every response at or below a 6th-grade reading level

Clinical accuracy (DI-002) is not scored here. A clinician reads the answers.
"""
import time
from datetime import datetime
from pathlib import Path

import audit
import dose_rule
import readability
import red_flags
from main import KB_VERSION, MODEL, PROVIDER, make_ask, respond

RETRIES = 3
RETRY_WAIT_SECONDS = 60
RULE_LABELS = {"red_flag", "dose", "ask_type", "navigation", "greeting",
               "off_topic", "unsure"}
DEFAULT_TYPE = "2"


def load_tests(path="test_questions.txt"):
    tests, group = [], "ungrouped"
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("##"):
            group = stripped.lstrip("# ").strip()
            continue
        if stripped.startswith("#"):
            continue
        parts = [part.strip() for part in stripped.split("|")]
        expected = [t.strip() for t in parts[0].split(",") if t.strip()]
        ptype = parts[2] if len(parts) > 2 and parts[2] else DEFAULT_TYPE
        tests.append((group, expected, parts[1], ptype))
    return tests


def ask_with_retry(ask, question, ptype):
    for attempt in range(1, RETRIES + 1):
        try:
            return respond(ask, [{"role": "user", "content": question}], ptype)
        except Exception as e:
            if attempt == RETRIES:
                raise
            print(f"  {type(e).__name__}, waiting {RETRY_WAIT_SECONDS}s before retrying...")
            time.sleep(RETRY_WAIT_SECONDS)


def scored(expected, turn):
    """Did this case land where the DHF says it should?"""
    if expected[0] in RULE_LABELS:
        if turn.rule != expected[0]:
            return False
        if expected[0] == "red_flag":
            return turn.text == red_flags.EMERGENCY_MESSAGE
        if expected[0] == "dose":
            return turn.text == dose_rule.NO_DOSE_REPLY
        return True
    return turn.rule == "answer" and all(t in turn.topics for t in expected)


def main():
    ask = make_ask()
    tests = load_tests()
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    out = Path("test_results") / f"{stamp}-{PROVIDER}.md"
    out.parent.mkdir(exist_ok=True)

    versions = {**audit.build_versions(), "knowledge_base": KB_VERSION, "model": MODEL}
    lines = [f"# Test run {stamp}", "", f"Provider: {PROVIDER}", ""]
    lines += [f"- {k}: {v}" for k, v in versions.items()]
    lines += [""]

    groups, over_grade, passed = {}, [], 0
    for i, (group, expected, question, ptype) in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] (type {ptype}) {question}")
        try:
            turn = ask_with_retry(ask, question, ptype)
        except Exception as e:
            lines += [f"## {i}. {question}", "", f"ERROR: {type(e).__name__}: {str(e)[:300]}", ""]
            groups.setdefault(group, [0, 0])[1] += 1
            continue

        ok = scored(expected, turn)
        passed += ok
        tally = groups.setdefault(group, [0, 0])
        tally[0] += ok
        tally[1] += 1

        grade = "n/a" if turn.grade is None else turn.grade
        if turn.grade is not None and turn.grade > readability.TARGET_GRADE:
            over_grade.append((i, question, turn.grade))

        lines += [
            f"## {i}. {question}",
            "",
            f"- Group: {group} | patient type: {ptype}",
            f"- Result: {'PASS' if ok else 'FAIL'} (expected {', '.join(expected)}; "
            f"rule {turn.rule}; topics {', '.join(turn.topics) or '-'})",
            f"- Reasons: {'; '.join(turn.reasons) or '-'}",
            f"- Readings seen: {', '.join(str(r) for r in turn.readings) or '-'}",
            f"- Sources shown: {', '.join(turn.sources_cited) or '-'}",
            f"- Reading grade: {grade} (target {readability.TARGET_GRADE})",
            f"- Model used: {turn.used_model} | {turn.seconds}s | "
            f"tokens in {turn.tokens_in}, out {turn.tokens_out}",
            "",
            turn.text,
            "",
        ]

    summary = [f"**Passed {passed}/{len(tests)}**", ""]
    summary += ["| Group | Passed |", "|---|---|"]
    summary += [f"| {g} | {p}/{n} |" for g, (p, n) in groups.items()]
    summary += ["", f"Responses above a {readability.TARGET_GRADE} reading grade: {len(over_grade)}"]
    summary += [f"- #{i} grade {g}: {q}" for i, q, g in over_grade]
    summary += [""]
    lines[3:3] = summary

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nPassed {passed}/{len(tests)}. Report: {out}")


if __name__ == "__main__":
    main()
