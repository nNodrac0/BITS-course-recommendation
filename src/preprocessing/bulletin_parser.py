import re
from dataclasses import dataclass
from typing import Optional

import fitz

COURSE_CODE_IN_TABLE = re.compile(r"[A-Z]{2,6}\s+[A-Z]\d{3}T?")
ELECTIVE_CATEGORY_PATTERN = re.compile(r"(?:Open/)?(?:Humanities|Open|Discipline)\s+Electives?")
ALTERNATIVE_MARKER_PATTERN = re.compile(r"\bor\b", re.IGNORECASE)

PROGRAMME_PAGE_MARKER = re.compile(
    r"Semester-wise Pattern for Students Admitted to (.+?) (?:Programme|Stream)"
)


def find_programme_pages(pdf_path, search_start=200, search_end=250):
    doc = fitz.open(pdf_path)
    found = []
    for page_num in range(search_start, search_end):
        text = " ".join(doc[page_num].get_text().split())
        match = PROGRAMME_PAGE_MARKER.search(text)
        if match:
            found.append((page_num, match.group(1).strip()))
    return found


@dataclass
class CourseSlot:
    slot_type: str
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    category: Optional[str] = None
    units: Optional[str] = None
    is_alternative: bool = False


def find_all_markers(flat_text):
    markers = []
    for m in COURSE_CODE_IN_TABLE.finditer(flat_text):
        markers.append(("course", m.group(0), m.start(), m.end()))
    for m in ELECTIVE_CATEGORY_PATTERN.finditer(flat_text):
        markers.append(("elective_placeholder", m.group(0), m.start(), m.end()))
    for m in ALTERNATIVE_MARKER_PATTERN.finditer(flat_text):
        markers.append(("alternative", m.group(0), m.start(), m.end()))
    markers.sort(key=lambda x: x[2])
    return markers


def split_cell_into_entries(course_text, units_text):
    flat_courses = re.sub(r"\s+", " ", course_text).strip()
    unit_values = [u.strip() for u in units_text.split("\n") if u.strip().lower() != "or"]

    markers = find_all_markers(flat_courses)
    if not markers:
        return []

    entries = []
    leading_text = flat_courses[:markers[0][2]].strip()
    pending_alternative = False
    unit_i = 0
    last_units = None

    def next_unit():
        nonlocal unit_i
        value = unit_values[unit_i] if unit_i < len(unit_values) else None
        unit_i += 1
        return value

    for i, (marker_type, marker_text, start, end) in enumerate(markers):
        start_of_next = markers[i + 1][2] if i + 1 < len(markers) else len(flat_courses)
        trailing = flat_courses[end:start_of_next].strip()

        if marker_type == "alternative":
            pending_alternative = True
            continue

        units = last_units if pending_alternative else next_unit()
        last_units = units

        if marker_type == "course":
            title = trailing
            if len(entries) == 0 and leading_text:
                title = (leading_text + " " + title).strip()
            entries.append(CourseSlot(
                slot_type="course", course_code=marker_text, course_title=title,
                units=units, is_alternative=pending_alternative,
            ))
        elif marker_type == "elective_placeholder":
            entries.append(CourseSlot(
                slot_type="elective_placeholder", category=marker_text,
                units=units, is_alternative=pending_alternative,
            ))

        pending_alternative = False

    return entries


def classify_and_parse_row(row):
    label = row[0]

    if label is None:
        return None
    if "Semester-wise Pattern" in label:
        return None
    if label == "Year":
        return None
    if label.startswith("Summer"):
        return None

    if label in ("I", "II", "III"):
        first_sem = split_cell_into_entries(row[1] or "", row[2] or "")
        second_sem = split_cell_into_entries(row[3] or "", row[4] or "")
        return {"year": label, "semester_1": first_sem, "semester_2": second_sem}

    if label == "IV":
        return {
            "year": "IV", "semester_1": [], "semester_2": [],
            "skipped_reason": (
                "Practice School / Thesis alternatives are represented via "
                "regulations.json's practice_school_thesis_rule instead of "
                "parsing this row directly - the raw text here has jumbled "
                "reading order and drops the department-code prefix after "
                "the first alternative."
            ),
        }

    return None


def parse_programme_page(pdf, page_num, programme_name):
    page = pdf.pages[page_num]
    tables = page.extract_tables()
    if not tables:
        return {"programme_name": programme_name, "source_page": page_num, "years": [], "flags": ["no_table_found"]}

    years = []
    for row in tables[0]:
        parsed = classify_and_parse_row(row)
        if parsed:
            years.append(parsed)

    return {"programme_name": programme_name, "source_page": page_num, "years": years, "flags": []}



CORE_COURSES_MARKER = re.compile(r"CORE COURSES")
DISCIPLINE_ELECTIVE_MARKER = re.compile(r"DISCIPLINE ELECTIVE COURSES")
PROJECT_TYPE_MARKER = re.compile(r"Project Type Courses")
HUMANITIES_START_MARKER = re.compile(r"Pool of Humanities courses")
HUMANITIES_END_MARKER = re.compile(r"Other Courses")


POOL_HEADER_PATTERN = re.compile(
    r"((?:[A-Z][A-Z&,\-\u2013]*|\u2013)(?:\s+(?:[A-Z][A-Z&,\-\u2013]*|\u2013))*)\s*$"
)

#Need to add this dict because many names mismatch
POOL_HEADER_TO_PROGRAMME_NAME = {
    "ARCHITECTURAL AND URBAN ENGINEERING": "B.E. Architecture and Urban Engineering",
    "BIOTECHNOLOGY": "B.E. Biotechnology",
    "BIOTECHNOLOGY WITH SPECIALIZATION IN APPLIED MOLECULAR BIOLOGY": "B.E. Biotechnology with Specialization in Applied Molecular Biology",
    "CHEMICAL ENGINEERING": "B.E. Chemical",
    "CHEMICAL ENGINEERING WITH SPECIALIZATION IN ENERGY, ENVIRONMENT, AND SUSTAINABILITY": "B.E. Chemical with Specialization in Energy, Environment, and Sustainability",
    "CIVIL ENGINEERING": "B.E. Civil",
    "COMPUTER SCIENCE": "B. E. Computer Science",
    "ELECTRICAL AND ELECTRONICS ENGINEERING": "B.E. Electrical & Electronics",
    "ELECTRONICS AND COMMUNICATION ENGINEERING": "B.E. Electronics & Communication",
    "ELECTRONICS AND COMPUTER ENGINEERING": "B.E. Electronics & Computer Engineering",
    "ELECTRONICS AND INSTRUMENTATION ENGINEERING": "B.E. Electronics and Instrumentation",
    "ENVIRONMENTAL AND SUSTAINABILITY ENGINEERING": "B.E. Environmental and Sustainability Engineering",
    "MANUFACTURING ENGINEERING": "B.E. Manufacturing",
    "MATHEMATICS AND COMPUTING": "B.E. Mathematics and Computing",
    "MECHANICAL ENGINEERING": "B.E. Mechanical",
    "MECHANICAL ENGINEERING WITH SPECIALIZATION IN AEROSPACE": "B.E. Mechanical with Specialization in Aerospace",
    "PHARMACY": "B. Pharm.",
    "BIOLOGICAL SCIENCES": "M.Sc. Biological Sciences",
    "CHEMISTRY": "M.Sc. Chemistry",
    "ECONOMICS": "M. Sc. Economics",
    "MATHEMATICS": "M.Sc. Mathematics",
    "PHYSICS": "M. Sc. Physics",
    "PHYSICS WITH SPECIALIZATION IN SPACE SCIENCE AND TECHNOLOGY": "M. Sc. Physics specialization in Space Science and Technology",
    "ROBOTICS AND INDUSTRIAL AUTOMATION": "B.E. Robotics & Industrial Automation",
    "GENERAL STUDIES \u2013 COMMUNICATION AND MEDIA STUDIES": "M.Sc. General Studies \u2013 Communication and Media Studies",
    "GENERAL STUDIES \u2013 DEVELOPMENT STUDIES": "M.Sc. General Studies \u2013 Development Studies",
    "SEMICONDUCTOR AND NANOSCIENCE": "M.Sc. Semiconductor and Nanoscience",
    "BBA (Honours)": "Bachelor of Business Administration (Honours)",
}

def find_pool_section_range(pdf_path, search_start=300, search_end=345):
    doc = fitz.open(pdf_path)
    start_page = None
    end_page = None
    for page_num in range(search_start, search_end):
        text = " ".join(doc[page_num].get_text().split())
        if start_page is None and re.search(r"List of Courses for", text):
            start_page = page_num
        if re.search(r"MINOR PROGRAMMES FOR FIRST DEGREE STUDENTS", text):
            end_page = page_num
            break
    return start_page, end_page


def find_pool_sections(full_text):
    sections = []
    for m in CORE_COURSES_MARKER.finditer(full_text):
        preceding_text = full_text[:m.start()]
        header_match = POOL_HEADER_PATTERN.search(preceding_text)
        pool_header_name = None
        if header_match:
            pool_header_name = re.sub(r"\s+(PROGRAMME|STREAM)$", "", header_match.group(1).strip())
        flags = []
        if pool_header_name is None:
            pool_header_name = "BBA (Honours)"
            flags.append("name_inferred_by_elimination")

        programme_name = POOL_HEADER_TO_PROGRAMME_NAME.get(pool_header_name)
        if programme_name is None:
            programme_name = pool_header_name
            flags.append("no_translation_found")

        sections.append({
            "programme_name": programme_name,
            "pool_header_name": pool_header_name,
            "core_courses_start": m.end(),
            "flags": flags,
        })
    return sections


def compute_section_ranges(sections, full_text):
    ranges = []
    for i, s in enumerate(sections):
        start = s["core_courses_start"]
        if i + 1 < len(sections):
            end = sections[i + 1]["core_courses_start"]
        else:
            project_marker = PROJECT_TYPE_MARKER.search(full_text, start)
            end = project_marker.start() if project_marker else len(full_text)
        ranges.append((s["programme_name"], start, end))
    return ranges


def extract_discipline_elective_codes(full_text, start, end):
    slice_text = full_text[start:end]
    de_marker = DISCIPLINE_ELECTIVE_MARKER.search(slice_text)
    if not de_marker:
        return []
    pool_slice = slice_text[de_marker.end():]
    return [m.group(0) for m in COURSE_CODE_IN_TABLE.finditer(pool_slice)]


def build_discipline_elective_pools(full_text, sections):
    ranges = compute_section_ranges(sections, full_text)
    return {
        programme_name: extract_discipline_elective_codes(full_text, start, end)
        for programme_name, start, end in ranges
    }


def extract_humanities_pool(full_text):
    start_marker = HUMANITIES_START_MARKER.search(full_text)
    end_marker = HUMANITIES_END_MARKER.search(full_text)
    if not start_marker or not end_marker:
        return []
    slice_text = full_text[start_marker.end():end_marker.start()]
    return [m.group(0) for m in COURSE_CODE_IN_TABLE.finditer(slice_text)]