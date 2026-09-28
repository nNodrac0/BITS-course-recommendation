import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.preprocessing.timetable_parser import find_coursewise_timetable_range, extract_offered_course_codes

TIMETABLE_PATH = "dataset/timetable.pdf"
OUTPUT_PATH = Path("data/processed/offered_courses.json")


def main():
    start_page, end_page = find_coursewise_timetable_range(TIMETABLE_PATH)
    print(f"Coursewise timetable section: pages {start_page} to {end_page - 1} (found dynamically)")

    offered_codes = extract_offered_course_codes(TIMETABLE_PATH, start_page, end_page)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(offered_codes), f, indent=2, ensure_ascii=False)

    print(f"Distinct in-scope course codes confirmed offered this semester: {len(offered_codes)}")

    with open("data/processed/handouts.json", encoding="utf-8") as f:
        handouts = json.load(f)
    handout_codes = {h["course_code"] for h in handouts if h["course_code"] and not h["is_out_of_scope"]}
    print(f"Confirmed offered but with no handout in our dataset: {len(offered_codes - handout_codes)}")
    print(f"Have a handout but NOT confirmed offered (worth a look): {len(handout_codes - offered_codes)}")


if __name__ == "__main__":
    main()