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
## 2026-11-06: Route questions to curated topic categories
Decision: Split the knowledge base into topic folders (kb_curated/). A short model call picks one or two categories per question (seeing the last few messages, so follow-ups route correctly), and only those documents plus an always-included "when to get help" page are sent.
Why: Sending the whole knowledge base (~19K tokens) exceeded Groq's free-tier limit (8K tokens/min). Curated categories also keep what the bot can say about each topic reviewable by the team. Chose this over LlamaIndex or embeddings because the corpus is small and the routing stays easy to inspect.
Revisit if: The classifier misroutes often, a single category grows too large, or the corpus grows past what manual curation can handle.
