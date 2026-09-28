import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pdfplumber

from src.preprocessing.timetable_parser import find_equivalence_section_range, parse_equivalence_table

TIMETABLE_PATH = "dataset/timetable.pdf"
OUTPUT_PATH = Path("data/processed/course_equivalences.json")


def main():
    start_page, end_page = find_equivalence_section_range(TIMETABLE_PATH)
    print(f"Equivalence section: pages {start_page} to {end_page - 1} (found dynamically)")

    with pdfplumber.open(TIMETABLE_PATH) as pdf:
        equivalence_map = parse_equivalence_table(pdf, start_page, end_page)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(equivalence_map, f, indent=2, ensure_ascii=False)

    group_sizes = [len(v) + 1 for v in equivalence_map.values()]
    print(f"Courses with at least one equivalent: {len(equivalence_map)}")
    print(f"Largest equivalence group size: {max(group_sizes)}")

    sample_code = "CS F213"
    print(f"\nSpot check - {sample_code}: {equivalence_map.get(sample_code)}")


if __name__ == "__main__":
    main()