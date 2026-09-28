import json
import os
import time

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "openai/gpt-oss-120b"

QUERY_PARSE_PROMPT = """You are helping a BITS Pilani student find courses. Given their
natural-language request, extract:

- "category": one of "discipline_elective", "humanities_elective", "open_elective",
  "open_or_humanities_elective", or null if not specified - this must be one of these
  exact values because it maps to a fixed category in the university's course structure.
  Students commonly use these exact abbreviations, which map one-to-one:
  DEL = discipline_elective, HUEL = humanities_elective, OPEL = open_elective.
  "open_or_humanities_elective" is a separate, flexible category - only use it if the
  request explicitly mentions both open and humanities together, never as a guess for OPEL.
- "topic_interest": a short free-text description of the subject matter they're interested
  in (e.g. "artificial intelligence and machine learning"), or null if none mentioned.
- "structured_filters": a JSON object with any of these keys the student's request clearly
  implies - "has_midsem": true/false, "has_compre": true/false, "has_quiz": true/false,
  "has_project": true/false. Only include a key if the student's wording clearly maps to it
  (e.g. "no midsem" -> has_midsem: false, "prefer project-based evaluation" -> has_project:
  true). Omit any key you're not confident about - do not guess.
- "unmatched_preferences": a list of short free-text strings for anything the student wants
  or wants to avoid that does NOT map to one of the structured_filters keys above (e.g.
  "lenient makeup policy", "good professor", "not too many quizzes", "avoid 8 AM classes") -
  written exactly as the kind of thing you'd check against a course's official handout or
  timetable. Do not limit yourself to any fixed list of preference types.

Student's request: "{query}"

Return ONLY a JSON object with these four fields, no other text."""


def parse_query(query, client=None, max_retries=3):
    client = client or Groq(api_key=os.environ["GROQ_API_KEY"])
    prompt = QUERY_PARSE_PROMPT.format(query=query)

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)