# Decision Log

## 2026-11-06: Knowledge base from a few trusted sources
Decision: Use 4 to 5 ADA patient handouts, converted to text, loaded whole into the prompt.
Why: Small enough to fit in context; avoids building a review pipeline for v1.
Revisit if: Corpus grows beyond what fits, or we need per-answer citations.

## 2026-11-06: No clinical context collection in v1
Decision: Skip structured extraction and storage of patient context.
Why: Not needed to demonstrate the core flow.
Revisit if: We test the nurse-handoff spec (≥80% sufficient without follow-up).

## 2026-11-06: Terminal interface for v1
Decision: Command-line prototype in Python.
Why: Logic matters more than UI at this stage.
Revisit if: We need usability data from older adults (Patient 3 spec).