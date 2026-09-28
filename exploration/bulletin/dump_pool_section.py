import fitz
#pdfplumber's table detection does NOT work reliably here (fragments into near-empty tables, missing the real course data)
doc = fitz.open("dataset/bulletin.pdf")
full_text = ""
for page_num in range(313, 316):  # first 3 pages of the section, enough to look at
    full_text += " ".join(doc[page_num].get_text().split()) + " "

print(full_text[:3000])