import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.student_profile import StudentProfile
from src.engine.requirement_engine import build_eligible_course_set
from src.llm.query_parser import parse_query
from src.llm.narrowing import narrow_candidates
from src.llm.judge_explain import judge_and_explain

with open(PROJECT_ROOT / "data/processed/programmes.json", encoding="utf-8") as f:
    programmes = json.load(f)
with open(PROJECT_ROOT / "data/processed/course_pools.json", encoding="utf-8") as f:
    course_pools = json.load(f)
with open(PROJECT_ROOT / "data/processed/handouts.json", encoding="utf-8") as f:
    handouts = json.load(f)

handout_codes = {h["course_code"] for h in handouts if h["course_code"] and not h["is_out_of_scope"]}
courses_by_code = {h["course_code"]: h for h in handouts if h["course_code"]}
chemical = next(p for p in programmes if p["programme_name"] == "B.E. Chemical")

completed = [
    "BITS F103", "BIO F101", "CHEM F101", "MATH F101", "PHY F101", "BITS F101", "BITS K101",
    "BITS F111", "BITS F112", "CS F111", "MATH F113", "MATH F102", "EEE F111", "BITS F102",
    "MATH F211", "CHE F211", "CHE F214", "CHE F213", "CHE F212", "BITS F225",
    "ECON F211", "BITS F214",
]
profile = StudentProfile(campus="Pilani", programme_name="B.E. Chemical", admission_year=2023,
                          current_semester=5, completed_courses=completed)

QUERY = "I need a HUEL related to environment or sustainability, no midsem if possible"

parsed = parse_query(QUERY)
print("STAGE 1 - parsed query:")
print(json.dumps(parsed, indent=2))
print()

result = build_eligible_course_set("B.E. Chemical", profile, chemical, course_pools, handout_codes)
category = parsed["category"]
if category not in result["elective_candidates"]:
    print(f"WARNING: no remaining requirement for '{category}' - falling back")
    category = next(iter(result["elective_candidates"]), None)
candidates = result["elective_candidates"].get(category, [])
print(f"Deterministic eligible candidates in category '{category}': {len(candidates)}")

narrowed = narrow_candidates(candidates, courses_by_code, parsed["structured_filters"], parsed["topic_interest"])
print(f"STAGE 2 - narrowed to: {len(narrowed)}")
print()

final = judge_and_explain(
    QUERY, narrowed, courses_by_code,
    parsed["topic_interest"], parsed["unmatched_preferences"],
)
print("STAGE 3 - final recommendations:")
print(json.dumps(final, indent=2))