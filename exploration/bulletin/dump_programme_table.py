import pdfplumber

PAGE_NUM = 210

with pdfplumber.open("dataset/bulletin.pdf") as pdf:
    page = pdf.pages[PAGE_NUM]
    tables = page.extract_tables()
    print(f"Number of tables found on this page: {len(tables)}")

    if tables:
        table = tables[0]
        print(f"Number of rows: {len(table)}")
        print(f"Number of columns in row 0: {len(table[0])}")
        print()
        for i, row in enumerate(table):
            print(f"--- row {i} ---")
            for j, cell in enumerate(row):
                print(f"  col {j}: {cell!r}")