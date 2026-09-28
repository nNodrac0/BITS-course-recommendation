CATEGORY_NORMALIZATION = {
    "discipline elective": "discipline_elective",
    "discipline electives": "discipline_elective",
    "humanities elective": "humanities_elective",
    "humanities electives": "humanities_elective",
    "open elective": "open_elective",
    "open electives": "open_elective",
    "open/humanities electives": "open_or_humanities_elective",
}


def normalize_category(raw_category):
    key = raw_category.strip().lower()
    if key not in CATEGORY_NORMALIZATION:
        raise ValueError(f"Unrecognized elective category: {raw_category!r}")
    return CATEGORY_NORMALIZATION[key]

#True if course_code or any of its equivalents is in target_set
def code_matches_any(course_code, target_set, equivalence_map=None):
    if course_code in target_set:
        return True
    for equivalent in (equivalence_map or {}).get(course_code, []):
        if equivalent in target_set:
            return True
    return False

def categorize_completed_course(course_code, programme_name, named_course_codes, course_pools, equivalence_map=None):
    if code_matches_any(course_code, named_course_codes, equivalence_map):
        return "named"

    discipline_pool = course_pools["discipline_elective_pools"].get(programme_name, [])
    if code_matches_any(course_code, discipline_pool, equivalence_map):
        return "discipline_elective"

    if code_matches_any(course_code, course_pools["humanities_elective_pool"], equivalence_map):
        return "humanities_elective"

    return "open_elective"

def expand_with_equivalents(codes, equivalence_map):
    if not equivalence_map:
        return set(codes)
    expanded = set(codes)
    for code in codes:
        expanded.update(equivalence_map.get(code, []))
    return expanded

def collect_named_courses_and_elective_requirements(programme_record):
    named_course_codes = set()
    elective_required_counts = {}
    for year_record in programme_record["years"]:
        if "skipped_reason" in year_record:
            continue
        for sem_key in ("semester_1", "semester_2"):
            for slot in year_record[sem_key]:
                if slot["slot_type"] == "course":
                    named_course_codes.add(slot["course_code"])
                elif slot["slot_type"] == "elective_placeholder":
                    category = normalize_category(slot["category"])
                    elective_required_counts[category] = elective_required_counts.get(category, 0) + 1
    return named_course_codes, elective_required_counts


def collect_named_course_groups(programme_record):
    groups = []
    current_group = None
    for year_record in programme_record["years"]:
        if "skipped_reason" in year_record:
            continue
        for sem_num, sem_key in [(1, "semester_1"), (2, "semester_2")]:
            for slot in year_record[sem_key]:
                if slot["slot_type"] != "course":
                    current_group = None
                    continue
                if slot["is_alternative"] and current_group is not None:
                    current_group["codes"].append(slot["course_code"])
                else:
                    current_group = {
                        "codes": [slot["course_code"]],
                        "year": year_record["year"],
                        "semester": sem_num,
                    }
                    groups.append(current_group)
    return groups


def allocate_elective_completions(completed_electives_with_categories, elective_required_counts):
    completed_by_category = {
        "discipline_elective": 0,
        "humanities_elective": 0,
        "open_elective": 0,
        "open_or_humanities_elective": 0,
    }

    for category in completed_electives_with_categories:
        if category == "discipline_elective":
            buckets = ["discipline_elective", "open_elective"]
        elif category == "humanities_elective":
            buckets = ["humanities_elective", "open_or_humanities_elective", "open_elective"]
        elif category == "open_elective":
            buckets = ["open_elective", "open_or_humanities_elective"]
        else:
            continue

        for bucket in buckets:
            required = elective_required_counts.get(bucket, 0)
            if completed_by_category[bucket] < required:
                completed_by_category[bucket] += 1
                break

    remaining = {
        bucket: max(0, elective_required_counts.get(bucket, 0) - completed_by_category.get(bucket, 0))
        for bucket in elective_required_counts
    }

    return completed_by_category, remaining


YEAR_TO_NUMBER = {"I": 1, "II": 2, "III": 3, "IV": 4}


def group_position(group):
    return (YEAR_TO_NUMBER[group["year"]] - 1) * 2 + group["semester"]


def filter_eligible_named_groups(remaining_named_groups):
    if not remaining_named_groups:
        return []
    min_position = min(group_position(g) for g in remaining_named_groups)
    return [g for g in remaining_named_groups if group_position(g) == min_position]


def compute_requirement_status(programme_name, student_profile, programme_record, course_pools, equivalence_map=None):
    named_groups = collect_named_course_groups(programme_record)
    _, elective_required_counts = collect_named_courses_and_elective_requirements(programme_record)

    completed_set = set(student_profile.completed_courses)
    all_named_codes = {code for group in named_groups for code in group["codes"]}

    remaining_named_groups = [
        g for g in named_groups
        if not any(code_matches_any(c, completed_set, equivalence_map) for c in g["codes"])
    ]

    elective_candidate_courses = [c for c in student_profile.completed_courses if not code_matches_any(c, all_named_codes, equivalence_map)]
    categorized = [
        categorize_completed_course(c, programme_name, all_named_codes, course_pools, equivalence_map)
        for c in elective_candidate_courses
    ]

    completed_by_category, remaining_electives = allocate_elective_completions(categorized, elective_required_counts)

    return {
        "remaining_named_groups": remaining_named_groups,
        "elective_required_counts": elective_required_counts,
        "completed_by_category": completed_by_category,
        "remaining_electives": remaining_electives,
    }


def build_eligible_course_set(programme_name, student_profile, programme_record, course_pools, offered_codes, equivalence_map=None):
    named_groups = collect_named_course_groups(programme_record)
    _, elective_required_counts = collect_named_courses_and_elective_requirements(programme_record)

    completed_set = set(student_profile.completed_courses)
    current_set = set(student_profile.current_courses)
    all_named_codes = {code for group in named_groups for code in group["codes"]}

    remaining_named_groups = [
        g for g in named_groups
        if not any(code_matches_any(c, completed_set, equivalence_map) for c in g["codes"])
    ]
    eligible_named_groups = filter_eligible_named_groups(remaining_named_groups)

    elective_candidate_courses = [
        c for c in student_profile.completed_courses
        if not code_matches_any(c, all_named_codes, equivalence_map)
    ]
    categorized = [
        categorize_completed_course(c, programme_name, all_named_codes, course_pools, equivalence_map)
        for c in elective_candidate_courses
    ]
    completed_by_category, remaining_electives = allocate_elective_completions(categorized, elective_required_counts)

    discipline_pool = set(course_pools["discipline_elective_pools"].get(programme_name, []))
    humanities_pool = set(course_pools["humanities_elective_pool"]) - discipline_pool
    unavailable = expand_with_equivalents(completed_set | current_set | all_named_codes, equivalence_map)

    elective_candidates = {}
    if remaining_electives.get("discipline_elective", 0) > 0:
        elective_candidates["discipline_elective"] = sorted(discipline_pool - unavailable)
    if remaining_electives.get("humanities_elective", 0) > 0:
        elective_candidates["humanities_elective"] = sorted(humanities_pool - unavailable)
    if remaining_electives.get("open_elective", 0) > 0:
        open_pool = offered_codes - discipline_pool - humanities_pool
        elective_candidates["open_elective"] = sorted(open_pool - unavailable)
    if remaining_electives.get("open_or_humanities_elective", 0) > 0:
        flex_pool = humanities_pool | (offered_codes - discipline_pool - humanities_pool)
        elective_candidates["open_or_humanities_elective"] = sorted(flex_pool - unavailable)

    return {
        "eligible_named_courses": eligible_named_groups,
        "remaining_electives": remaining_electives,
        "elective_candidates": elective_candidates,
    }