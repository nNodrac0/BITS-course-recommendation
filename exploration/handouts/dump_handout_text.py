import fitz

FILES = [
    "049_BITS_F416.pdf",   
    "521_PHY_G541.pdf",    
    "371_MATH_F421.pdf",   
    "535_SNS_F242.pdf",    
    "128_CHE_F376.pdf",
]

for name in FILES:
    doc = fitz.open(f"dataset/handouts/{name}")
    text = "\n".join(page.get_text() for page in doc)
    out_path = f"exploration/handouts/dumps_{name.replace('.pdf', '.txt')}"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{name}: {len(text)} chars -> {out_path}")