import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import streamlit as st

from src.models.student_profile import StudentProfile, semester_to_year_position
from src.engine.requirement_engine import build_eligible_course_set
from src.llm.query_parser import parse_query
from src.llm.narrowing import narrow_candidates
from src.llm.judge_explain import judge_and_explain


@st.cache_data
def load_data():
    with open(PROJECT_ROOT / "data/processed/programmes.json", encoding="utf-8") as f:
        programmes = json.load(f)
    with open(PROJECT_ROOT / "data/processed/course_pools.json", encoding="utf-8") as f:
        course_pools = json.load(f)
    with open(PROJECT_ROOT / "data/processed/handouts.json", encoding="utf-8") as f:
        handouts = json.load(f)
    with open(PROJECT_ROOT / "data/processed/offered_courses.json", encoding="utf-8") as f:
        offered_codes = set(json.load(f))
    courses_by_code = {h["course_code"]: h for h in handouts if h["course_code"]}
    return programmes, course_pools, offered_codes, courses_by_code


programmes, course_pools, offered_codes, courses_by_code = load_data()
programme_names = [p["programme_name"] for p in programmes]

st.title("BITS Course Recommender")

with st.sidebar:
    st.header("Your Profile")
    programme_name = st.selectbox("Programme", programme_names)
    current_semester = st.number_input("Current semester", min_value=1, max_value=8, value=1)
    completed_courses_raw = st.text_area("Completed courses (comma-separated course codes)")
    current_courses_raw = st.text_area("Currently registered courses (comma-separated course codes)")
    interests_raw = st.text_area("General academic interests (comma-separated, optional)")
    build_profile = st.button("Save profile")

if "profile" not in st.session_state:
    st.session_state.profile = None
if "messages" not in st.session_state:
    st.session_state.messages = []

if build_profile:
    completed_courses = [c.strip() for c in completed_courses_raw.split(",") if c.strip()]
    current_courses = [c.strip() for c in current_courses_raw.split(",") if c.strip()]
    interests = [c.strip() for c in interests_raw.split(",") if c.strip()]
    st.session_state.profile = StudentProfile(
        campus="Pilani", programme_name=programme_name, admission_year=2023,
        current_semester=current_semester, completed_courses=completed_courses,
        current_courses=current_courses, interests=interests,
    )
    st.session_state.messages = []
    st.sidebar.success("Profile saved. Ask a question below.")

if st.session_state.profile is None:
    st.info("Set up your profile in the sidebar and click 'Save profile' to start.")
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    query = st.chat_input("Ask about courses, e.g. 'Suggest a HUEL related to environment'")
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Checking your eligibility and matching courses..."):
                profile = st.session_state.profile
                programme_record = next(p for p in programmes if p["programme_name"] == profile.programme_name)

                parsed = parse_query(query)
                if not parsed.get("topic_interest") and profile.interests:
                    parsed["topic_interest"] = ", ".join(profile.interests)
                result = build_eligible_course_set(
                    profile.programme_name, profile, programme_record, course_pools, offered_codes
                )

                category = parsed["category"]
                if category not in result["elective_candidates"]:
                    available = list(result["elective_candidates"].keys())
                    category = available[0] if available else None

                if category is None:
                    response_text = (
                        "You don't currently have any remaining elective requirements "
                        "to fill, based on your profile."
                    )
                else:
                    candidates = result["elective_candidates"][category]
                    narrowed = narrow_candidates(
                        candidates, courses_by_code, parsed["structured_filters"], parsed["topic_interest"]
                    )
                    final = judge_and_explain(
                        query, narrowed, courses_by_code,
                        parsed["topic_interest"], parsed["unmatched_preferences"],
                        offered_codes=offered_codes,
                    )

                    lines = [f"**Category:** {category.replace('_', ' ').title()}\n"]
                    if final["recommendations"]:
                        lines.append("**Recommendations:**")
                        for rec in final["recommendations"]:
                            title = courses_by_code.get(rec["course_code"], {}).get("course_title") or "(title unavailable)"
                            lines.append(f"- **{rec['course_code']}** - {title}\n  {rec['explanation']}")
                    else:
                        lines.append("No courses with enough data to confidently recommend were found.")

                    if final.get("unverified_candidates"):
                        confirmed_offered = sum(1 for c in final["unverified_candidates"] if "Confirmed offered" in c["note"])
                        not_offered = len(final["unverified_candidates"]) - confirmed_offered
                        lines.append(f"\n*{len(final['unverified_candidates'])} more courses are eligible for this "
                                      f"category without enough data to rank ({confirmed_offered} confirmed offered "
                                      f"this semester but missing a handout, {not_offered} not found in this "
                                      f"semester's timetable).*")

                    response_text = "\n".join(lines)

                year_roman, _ = semester_to_year_position(profile.current_semester)
                if year_roman == "IV" and not result["eligible_named_courses"]:
                    response_text += (
                        "\n\n*Note: Year IV is governed by the Practice School/Thesis process, "
                        "not a fixed named-course list, so this system doesn't track named-course "
                        "eligibility for Year IV - see regulations.json's practice_school_thesis_rule "
                        "for the actual policy.*"
                    )

            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

    with st.expander("Full eligibility breakdown (debug)"):
        if st.session_state.profile:
            programme_record = next(p for p in programmes if p["programme_name"] == st.session_state.profile.programme_name)
            st.json(build_eligible_course_set(
                st.session_state.profile.programme_name, st.session_state.profile,
                programme_record, course_pools, offered_codes,
            ))