import json
import os
import time

from dotenv import load_dotenv
from groq import Groq

from src.llm.narrowing import derive_course_flags

load_dotenv()

MODEL = "openai/gpt-oss-120b"

JUDGE_EXPLAIN_PROMPT = """A BITS Pilani student asked: "{original_query}"

Their request breaks down to:
- Topic interest: {topic_interest}
- Specific preferences to check: {unmatched_preferences}

Below is a shortlist of courses this student is ACADEMICALLY ELIGIBLE to take right now
(eligibility, prerequisites, and category requirements are already verified separately -
your only job is matching interest and preferences, not re-checking eligibility).

Each course lists what is actually known. A field value of null means it could NOT be
verified from the official course handout - it does NOT mean the property is absent or
false. Never claim a null field is true or false; if the student asked about something
that is null for a course, say explicitly it could not be verified for that course.

Courses:
{courses_json}

Pick the top {top_n} courses that best match the student's topic interest and preferences,
ranked best first. For each, write a short explanation citing the specific facts (or
explicitly noting what couldn't be verified). Return ONLY a JSON object:
{{"recommendations": [{{"course_code": "...", "explanation": "..."}}, ...]}}"""


def build_course_summary(course_code, course_record):
    flags = derive_course_flags(course_record.get("evaluation_scheme", []))
    return {
        "course_code": course_code,
        "title": course_record.get("course_title"),
        "description": (course_record.get("course_description") or "")[:300] or None,
        "has_midsem": flags["has_midsem"],
        "has_compre": flags["has_compre"],
        "has_quiz": flags["has_quiz"],
        "has_project": flags["has_project"],
        "attendance_policy": (course_record.get("attendance_policy") or "")[:200] or None,
        "makeup_policy": (course_record.get("makeup_policy") or "")[:200] or None,
    }


def judge_and_explain(original_query, narrowed_codes, courses_by_code, topic_interest, unmatched_preferences, top_n=5, client=None, max_retries=3, offered_codes=None):
    with_data = []
    unverified = []
    for code in narrowed_codes:
        record = courses_by_code.get(code, {})
        if record.get("course_title") or record.get("course_description"):
            with_data.append(code)
        else:
            unverified.append(code)

    unverified_candidates = []
    for code in unverified:
        if offered_codes and code in offered_codes:
            note = ("Confirmed offered this semester (per the timetable), but no handout was included in the supplied dataset - title, description, and evaluation scheme could not be verified.")
        else:
            note = ("Technically eligible for this category, but not found in this semester's timetable - likely not actually offered this semester.")
        unverified_candidates.append({"course_code": code, "note": note})

    if not with_data:
        return {"recommendations": [], "unverified_candidates": unverified_candidates}

    client = client or Groq(api_key=os.environ["GROQ_API_KEY"])
    courses = [build_course_summary(code, courses_by_code.get(code, {})) for code in with_data]

    prompt = JUDGE_EXPLAIN_PROMPT.format(
        original_query=original_query,
        topic_interest=topic_interest or "not specified",
        unmatched_preferences=unmatched_preferences or "none",
        courses_json=json.dumps(courses, ensure_ascii=False),
        top_n=top_n,
    )

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            result["unverified_candidates"] = unverified_candidates
            return result
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)