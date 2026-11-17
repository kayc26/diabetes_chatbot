# Curated knowledge base

Step 3 of the software specification (DHF 7.1) sorts each patient question into one or
two of these folders and sends only those documents to the model. Everything in
`always/` is sent with every answer.

Each `.txt` file starts with two header lines, then a blank line, then the text:

```
Source: <original document>
Type: 1 | 2 | both
```

`Source:` is the name the bot cites. `Type:` decides which patients the file is loaded
for. Both types of diabetes are in scope, so the bot asks the patient's type once per
chat and then loads only the files tagged with their type, plus the `both` files. The
raw text extracted from the PDFs stays in `../kb/`.

Every folder except `sweeteners_and_liver/` holds a type 1 file and a type 2 file.
`sweeteners_and_liver/` holds only one-pagers. The one-pagers and the team FAQs are
tagged `both`, so they load for every patient.

| Folder | Contents |
|---|---|
| `always/` | When to get help right away; what to keep on hand (type 1 file only) |
| `basics/` | What the patient's type of diabetes is, and what a new diagnosis means |
| `low_blood_sugar/` | Hypoglycemia, the 15-15 rule and the Rule of 15, glucagon |
| `high_blood_sugar/` | Hyperglycemia, ketones, DKA warning signs |
| `monitoring/` | Meters, CGMs, AID systems, targets, help paying for devices |
| `insulin_devices/` | Insulin and how it is taken (type 1); medications and insulin (type 2) |
| `food/` | Eating with each type, plus Plan Your Plate, portions vs. servings, nutrition FAQs |
| `sweeteners_and_liver/` | Sugar substitutes, healthy eating for liver health |
| `activity/` | Physical activity and staying safe while active, plus the exercise and nutrition one-pager |
| `daily_life/` | Sick days (both types); stress, sleep, work, school, travel, insulin storage (type 1) |
| `support/` | Emotional wellbeing, burnout, the care team, diabetes education, community resources, complications |

Sourced from the two ADA guides. Covers, rights pages, tables of contents, terms pages
and the fill-in tables (My Meds, My ABCs, My Key Appointments) were left out of both.

`team-faqs.txt` in `food/`, `high_blood_sugar/` and `insulin_devices/` holds the team's
FAQ answers, copied on 2026-11-06 from the shared "FAQs" Google Doc
(`sources/FAQs.gdoc`; `sources/` is a git-ignored link to the team's shared Google
Drive folder, so it only resolves on a machine with that Drive synced). The bot is
told to prefer these answers when they cover the question. When the Google Doc
changes, update these files to match, and add any new questions to
`../test_questions.txt`.

## Reviewing

- Check that each file holds what its folder name promises, and move text that belongs
  elsewhere.
- Check that each file's `Type:` line is right. A type 1 patient getting type 2
  medication guidance, or the reverse, is the failure this header exists to prevent.
- Fix PDF extraction breaks (words split across lines) where they change the meaning.
- After any change, bump `KB_VERSION` in `main.py`. It is written to every line of the
  audit log (`../logs/`) and to the top of every test report, so each answer can be
  traced to the knowledge base that produced it.
- Then run `python run_tests.py` from the project folder and read the report in
  `../test_results/`. Cases run as a type 2 patient unless the line in
  `../test_questions.txt` ends with `| 1`.
- The DHF names Penn Survival Skills, the Diabetes Action Plan, the insulin dose
  worksheet and the educator FAQs as the knowledge base (DHF 7.1). Those Penn documents
  are still [to request], so this folder is ADA material standing in for them.
- Nothing here has clinical sign-off yet. DI-002 wants at least 90% of answers rated
  accurate by a clinician.

## Adding a document

Add a `.txt` file to the right folder with both header lines and a blank line after
them, then bump `KB_VERSION`. No code changes: the loader reads the headers.

- A file with no `Type:` line is treated as `both` and loads for every patient, so
  always set it.
- A `Type:` value other than `1`, `2` or `both` stops the bot at startup.
- A file with no `Source:` line is cited by its file name.

## Adding a category

1. Create a folder here and add `.txt` files in the format above.
2. Add the folder name and a one-line description to `CATEGORIES` in `main.py`.
   The classifier reads that description to decide when to use the folder, and picks
   at most two folders per question (`MAX_CATEGORIES`). The bot will not start if a
   folder listed in `CATEGORIES` is missing here.
3. Add test cases to `../test_questions.txt` with the new folder name as the expected
   value, and run `python run_tests.py`.
