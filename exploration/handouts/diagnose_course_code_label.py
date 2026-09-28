import re
import glob
import fitz

LABEL_NO = re.compile(r"Course\s+No\.?\s*:", re.IGNORECASE)
LABEL_NUMBER = re.compile(r"Course\s+Number\s*:", re.IGNORECASE)
CODE_PATTERN = re.compile(r"Course\s+(?:No\.?|Number)\s*:?\s*([A-Z]{2,6}\s*[A-Z]\s*\d{3}T?)", re.IGNORECASE)
HIGHER_DEGREE = re.compile(r"^[A-Z]+\s*G\d{3}T?$")

files = sorted(glob.glob("dataset/handouts/*.pdf"))

label_no = 0
label_number = 0
label_neither = 0
code_found = 0
higher_degree = 0
first_degree = 0

for path in files:
    doc = fitz.open(path)
    text = re.sub(r"\s+", " ", "\n".join(p.get_text() for p in doc))

    if LABEL_NO.search(text):
        label_no += 1
    elif LABEL_NUMBER.search(text):
        label_number += 1
    else:
        label_neither += 1

    m = CODE_PATTERN.search(text)
    if m:
        code_found += 1
        code = re.sub(r"\s+", " ", m.group(1)).strip()
        if HIGHER_DEGREE.match(code):
            higher_degree += 1
        else:
            first_degree += 1

n = len(files)
print(f"Total handouts checked: {n}")
print(f"Label 'Course No'/'Course No.': {label_no}")
print(f"Label 'Course Number': {label_number}")
print(f"Neither label found: {label_neither}")
print()
print(f"Course code successfully extracted: {code_found}/{n}")
print(f"  of which higher-degree (G-series): {higher_degree}")
print(f"  of which first-degree: {first_degree}")