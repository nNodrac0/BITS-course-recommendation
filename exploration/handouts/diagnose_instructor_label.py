import re
import glob
import fitz

HYPHENATED = re.compile(r"Instructor-in-Charge", re.IGNORECASE)
SPACED_NO_HYPHEN = re.compile(r"Instructor\s+in\s+Charge", re.IGNORECASE)
LITERAL_EMAIL_WORD = re.compile(r"Instructor[\s-]+in[\s-]+Charge\s*:?\s*.{0,80}?\(email", re.IGNORECASE)
REAL_EMAIL_IN_PARENS = re.compile(r"Instructor[\s-]+in[\s-]+Charge\s*:?\s*.{0,80}?\([^)]*@[^)]*\)", re.IGNORECASE)

files = sorted(glob.glob("dataset/handouts/*.pdf"))
hyphenated_count = 0
spaced_no_hyphen_count = 0
literal_email_word_count = 0
real_email_count = 0
label_missing_count = 0

for path in files:
    doc = fitz.open(path)
    text = re.sub(r"\s+", " ", "\n".join(p.get_text() for p in doc))

    has_hyphenated = bool(HYPHENATED.search(text))
    has_spaced = bool(SPACED_NO_HYPHEN.search(text)) and not has_hyphenated
    if has_hyphenated:
        hyphenated_count += 1
    elif has_spaced:
        spaced_no_hyphen_count += 1
    else:
        label_missing_count += 1

    if LITERAL_EMAIL_WORD.search(text):
        literal_email_word_count += 1
    if REAL_EMAIL_IN_PARENS.search(text):
        real_email_count += 1

n = len(files)
print(f"Total handouts checked: {n}")
print(f"Label as 'Instructor-in-Charge' (hyphenated, any case): {hyphenated_count}")
print(f"Label as 'Instructor in Charge' (spaced, no hyphen): {spaced_no_hyphen_count}")
print(f"Label not found in either form: {label_missing_count}")
print()
print(f"Handouts where literal text '(email' appears after the label: {literal_email_word_count}")
print(f"Handouts where an actual email address appears in parens after the label: {real_email_count}")