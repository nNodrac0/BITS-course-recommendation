import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pdfplumber

from src.preprocessing.bulletin_parser import find_programme_pages, parse_programme_page

BULLETIN_PATH = "dataset/bulletin.pdf"
OUTPUT_PATH = Path("data/processed/programmes.json")


def main():
    programme_pages = find_programme_pages(BULLETIN_PATH)
    print(f"Located {len(programme_pages)} programme pages dynamically")

    records = []
    with pdfplumber.open(BULLETIN_PATH) as pdf:
        for page_num, programme_name in programme_pages:
            record = parse_programme_page(pdf, page_num, programme_name)
            records.append(record)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False, default=asdict)

    course_slots = 0
    elective_placeholders = 0
    none_units = 0
    no_table_found = []

    for record in records:
        if "no_table_found" in record["flags"]:
            no_table_found.append(record["programme_name"])
        for year in record["years"]:
            if "skipped_reason" in year:
                continue
            for sem_key in ("semester_1", "semester_2"):
                for slot in year[sem_key]:
                    if slot.slot_type == "course":
                        course_slots += 1
                    else:
                        elective_placeholders += 1
                    if slot.units is None:
                        none_units += 1

    print(f"Parsed {len(records)} programmes -> {OUTPUT_PATH}")
    print(f"Course slots: {course_slots}")
    print(f"Elective placeholders: {elective_placeholders}")
    print(f"Slots with units=None: {none_units}")
    if no_table_found:
        print(f"Programmes with no table found: {no_table_found}")


if __name__ == "__main__":
    main()