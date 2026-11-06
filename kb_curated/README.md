# Curated knowledge base

`main.py` sorts each patient question into one or two of these folders and sends only
those documents to the model. Everything in `always/` is sent with every question.

Each `.txt` file starts with a `Source: <original document>` line, which is the name
the bot cites. The raw text extracted from the PDFs stays in `../kb/`.

| Folder | Contents |
|---|---|
| `always/` | When to get help right away; what to keep on hand (type 1 guide p. 9) |
| `basics/` | What type 1 diabetes is (type 1 guide p. 4) |
| `low_blood_sugar/` | Hypoglycemia, the 15-15 rule, glucagon (type 1 guide p. 5–7) |
| `high_blood_sugar/` | Hyperglycemia, ketones, DKA (type 1 guide p. 7–8) |
| `monitoring/` | Meters, CGMs, AID systems, target range (type 1 guide p. 10–12) |
| `insulin_devices/` | Insulin and ways to take it (type 1 guide p. 13) |
| `food/` | Type 1 guide p. 14–16, Plan Your Plate, portions vs. servings, nutrition FAQs |
| `sweeteners_and_liver/` | Sugar substitutes, healthy eating for liver health |
| `activity/` | Type 1 guide p. 17–19, exercise and nutrition one-pager |
| `daily_life/` | Sick days, stress, sleep, work, school, travel (type 1 guide p. 20–22) |
| `support/` | Emotional wellbeing, care team, education, information sources (type 1 guide p. 23–31) |

The type 1 guide's cover, table of contents, and terms page (p. 1–3) were left out.

## Reviewing

- Check that each file holds what its folder name promises, and move text that belongs elsewhere.
- Fix PDF extraction breaks (words split across lines) where they change the meaning.
- Every safety topic (lows, highs, DKA, sick days) currently comes from a **type 1** guide.
  Many newly diagnosed adults have type 2, so a type 2 source is a known gap.

## Adding a category

1. Create a folder here and add `.txt` files that start with `Source: <document name>` and a blank line.
2. Add the folder name and a one-line description to `CATEGORIES` in `main.py`.
   The classifier reads that description to decide when to use the folder.
