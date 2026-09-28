import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.preprocessing.handout_parser import parse_single_handout

HANDOUTS_DIR = Path("dataset/handouts")
OUTPUT_PATH = Path("data/processed/handouts.json")


def main():
    files = sorted(HANDOUTS_DIR.glob("*.pdf"))
    records = []
    failures = []

    for path in files:
        try:
            record = parse_single_handout(str(path))
            records.append(asdict(record))
        except Exception as e:
            failures.append((path.name, str(e)))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Parsed {len(records)}/{len(files)} handouts -> {OUTPUT_PATH}")
    if failures:
        print(f"{len(failures)} hard failures (exceptions, not unverified fields):")
        for name, err in failures:
            print(f"  {name}: {err}")

    fields = [
        "course_title", "course_code", "makeup_policy", "evaluation_scheme",
        "course_description", "attendance_policy", "grading_policy", "instructor_in_charge",
    ]
    n = len(records)
    print(f"\nCoverage (field confidently determined, i.e. not in unverified_fields):")
    for field_name in fields:
        confirmed = sum(1 for r in records if field_name not in r["unverified_fields"])
        print(f"  {field_name}: {confirmed}/{n} = {confirmed/n*100:.1f}%")

    higher_degree = sum(1 for r in records if r["is_higher_degree"])
    print(f"\nHigher-degree (G-series) handouts: {higher_degree}/{n}")


if __name__ == "__main__":
    main()