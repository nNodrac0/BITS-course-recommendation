import re


def derive_course_flags(evaluation_scheme):
    # Returns True/False if checked, or None if table was missing/unverifiable
    if not evaluation_scheme:
        return {"has_midsem": None, "has_compre": None, "has_quiz": None, "has_project": None}
    names = " ".join(c["name"].lower() for c in evaluation_scheme)
    return {
        "has_midsem": bool(re.search(r"mid[\s-]?sem|midterm", names)),
        "has_compre": bool(re.search(r"compre", names)),
        "has_quiz": bool(re.search(r"quiz", names)),
        "has_project": bool(re.search(r"project", names)),
    }


def matches_structured_filters(course_flags, structured_filters):
    # Drop only on explicit conflict; keep None values to avoid false negatives
    for key, wanted in structured_filters.items():
        actual = course_flags.get(key)
        if actual is not None and actual != wanted:
            return False
    return True


def topic_overlap_score(topic_interest, title, description):
    # Basic word overlap check for initial candidate ranking
    if not topic_interest:
        return 0
    topic_words = set(re.findall(r"[a-z]+", topic_interest.lower()))
    text = f"{title or ''} {description or ''}".lower()
    return sum(1 for w in topic_words if w in text and len(w) > 2)


def narrow_candidates(candidate_codes, courses_by_code, structured_filters, topic_interest, cap=40):
    # Filter by evaluation flags, rank by topic overlap, and truncate to cap
    filtered = []
    for code in candidate_codes:
        course = courses_by_code.get(code, {})
        flags = derive_course_flags(course.get("evaluation_scheme", []))
        if matches_structured_filters(flags, structured_filters):
            filtered.append(code)

    if topic_interest:
        filtered.sort(
            key=lambda code: topic_overlap_score(
                topic_interest,
                courses_by_code.get(code, {}).get("course_title"),
                courses_by_code.get(code, {}).get("course_description"),
            ),
            reverse=True,
        )

    return filtered[:cap]