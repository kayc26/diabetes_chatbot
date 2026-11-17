"""Per-turn audit log.

Every step records its intermediate state, not just its output: the rule that
fired, the topics loaded, the sources shown, the reading grade and the response
time. Those are the columns the raw-data sheet in DHF 6.3 expects, so a scored
run can be rebuilt from the log.
"""
import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs")


def build_versions():
    import dose_rule
    import instructions
    import red_flags
    import resources
    import patient_type

    return {
        "red_flag_rules": red_flags.RULES_VERSION,
        "dose_rule": dose_rule.RULES_VERSION,
        "instructions": instructions.INSTRUCTIONS_VERSION,
        "patient_type": patient_type.TYPE_VERSION,
        "resources": resources.RESOURCES_VERSION,
    }


def log_turn(record, log_dir=LOG_DIR):
    """Append one turn to logs/turns-YYYY-MM-DD.jsonl."""
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)
    row = {"time": datetime.now().isoformat(timespec="seconds"), **record}
    path = log_dir / f"turns-{datetime.now():%Y-%m-%d}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path
