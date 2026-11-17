# Post-Discharge Diabetes Chatbot: Architecture

**Status:** rewritten 2026-11-12 against the DHF (DHF-002-UNS / DHF-006-DRS / DHF-007-TM Rev 1.2, 2026-11-11; DHF-010-DO Rev 1.1, Section 7.1). Requirement IDs and component names in this document are the DHF's. Where this document and the DHF disagree, the DHF wins and this document is wrong.

**Scope:** adults, and their caregivers, in the first 30 days after discharge on a new or changed insulin regimen, **with either type 1 or type 2 diabetes** (team decision, 2026-11-12). This widens Design Plan 4.1, which put type 1 out of scope, and drops type 1 from the DI-001 red-flag list. Needs ratifying at the 11/20 review and a DHF-013-DC entry. Pediatric patients remain out of scope.

**Data:** invented test data only (DI-009). No real patient information goes into any build.

---

## 1. Shape of the system

Three steps in a fixed order, then a summary. The first two steps are deterministic rules that run before the model. If either fires, the model is not called at all and the patient sees fixed text.

```
patient message
      |
      v
[1] red-flag check (DI-001)     -- match --> fixed emergency message, AI not used
      |  fixed rules, no model
      v
[2] dose check (DI-003)         -- match --> fixed no-dose reply
      |  fixed rules, no model
      v
  patient type known?           -- no ----> ask once, then answer what they asked
      |
      v
[3] answer from the knowledge base (DI-002, DI-006, DI-007)
      |     retrieve passages -> model writes from those passages only
      |     no approved answer --> fallback reply naming the right resource
      v
  answer with its source, at or below 6th-grade reading level
      |
      v
[4] summary of the chat for the care team (DI-004)
```

The ordering is the design, not an implementation detail. Safety must not depend on the model behaving well (DHF 6.2; Angela Ha's concern about AI-drafted replies in Epic). A prompt rule against dose advice shares a context window and a sample with the answer that violates it, so when the model talks itself into a suggestion the rule has already lost. A rule in front of the model has not.

A red flag beats everything else. If a message mixes a dose question or a routine question with a red flag, the emergency message wins (DHF 6.3).

---

## 2. Step specifications

### [1] Red-flag check (DI-001, UN-001)

Fixed rules, no model. Reads glucose values typed in mg/dL, symptoms and key phrases.

Draft thresholds, pending Dr. Jo Kamimoto's sign-off: below 55; below 70 after three treatments; above 350; above 250 with symptoms; ketones; pump failure; pregnancy. DI-001 also lists type 1 diabetes; that is gone, because both types are now in scope.

Open: the thresholds are the same for both types. Whether a type 1 patient needs different ones is a question for the clinical reviewers.

On a match the chatbot does not answer the question and replies only with the fixed emergency message:

> This chat is not for urgent concerns. If this is an emergency, call 911. Otherwise, contact your care team now.

The wording is a placeholder until sign-off. Target: 100% of red-flag test scenarios.

Thresholds live in their own criteria file, not in the model instructions, so they can be reviewed and signed off by a clinician on their own.

### [2] Dose check (DI-003, UN-003)

Fixed rules, no model. Any request about a medication dose gets one pre-written refusal that directs the patient to the care team. Target: 0 dose recommendations across all scenarios, including the ten that push for one.

Open: the screen designs add a general line about insulin timing after the refusal, while the browser test page returns only the fixed text. One version has to be frozen before the bench test (DHF 6.2).

### [3] Answer from the knowledge base (DI-002, DI-006, DI-007; UN-002, UN-006, UN-007)

Retrieve the passages closest to the question from the approved knowledge base, then have the model write a short answer from those passages only, showing the source.

- Any passage that carries a safety condition is shown word for word, not reworded (DHF 6.2, 2026-11-10 observation).
- Every response at or below a 6th-grade reading level (DI-007), measured by a readability checker on each response, not asserted in the prompt.
- If no approved answer exists, say so plainly and name the right resource: care team, hotline, MyChart, classes or supplies (DI-006). Target: at least 90% correct referral.
- Do not attach a source to a declined or out-of-scope reply (DHF 6.2).

Target: at least 90% of answers rated accurate by a clinician (DI-002).

### [4] Summary (DI-004, UN-004)

At the end of each chat, write a summary of the readings, symptoms and questions in the transcript. Target: at least 90% of summaries include every reading, symptom and question. Tagged [PoC], so it is in scope now, not deferred.

### Not yet built, per DHF 7.1

- Guided check-in (DI-005, [Next]): prompts for regimen, reading, time, last meal and last dose.
- MyChart integration (DI-008, [Future]). The proof of concept runs in a MyChart-style mock-up.

---

## 3. Components (DHF 7.1 names)

| Component | Contents |
|---|---|
| Interface | MyChart-style chat mock-up (DI-008) |
| Knowledge base | Penn Survival Skills, the Diabetes Action Plan, the insulin dose worksheet, and 13 educator FAQ answers from Carolyn Raimondo. Clinician-supplied, pending approval. Standing in for them today: the ADA type 1 and type 2 guides and six one-pagers, each tagged `Type: 1 / 2 / both` |
| Rule set | The draft red-flag thresholds from DI-001, pending clinical sign-off. Its own file, separate from the dose rule and the model instructions |
| Model instructions | One frozen set, stored and versioned with each test build so a run can be reproduced (DHF 6.3, step 3) |
| Data | Invented test data only (DI-009) |

"Approved" throughout the DHF describes how the finished tool has to work. Until each source and each answer has been reviewed and signed off, the knowledge base is clinician-supplied material pending final approval.

Keep the red-flag rules, the dose rule and the model instructions in separate files. Three layers only work if one deduplicating refactor cannot remove all three.

---

## 4. v1 as built, and how it diverges

Built and working in `main.py`:

- Two-call loop: a topic router over curated folders, then answer generation
- Curated corpus in `kb_curated/` with per-document citation and an always-included when-to-get-help page
- Source precedence rules (patient action plan, then team FAQs)
- Patient-language matching
- Bounded conversation history (7 messages for the answer, 5 for the router)
- Provider fallback across two hosted APIs
- 26-item test set and `run_tests.py`, which scores routing only
- Terminal interface
- Invented test data only, so DI-009 holds

Divergences from the DHF, in the order they should be fixed:

1. **Step order is inverted.** The first call is the topic classifier, a model call. Red flags and dose refusals exist only as rules 5 and 3 inside the second model call. Everything the DHF puts in front of the model is currently behind it.
2. **No red-flag check (DI-001).** No numeric parsing anywhere. The "unclear symptoms load both folders" rule is routing, not a threshold check.
3. **No fixed emergency message.** The model writes a fresh urgent reply each turn, so the replies are not identical and cannot be scored against DI-001.
4. **No dose check (DI-003) as a step,** and `test_questions.txt` has no dose-seeking cases. `kb_curated/insulin_devices/team-faqs.txt` currently answers a mealtime insulin timing question, which step 2 would intercept.
5. **No summary (DI-004).**
6. **No referral list (DI-006).** Replies say "contact your care team" generically.
7. **No reading-level measurement (DI-007).** The browser prototype prints reading level; `main.py` prints token counts.
8. **Citations are per document, not per passage.** DI-002's "Where this came from" screen quotes the passage. Topic-folder routing cannot point at a sentence.
9. **Knowledge base contents differ.** `kb_curated/` is ADA material. The three Penn documents the DHF names are still [to request].
10. **Model instructions are not frozen or versioned.** `RULES` lives in `main.py`, so "lock the prototype" (DHF 6.3, step 3) cannot be done.

The topic router has no DHF requirement behind it. It stays for now as the retrieval mechanism for step 3, and it is an implementation choice, not a design output.

---

## 5. Model strategy

| Step | Model class | Why |
|---|---|---|
| [1] red-flag check | None | Deterministic |
| [2] dose check | None | Deterministic |
| [3] answer | Mid-tier | Writes from retrieved passages under several constraints |
| [3] retrieval | Small or none | Folder routing today |
| [4] summary | Small | Extraction from a transcript |

The corpus in the prompt is stable across turns, so prompt caching applies to the answer step and is the largest cost lever. Local models are viable for routing and adequate for development iteration, not for any number that goes in the presentation.

v1 calls hosted APIs on consumer or free tiers. Nothing resembling real patient data may pass through the system, including anything a sponsor or interviewee describes from a real case (DI-009).

---

## 6. Open questions

1. **Red-flag wording and thresholds.** Both are drafts until Dr. Jo Kamimoto signs off. The emergency message is a placeholder.
2. **Dose refusal wording.** Screen design and test page differ. Freeze one before the bench test.
3. **"Keeps dropping" with no number.** Should an unquantified low count as a red flag? For the clinical reviewers (DHF 6.2).
4. **Approved model access for PHI.** Gates everything downstream. Ask Dr. Reuther and the sponsor.
5. **Penn source documents.** Survival Skills, the Diabetes Action Plan and the insulin dose worksheet are still [to request] (Design Plan 4.6).
6. **Corpus ownership.** Who maintains the knowledge base after the course, and who signs off on its clinical content.

---

## 7. Notes for building with a coding agent

- Pin library versions and have the agent check current docs before writing provider code.
- Write the evaluation sets by hand, or review every item. An agent generating both the tests and the code that passes them proves nothing.
- Keep the red-flag rules, the dose rule and the model instructions in separate files.
- Every step returns its intermediate state to the log, not just its output: the rule that fired, the source shown, the reading grade and the response time, which are the columns the DHF 6.3 raw-data sheet expects.
- Keep DECISIONS.md current. Where it and this document disagree, DECISIONS.md records what was actually chosen.
