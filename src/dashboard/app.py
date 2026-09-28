import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import streamlit as st

from src.models.student_profile import StudentProfile
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
    handout_codes = {h["course_code"] for h in handouts if h["course_code"] and not h["is_out_of_scope"]}
    courses_by_code = {h["course_code"]: h for h in handouts if h["course_code"]}
    return programmes, course_pools, handout_codes, courses_by_code


programmes, course_pools, handout_codes, courses_by_code = load_data()
programme_names = [p["programme_name"] for p in programmes]

st.title("BITS Course Recommender")

with st.sidebar:
    st.header("Your Profile")
    programme_name = st.selectbox("Programme", programme_names)
    current_semester = st.number_input("Current semester", min_value=1, max_value=8, value=1)
    completed_courses_raw = st.text_area("Completed courses (comma-separated course codes)")
    build_profile = st.button("Save profile")

if "profile" not in st.session_state:
    st.session_state.profile = None
if "messages" not in st.session_state:
    st.session_state.messages = []

if build_profile:
    completed_courses = [c.strip() for c in completed_courses_raw.split(",") if c.strip()]
    st.session_state.profile = StudentProfile(
        campus="Pilani", programme_name=programme_name, admission_year=2023,
        current_semester=current_semester, completed_courses=completed_courses,
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
                result = build_eligible_course_set(
                    profile.programme_name, profile, programme_record, course_pools, handout_codes
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
                        lines.append(f"\n*{len(final['unverified_candidates'])} more courses are eligible for this "
                                      f"category but have no handout data (may not be offered this semester).*")

                    response_text = "\n".join(lines)

            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

    with st.expander("Full eligibility breakdown (debug)"):
        if st.session_state.profile:
            programme_record = next(p for p in programmes if p["programme_name"] == st.session_state.profile.programme_name)
            st.json(build_eligible_course_set(
                st.session_state.profile.programme_name, st.session_state.profile,
                programme_record, course_pools, handout_codes,
            ))