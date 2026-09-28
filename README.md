# BITS Course Recommender

A course recommendation dashboard for BITS Pilani students, built for the Postman Round 2 club recruitment task. Given a student's programme, semester, and completed courses, it determines which courses they are actually eligible for right now, then uses natural-language queries to help pick among them.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root with:

```
GROQ_API_KEY=your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com).

## Regenerating the processed data

The dashboard reads from `data/processed/*.json`, which are derived from the raw PDFs in `dataset/`. To regenerate them from scratch:

```bash
python -m src.preprocessing.parse_handouts
python -m src.preprocessing.parse_bulletin
python -m src.preprocessing.parse_course_pools
python -m src.preprocessing.parse_equivalences
python -m src.preprocessing.parse_timetable_offerings
```

## Running the dashboard

```bash
streamlit run src/dashboard/app.py
```

Set up a profile in the sidebar (programme, current semester, completed courses, currently registered courses, and optional general interests), then ask a question in the chat, e.g. "Suggest a HUEL related to environment" or "I want a DEL, no midsem preferred."

## How it works

1. **Deterministic pre-processing** (`src/preprocessing/`) parses the four source PDFs (handouts, bulletin, timetable, regulations) into structured JSON. Section/page locations are found dynamically by scanning for real marker text, not hardcoded, so new semester data can be dropped in without code changes.
2. **Requirement engine** (`src/engine/requirement_engine.py`) computes which named courses and elective categories a student still needs, based on their programme's semester-wise pattern and completed courses, accounting for cross-listed course-code equivalence from the timetable.
3. **LLM layer** (`src/llm/`), three stages:
   - `query_parser.py` extracts a category (DEL/HUEL/OPEL), topic interest, and structured filters (has_midsem, has_compre, etc.) from the student's natural-language query.
   - `narrowing.py` deterministically filters candidates against those structured filters and does a cheap topic-keyword overlap ranking, without ever hard-filtering on missing data.
   - `judge_explain.py` does the final semantic ranking and explanation, splitting results into courses with enough handout data to confidently recommend, and "unverified candidates" that are eligible but have no handout, with an honest note on whether they're at least confirmed offered this semester per the timetable.
4. **Dashboard** (`src/dashboard/app.py`) ties it together with a chat interface.

## Known limitations

- **Year IV** (Practice School/Thesis) is not tracked as a named-course requirement — it's a registration process, not a fixed course list, and the dashboard says so explicitly rather than silently returning nothing.
- **Minor programmes** are not yet parsed or checked — `regulations.json` documents the overlap-cap rules, but no minor course lists have been extracted from the bulletin yet.
- **Dual degree** (M.Sc. + B.E. composite programmes) is out of scope for this submission. Single-degree recommendation is fully correct; dual degree was deliberately not attempted rather than half-built.
- **Timetable data** only covers "is this course offered this semester" and cross-listed equivalence — sections, instructors, room, and exam-slot clash-checking (the brief's own "brownie point") were not extracted.
- Course `department` (derivable from the code prefix) is not currently a separate field.
- Source citations (which page/document a given fact came from) are tracked internally in `regulations.json` and the bulletin parser, but are not surfaced in the final recommendation text shown to the student.

## Testing

No automated test suite. Every parser was validated by running it against the full real dataset and checking coverage/counts (see print statements in each `parse_*.py` driver script), and the dashboard was smoke-tested manually with real profiles and queries.
