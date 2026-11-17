# Decision Log

## 2026-11-06: Knowledge base from a few trusted sources
Decision: Use 4 to 5 ADA patient handouts, converted to text, loaded whole into the prompt.
Why: Small enough to fit in context; avoids building a review pipeline for v1.
Revisit if: Corpus grows beyond what fits, or we need per-answer citations.
Status: The "loaded whole" part is replaced by topic routing (see "Route questions to curated topic categories").

## 2026-11-06: No clinical context collection in v1
Decision: Skip structured extraction and storage of patient context.
Why: Not needed to demonstrate the core flow.
Revisit if: We test the nurse-handoff spec (≥80% sufficient without follow-up).

## 2026-11-06: Terminal interface for v1
Decision: Command-line prototype in Python.
Why: Logic matters more than UI at this stage.
Revisit if: We need usability data from older adults (Patient 3 spec).

## 2026-11-06: Support both Gemini and Groq, switchable in .env
Decision: Move off the Anthropic API to free tiers. Keep Gemini and add Groq (openai/gpt-oss-120b), chosen with `PROVIDER` in `.env`. Groq is the current default because Gemini kept returning 503 "high demand" errors.
Why: Free tiers keep the prototype at no cost. A second provider means one outage does not stop testing.
Revisit if: Either free tier changes, or rate limits block testing with real users.

## 2026-11-06: Do not use DeepSeek's own API
Decision: Not adding DeepSeek's hosted API as a provider.
Why: It runs on servers in China. Patients will type health details (readings, symptoms, medications), which may not be allowed to go there. The cost and limits were not the problem.
Revisit if: We use DeepSeek models through a host outside China (e.g. OpenRouter), after checking that host's data terms.

## 2026-11-06: Route questions to curated topic categories
Decision: Split the knowledge base into topic folders (kb_curated/). A short model call picks one or two categories per question (seeing the last few messages, so follow-ups route correctly), and only those documents plus an always-included "when to get help" page are sent.
Why: Sending the whole knowledge base (~19K tokens) exceeded Groq's free-tier limit (8K tokens/min). Curated categories also keep what the bot can say about each topic reviewable by the team. Chose this over LlamaIndex or embeddings because the corpus is small and the routing stays easy to inspect.
Revisit if: The classifier misroutes often, a single category grows too large, or the corpus grows past what manual curation can handle.

## 2026-11-06: Send only recent messages with each request
Decision: The answer sees the last 7 messages; the topic classifier sees the last 5.
Why: Keeps follow-up questions working while stopping long chats from growing past the rate limit.
Revisit if: Patients refer back to things said earlier than that and the bot loses track.

## 2026-11-06: Unclear symptoms load both low and high blood sugar
Decision: If a patient describes feeling unwell (fainting, confusion, dizziness, weakness) without a reading that shows whether they are low or high, the classifier picks both topics.
Why: "I'm fainting" was routed to high blood sugar only, though fainting is mainly a sign of a severe low. Loading both means the bot has the right safety information either way.
Revisit if: The test set shows this causes wrong answers for clear-cut questions.

## 2026-11-06: Strict grounding in the documents
Decision: Every fact, example, food, and number must appear in the documents. If a document names only a group (e.g. "fruits"), the bot does not list examples of its own. It answers the question asked first and brings in the Diabetes Plate only when the question is about building a meal. It cites only the documents it actually used.
Why: The bot was adding fruits that appear in none of our sources, citing the wrong document, and steering almost every food answer back to the plate.
Revisit if: Answers become too thin to be useful. The better fix then is adding content, not loosening the rule.

## 2026-11-06: Team FAQs take priority over handouts
Decision: Add the team's FAQ answers (Google Doc "FAQs") as `team-faqs.txt` in the matching topic folders. When an FAQ covers a question, the bot builds its answer on it and keeps its facts and numbers.
Why: The FAQs answer common questions the handouts do not (e.g. carbs per meal, which fruits) and keep answers consistent.
Revisit if: We want approved answers sent word for word, with no rewording (needs clinical sign-off).

## 2026-11-06: Different replies for off-topic and uncovered questions
Decision: Questions unrelated to diabetes or health get a short "I can only help with diabetes questions" and example questions. Health questions the documents do not cover get "I'm not sure, check with your care team."
Why: The bot was telling people to ask their care team about the weather.

## 2026-11-06: Fixed test set, re-run after every change
Decision: Keep `test_questions.txt` (the FAQ questions plus urgent-symptom and off-topic checks, each with expected topics). `run_tests.py` checks the routing automatically and saves every answer to `test_results/` for a person to read.
Why: The grounding rules are instructions, not a guarantee, so answers need checking whenever prompts or documents change.

## 2026-11-12: Rebuild around the DHF's three fixed steps
Decision: Follow DHF 7.1 (DRS Rev 1.2). Every message passes a deterministic red-flag check (DI-001) and a deterministic dose check (DI-003) before any model call. Only a message that passes both reaches the knowledge-base answer step (DI-002, DI-006, DI-007). A chat ends with a summary (DI-004). `architecture.md` was rewritten to use the DHF's requirement IDs and component names.
Why: v1 runs the topic classifier first, so both safety behaviours live inside model calls as prompt rules 3 and 5. The DHF ordered the steps the other way so that safety does not depend on the model behaving well, which was Angela Ha's concern about AI-drafted replies in Epic. A prompt rule shares a context window and a sample with the answer that breaks it.
Revisit if: the red-flag rules over-fire on plainly worded routine questions. The fix is the test set capping DI-001, not loosening the rules.
Status: not implemented yet. The topic router stays as the retrieval mechanism for step 3; it has no DHF requirement behind it.

## 2026-11-12: Type 1 material is out of scope
Decision: Treat type 1 diabetes as out of scope and as a red flag, per Design Plan 4.1 and DI-001. The knowledge base moves to Penn Survival Skills, the Diabetes Action Plan, the insulin dose worksheet and the educator FAQs.
Why: the DHF scopes the device to adults on a new or changed insulin regimen and excludes pediatric patients and type 1. `kb_curated/` is almost entirely derived from an ADA type 1 guide, and an off-topic reply already cited it.
Revisit if: the clinical sponsor widens the population back to both types.

## 2026-11-12: Knowledge base rebuilt from the type 2 guide
Decision: Curate the ADA guide for people with type 2 diabetes into the existing ten folders, and move the type 1 derived files to `kb_superseded/`. `activity/exercise_and_nutrition.txt` moved too, because the type 2 guide's physical activity section covers all of it and is more specific. (Reversed later the same day: it came back tagged `Type: both` once type 1 was back in scope, because the type 1 guide's activity section states only the 150 minutes and has no resistance, flexibility or balance guidance.) The ADA one-pagers and the three `team-faqs.txt` files stay: they are not type-specific and they carry content neither guide has, such as the example food lists the grounding rule depends on.
Why: the type 1 guide was the source for every safety topic, including the always-loaded page, while Design Plan 4.1 puts type 1 out of scope and DI-001 now returns the emergency message to anyone who mentions it. Answering from an out-of-scope source was the larger problem, and kb/ already had the type 2 text.
Revisit if: the clinical sponsor widens the population back to both types, in which case the superseded files come back under type-labelled names.
Status: `always/` is thinner than the type 1 version it replaced. The type 2 guide has no equivalent of the type 1 guide's full "when to seek immediate help" list or its "keep these handy" list. Step 1 (DI-001) now owns escalation, so the page carries less weight than it did, but the gap should be filled from a Penn source.

## 2026-11-12: Type 1 is out of scope, not an emergency
Decision: Move type 1 diabetes out of the red-flag rule into its own scope check (`scope_rule.py`), with its own fixed reply pointing to the care team and its own log label, `out_of_scope`. It runs after the red-flag check, so a type 1 patient who is also in danger still gets the emergency message. Only a self-stated diagnosis fires: "what is the difference between type 1 and type 2?" and "my mother has type 1" are answered normally.
Why: DI-001 lists type 1 alongside DKA and severe hypoglycemia. Being type 1 is a scope problem, not a clinical emergency. Treating it as one told those patients to call 911, which is wrong on its face and trains people to discount the emergency message. It also put a scope condition inside the metric that reports at least 98% of urgent scenarios escalated with no more than 15% of routine inquiries over-escalated, so every "what is the difference" question inflated the over-escalation figure against a case that was never urgent.
Revisit if: Dr. Jo Kamimoto wants type 1 kept inside DI-001, or wants the scope reply worded differently.
Status: a departure from DRS Rev 1.2 as written. Needs clinical sign-off, and DHF-013-DC should record it. The real fix is to collect diabetes type once as a patient attribute rather than detect it per message, which belongs with the guided check-in (DI-005).

## 2026-11-12: Both types of diabetes are in scope
Decision: The chatbot serves patients with type 1 and with type 2 (team decision). Supersedes the two entries below from earlier today. The scope check is gone, type 1 is out of the DI-001 red-flag list, and `kb_curated/` holds documents for both types, each file tagged with a `Type:` header of 1, 2 or both. Before the first answer that needs documents, the chatbot asks which type the patient has and keeps it for the chat; it also picks it up when the patient states it unprompted. Only that patient's documents are loaded, plus the type-agnostic one-pagers and team FAQs.
Why: Section 7.1 intended use is written around adults on a new or changed insulin regimen and never says type 2. Insulin is the defining treatment for type 1, so excluding those patients looked like a corpus limitation rather than a population decision. Serving both without knowing the type is not an option: the type 2 guide has one line on glucagon where the type 1 guide has a page, nothing on hypoglycemia unawareness, nothing on AID users taking 5 to 10 grams instead of 15, and it frames treatment around metformin, GLP-1 and SGLT2, none of which apply to type 1.
Revisit if: the clinical sponsor wants the population narrowed again, or wants the red-flag thresholds to differ by type (they are currently the same for both).
Status: widens Design Plan 4.1 and changes DI-001. Needs ratifying at the 11/20 review and a DHF-013-DC entry. Asking in the chat is a stand-in for the type coming from MyChart, and it is one of DI-005's five check-in fields.

## Open questions
- Emergency answers: should the bot give the guide's "while you wait" steps (check glucose, 15 g fast-acting carbs if able to swallow, glucagon given by someone else), or only tell the patient to call 911 or the care team? Needs a clinical decision.
- Two FAQ answers mention insulin timing ("10-15 minutes before eating"; "correction insulin if you have not taken insulin in the last 4 hours"). Confirm who wrote or approved them, since the bot otherwise avoids medication instructions.
- The knowledge base is ADA material standing in for the Penn documents the DHF names (Survival Skills, the Diabetes Action Plan, the insulin dose worksheet). Those are still [to request].
- `always/` now has a page per type, so the type 1 call-911 list is back for type 1 patients. The type 2 page is still thinner; find a type 2 or Penn equivalent.
- Red-flag thresholds are the same for both types. Confirm that is right with the clinical reviewers.
