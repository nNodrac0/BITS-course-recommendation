import fitz
import re

MARKER_PATTERN = re.compile(
    r"Semester-wise Pattern for Students Admitted to (.+?) (?:Programme|Stream)"
)

SEARCH_START = 200
SEARCH_END = 250

doc = fitz.open("dataset/bulletin.pdf")

found = []
for page_num in range(SEARCH_START, SEARCH_END):
    text = " ".join(doc[page_num].get_text().split())
    match = MARKER_PATTERN.search(text)
    if match:
        programme_name = match.group(1).strip()
        found.append((page_num, programme_name))

print(f"Matches found: {len(found)}")
for page_num, name in found:
    print(f"  page {page_num}: {name}")