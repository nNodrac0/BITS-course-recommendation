import glob
import pdfplumber

files = sorted(glob.glob("dataset/handouts/*.pdf"))

weightage_style = 0
marks_style = 0
neither_found = 0

for i, path in enumerate(files):
    #Added this because this is a slow process so it shows that the process is running and not stuck
    if i % 50 == 0:
        print(f"...{i}/{len(files)}")
    found_weightage = False
    found_marks = False
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    if not table or not table[0]:
                        continue
                    header = " ".join(c for c in table[0] if c).lower()
                    if "weightage" in header:
                        found_weightage = True
                    elif "marks" in header and ("component" in header or "duration" in header):
                        found_marks = True
    except Exception:
        continue

    if found_weightage:
        weightage_style += 1
    elif found_marks:
        marks_style += 1
    else:
        neither_found += 1


n = len(files)
print(f"Total handouts checked: {n}")
print(f"Real table found, 'Weightage' column style: {weightage_style}")
print(f"Real table found, 'Marks(total)' column style: {marks_style}")
print(f"No recognizable evaluation table found by either style: {neither_found}")