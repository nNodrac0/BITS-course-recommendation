import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import fitz
from src.preprocessing.bulletin_parser import find_pool_section_range, find_pool_sections

start_page, end_page = find_pool_section_range("dataset/bulletin.pdf")
print(f"Section range found: pages {start_page} to {end_page - 1}")

doc = fitz.open("dataset/bulletin.pdf")
full_text = ""
for page_num in range(start_page, end_page):
    full_text += " ".join(doc[page_num].get_text().split()) + " "

sections = find_pool_sections(full_text)
print(f"Sections found: {len(sections)} (expected 28)\n")
for s in sections:
    flag_note = f" <- {s['flags']}" if s["flags"] else ""
    print(f"  {s['programme_name']}{flag_note}")