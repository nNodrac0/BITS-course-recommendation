import os
import re
from dataclasses import dataclass, field
from typing import Optional

import fitz
import pdfplumber

FIELD_KEYWORDS = {
    "course_description": r"course description",
    "attendance_policy": r"attendance",
    "makeup_policy": r"make[\s-]?up",
    "grading_policy": r"grad(e|ing)",
}

HEADING_PATTERN = re.compile(r"(?:\d{1,2}|[IVX]{1,4})\.\s*([A-Z][A-Za-z0-9 &/\-]*?):")

INSTRUCTOR_FOLLOWING_LABELS = re.compile(
    r"(?:Email|Co-Instructors?|Practical Lab Instructors?|"
    r"Lecture Instructors?|Tutorial Instructors?|Class Timings)\s*:",
    re.IGNORECASE,
)

UNNUMBERED_HEADING_PATTERN = re.compile(
    r"(Attendance(?:\s+Policy)?|Make[\s-]?up(?:\s+Policy)?|Grading(?:\s+Policy)?|"
    r"Academic Conduct(?:\s+Policy)?|Chamber Consultation(?:\s+Hour)?|Notices)\s*:",
    re.IGNORECASE,
)

COURSE_CODE_PATTERN = r"[A-Z]{2,6}\s*[A-Z]\s*\d{3}T?"

OUT_OF_SCOPE_CODE_PATTERN = re.compile(r"[A-Z]+\s*[GUEC]\d{3}T?")

INSTRUCTOR_LABEL_PATTERN = re.compile(r"Instructor[\s-]+in[\s-]+Charge", re.IGNORECASE)


def find_all_headings(normalized_text):
    numbered = [(m.group(1), m.start(), m.end()) for m in HEADING_PATTERN.finditer(normalized_text)]
    unnumbered = [(m.group(1), m.start(), m.end()) for m in UNNUMBERED_HEADING_PATTERN.finditer(normalized_text)]
    combined = numbered + unnumbered
    combined.sort(key=lambda h: h[1])
    return combined


def extract_sections(normalized_text, headings):
    result = {}
    unverified = []

    for field_name, keyword_pattern in FIELD_KEYWORDS.items():
        match_index = None
        for i, (heading_text, start, end) in enumerate(headings):
            if re.search(keyword_pattern, heading_text, re.IGNORECASE):
                match_index = i
                break

        if match_index is None:
            result[field_name] = None
            unverified.append(field_name)
            continue

        content_start = headings[match_index][2]
        if match_index + 1 < len(headings):
            content_end = headings[match_index + 1][1]
        else:
            content_end = len(normalized_text)

        result[field_name] = normalized_text[content_start:content_end].strip()

    return result, unverified


def extract_course_code(normalized_text):
    pattern = r"Course\s+(?:No\.?|Number)\s*:?\s*(" + COURSE_CODE_PATTERN + r")"
    match = re.search(pattern, normalized_text, re.IGNORECASE)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def extract_course_title(normalized_text):
    match = re.search(r"Course Title\s*:\s*(.+?)\s*Instructor", normalized_text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def extract_instructor(normalized_text, headings):
    label_match = INSTRUCTOR_LABEL_PATTERN.search(normalized_text)
    if not label_match:
        return None

    value_start = label_match.end()
    if normalized_text[value_start:value_start + 1] == ":":
        value_start += 1
    remainder = normalized_text[value_start:]

    candidates = [len(remainder)]
    paren = remainder.find("(")
    if paren != -1:
        candidates.append(paren)
    following_label = INSTRUCTOR_FOLLOWING_LABELS.search(remainder)
    if following_label:
        candidates.append(following_label.start())
    for _, start, _ in headings:
        if start >= value_start:
            candidates.append(start - value_start)

    cutoff = min(candidates)
    value = remainder[:cutoff].strip(" :\t")
    return value if value else None


def clean_cell(text):
    if text is None:
        return None
    text = text.replace("-\n", "").replace("\n", " ")
    return text.strip()


def find_column_map(header_row):
    keywords = {
        "name": "component",
        "duration": "duration",
        "weightage": "weightage",
        "marks": "marks",
        "date_time": "date",
        "nature": "nature",
    }
    column_map = {}
    for field, keyword in keywords.items():
        for i, cell in enumerate(header_row):
            if cell and keyword in cell.lower():
                column_map[field] = i
                break
    return column_map


def parse_weightage(raw):
    if not raw:
        return None
    raw = raw.replace("%", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def parse_marks_total(header_cell):
    if not header_cell:
        return None
    match = re.search(r"\(\s*(\d+(?:\.\d+)?)\s*\)", header_cell)
    return float(match.group(1)) if match else None


def extract_evaluation_scheme(pdf_path):
    components = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table:
                    continue
                header_row = table[0]
                column_map = find_column_map(header_row)

                if "weightage" in column_map:
                    weightage_col = column_map["weightage"]
                    marks_total = None
                elif "marks" in column_map:
                    weightage_col = column_map["marks"]
                    marks_total = parse_marks_total(header_row[weightage_col])
                else:
                    continue

                for row in table[1:]:
                    name = clean_cell(row[column_map.get("name")]) if "name" in column_map else None
                    if not name:
                        continue
                    raw_value = row[weightage_col]
                    if marks_total:
                        raw_marks = parse_weightage(raw_value)
                        weightage_percent = (raw_marks / marks_total * 100) if raw_marks is not None else None
                    else:
                        weightage_percent = parse_weightage(raw_value)
                    components.append({
                        "name": name,
                        "duration": clean_cell(row[column_map.get("duration")]) if "duration" in column_map else None,
                        "weightage_percent": weightage_percent,
                        "date_time": clean_cell(row[column_map.get("date_time")]) if "date_time" in column_map else None,
                        "nature": clean_cell(row[column_map.get("nature")]) if "nature" in column_map else None,
                    })
                return components
    return components


@dataclass
class HandoutRecord:
    course_code: Optional[str]
    course_title: Optional[str]
    instructor_in_charge: Optional[str]
    course_description: Optional[str]
    attendance_policy: Optional[str]
    makeup_policy: Optional[str]
    grading_policy: Optional[str]
    is_out_of_scope: bool
    evaluation_scheme: list = field(default_factory=list)
    unverified_fields: list = field(default_factory=list)
    source_file: str = ""


def parse_single_handout(path):
    doc = fitz.open(path)
    full_text = "\n".join(page.get_text() for page in doc)
    normalized = re.sub(r"\s+", " ", full_text)
    headings = find_all_headings(normalized)

    sections, unverified = extract_sections(normalized, headings)
    evaluation_scheme = extract_evaluation_scheme(path)
    if not evaluation_scheme:
        unverified.append("evaluation_scheme")

    course_code = extract_course_code(normalized)
    if course_code is None:
        unverified.append("course_code")

    course_title = extract_course_title(normalized)
    if course_title is None:
        unverified.append("course_title")

    instructor = extract_instructor(normalized, headings)
    if instructor is None:
        unverified.append("instructor_in_charge")

    is_out_of_scope = bool(course_code and OUT_OF_SCOPE_CODE_PATTERN.fullmatch(course_code))

    return HandoutRecord(
        course_code=course_code,
        course_title=course_title,
        instructor_in_charge=instructor,
        course_description=sections["course_description"],
        attendance_policy=sections["attendance_policy"],
        makeup_policy=sections["makeup_policy"],
        grading_policy=sections["grading_policy"],
        is_out_of_scope=is_out_of_scope,
        evaluation_scheme=evaluation_scheme,
        unverified_fields=unverified,
        source_file=os.path.basename(path),
    )