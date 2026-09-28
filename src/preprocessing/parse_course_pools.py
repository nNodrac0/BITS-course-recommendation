import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import fitz

from src.preprocessing.bulletin_parser import (
    find_pool_section_range,
    find_pool_sections,
    build_discipline_elective_pools,
    extract_humanities_pool,
)

BULLETIN_PATH = "dataset/bulletin.pdf"
OUTPUT_PATH = Path("data/processed/course_pools.json")


def main():
    start_page, end_page = find_pool_section_range(BULLETIN_PATH)
    print(f"Course pools section: pages {start_page} to {end_page - 1} (found dynamically)")

    doc = fitz.open(BULLETIN_PATH)
    full_text = ""
    for page_num in range(start_page, end_page):
        full_text += " ".join(doc[page_num].get_text().split()) + " "

    sections = find_pool_sections(full_text)
    print(f"Programme sections found: {len(sections)}")

    untranslated = [s["pool_header_name"] for s in sections if "no_translation_found" in s["flags"]]
    if untranslated:
        print(f"WARNING - no translation found for: {untranslated}")

    discipline_pools = build_discipline_elective_pools(full_text, sections)
    humanities_pool = extract_humanities_pool(full_text)

    output = {
        "discipline_elective_pools": discipline_pools,
        "humanities_elective_pool": humanities_pool,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    sizes = {name: len(codes) for name, codes in discipline_pools.items()}
    empty_pools = [name for name, size in sizes.items() if size == 0]
    inferred = [s["programme_name"] for s in sections if s["flags"]]

    print(f"Discipline elective pool sizes: min {min(sizes.values())}, max {max(sizes.values())}")
    print(f"Empty pools: {empty_pools}")
    print(f"Names inferred by elimination: {inferred}")
    print(f"Humanities pool size: {len(humanities_pool)}")


if __name__ == "__main__":
    main()