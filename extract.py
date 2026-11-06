"""Convert every PDF in sources/ into a .txt file in kb/."""
from pathlib import Path
from pypdf import PdfReader

SOURCES = Path("sources")
KB = Path("kb")
KB.mkdir(exist_ok=True)

for pdf in sorted(SOURCES.glob("*.pdf")):
    reader = PdfReader(pdf)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    out = KB / (pdf.stem + ".txt")
    out.write_text(text, encoding="utf-8")

    words = len(text.split())
    flag = "  <-- check this one, very little text came out" if words < 50 else ""
    print(f"{pdf.name} -> {out.name} ({words} words){flag}")