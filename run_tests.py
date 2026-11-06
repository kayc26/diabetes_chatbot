"""Run every question in test_questions.txt through the bot and save a report to test_results/.

Each question is asked on its own, with no earlier conversation. The report shows the topics
picked and the full answer, so the team can check answers against the sources after any change.
"""
import time
from datetime import datetime
from pathlib import Path

from main import MODEL, PROVIDER, make_ask, respond

RETRIES = 3
RETRY_WAIT_SECONDS = 60  # long enough for Groq's per-minute token limit to reset


def load_tests(path="test_questions.txt"):
    tests = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        expected, _, question = line.partition("|")
        expected = [t.strip() for t in expected.split(",") if t.strip() and t.strip() != "none"]
        tests.append((expected, question.strip()))
    return tests


def ask_with_retry(ask, question):
    for attempt in range(1, RETRIES + 1):
        try:
            return respond(ask, [{"role": "user", "content": question}])
        except Exception as e:
            if attempt == RETRIES:
                raise
            print(f"  {type(e).__name__}, waiting {RETRY_WAIT_SECONDS}s before retrying...")
            time.sleep(RETRY_WAIT_SECONDS)


def main():
    ask = make_ask()
    tests = load_tests()
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    out = Path("test_results") / f"{stamp}-{PROVIDER}.md"
    out.parent.mkdir(exist_ok=True)

    lines = [f"# Test run {stamp}", "", f"Provider: {PROVIDER}, model: {MODEL}", ""]
    passed = 0
    for i, (expected, question) in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] {question}")
        try:
            text, picked, _, _ = ask_with_retry(ask, question)
        except Exception as e:
            text, picked = f"ERROR: {type(e).__name__}: {str(e)[:300]}", []
        ok = all(t in picked for t in expected) if expected else not picked
        passed += ok
        lines += [
            f"## {i}. {question}",
            "",
            f"Routing: {'PASS' if ok else 'FAIL'} (expected: {', '.join(expected) or 'none'}; "
            f"picked: {', '.join(picked) or 'none'})",
            "",
            text,
            "",
        ]

    summary = f"Routing passed {passed}/{len(tests)}"
    lines.insert(4, f"**{summary}**\n")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{summary}. Report: {out}")


if __name__ == "__main__":
    main()
