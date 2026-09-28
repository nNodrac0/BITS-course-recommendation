import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pdfplumber
from src.preprocessing.bulletin_parser import find_programme_pages, parse_programme_page

all_pages = find_programme_pages("dataset/bulletin.pdf")
by_name = dict(all_pages)

test_names = ["B.E. Architecture and Urban Engineering", "B. Pharm."]

with pdfplumber.open("dataset/bulletin.pdf") as pdf:
    for name in test_names:
        page_num = next(p for p, n in all_pages if n == name)
        result = parse_programme_page(pdf, page_num, name)
        none_count = 0
        alt_count = 0
        for year in result["years"]:
            if "skipped_reason" in year:
                continue
            for sem_key in ("semester_1", "semester_2"):
                for slot in year[sem_key]:
                    if slot.units is None:
                        none_count += 1
                    if slot.is_alternative:
                        alt_count += 1
        print(f"{name} (page {page_num}): units=None count = {none_count}, alternative slots = {alt_count}")