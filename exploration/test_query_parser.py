import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm.query_parser import parse_query

QUERIES = [
    # from the brief directly
    "Suggest DELs related to AI.",
    "I want an OPEL with no attendance requirement.",
    "Suggest courses with no midsem and a lenient makeup policy.",
    "I need a HUEL and prefer project-based evaluation.",
    # deliberately different phrasings - not shaped like the above, to check
    # this isn't just overfit to the brief's own four examples
    "I want something chill, not too much work",
    "looking for a good professor teaching something in machine learning",
    "any elective is fine as long as it's not too many quizzes",
    "avoid 8 AM classes if possible",
]

for q in QUERIES:
    result = parse_query(q)
    print(f"QUERY: {q}")
    print(json.dumps(result, indent=2))
    print()