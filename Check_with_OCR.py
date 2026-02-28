from pdfminer.high_level import extract_text

text = extract_text("23269_english_2026-02-05.pdf")

with open("extracted_pdfminer.txt", "w", encoding="utf-8") as output_file:
	output_file.write(text)