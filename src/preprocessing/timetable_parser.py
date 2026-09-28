import re

import fitz

EQUIVALENCE_START_MARKER = re.compile(r"LIST OF EQUIVALENT COURSES", re.IGNORECASE)
EQUIVALENCE_END_MARKER = re.compile(r"LIBRARY AND BITS COOP", re.IGNORECASE)

from src.preprocessing.handout_parser import OUT_OF_SCOPE_CODE_PATTERN

COURSEWISE_TIMETABLE_MARKER = re.compile(r"COURSEWISE TIMETABLE", re.IGNORECASE)
COURSEWISE_TIMETABLE_END_MARKER = re.compile(r"TEXT\s*BOOKS", re.IGNORECASE)
COURSE_CODE_PATTERN = re.compile(r"[A-Z]{2,6}\s+[A-Z]\d{3}T?")


def find_coursewise_timetable_range(pdf_path, search_start=0, search_end=120):
    doc = fitz.open(pdf_path)
    start_page = None
    end_page = None
    for page_num in range(search_start, search_end):
        text = " ".join(doc[page_num].get_text().split())
        if start_page is None and COURSEWISE_TIMETABLE_MARKER.search(text):
            start_page = page_num
        if start_page is not None and page_num > start_page and COURSEWISE_TIMETABLE_END_MARKER.search(text):
            end_page = page_num
            break
    return start_page, end_page


def extract_offered_course_codes(pdf_path, start_page, end_page):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page_num in range(start_page, end_page):
        full_text += " ".join(doc[page_num].get_text().split()) + " "

    codes = {m.group(0) for m in COURSE_CODE_PATTERN.finditer(full_text)}
    return {c for c in codes if not OUT_OF_SCOPE_CODE_PATTERN.fullmatch(c)}


def find_equivalence_section_range(pdf_path, search_start=100, search_end=140):
    doc = fitz.open(pdf_path)
    start_page = None
    end_page = None
    for page_num in range(search_start, search_end):
        text = " ".join(doc[page_num].get_text().split())
        if start_page is None and EQUIVALENCE_START_MARKER.search(text):
            start_page = page_num
        if start_page is not None and page_num > start_page and EQUIVALENCE_END_MARKER.search(text):
            end_page = page_num
            break
    return start_page, end_page


def parse_equivalence_table(pdf, start_page, end_page):
    equivalence_map = {}

    for page_num in range(start_page, end_page):
        page = pdf.pages[page_num]
        tables = page.extract_tables()
        if not tables:
            continue
        for row in tables[0]:
            if not row or not row[0] or row[0].strip().upper() == "COURSE NO.":
                continue
            course_code = row[0].strip()
            row_codes = {course_code}
            for cell in row[2:]:
                if cell and cell.strip():
                    row_codes.add(cell.strip())

            if len(row_codes) < 2:
                continue

            for code in row_codes:
                others = row_codes - {code}
                equivalence_map.setdefault(code, set()).update(others)

    return {code: sorted(others) for code, others in equivalence_map.items()}