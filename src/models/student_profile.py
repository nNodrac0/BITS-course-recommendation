from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StudentProfile:
    campus: str
    programme_name: str
    admission_year: int
    current_semester: int
    completed_courses: list = field(default_factory=list)
    current_courses: list = field(default_factory=list)
    minor: Optional[str] = None
    interests: list = field(default_factory=list)


def semester_to_year_position(current_semester):
    year_number = (current_semester - 1) // 2 + 1
    semester_in_year = 1 if current_semester % 2 == 1 else 2
    year_roman = {1: "I", 2: "II", 3: "III", 4: "IV"}[year_number]
    return year_roman, semester_in_year