import pdfplumber
import sys
import json
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"c:\Users\ashin\Desktop\hanzards\23269_english_2026-02-05.pdf"

def extract_with_pdfplumber():
    """
    Extract PDF using pdfplumber (Python alternative to pdftohtml)
    More effective for complex PDF layouts
    """
    print("PDF Extraction with pdfplumber")
    print("=" * 60)
    print(f"PDF Path: {pdf_path}")
    print(f"Console encoding: {sys.stdout.encoding}\n")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}\n")
            
            all_text = []
            all_tables = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"--- Page {page_num} ---")
                
                # Extract text
                text = page.extract_text()
                if text:
                    all_text.append(text)
                    print(f"✓ Text extracted: {len(text)} characters")
                else:
                    print("No text found")
                
                # Extract tables if any
                tables = page.extract_tables()
                if tables:
                    print(f"✓ Tables found: {len(tables)}")
                    for table_idx, table in enumerate(tables):
                        all_tables.append({
                            'page': page_num,
                            'table_index': table_idx,
                            'data': table
                        })
                
                # Extract layout information
                chars = page.chars
                if chars:
                    print(f"✓ Characters analyzed: {len(chars)}")
                
                print(f"Progress: {page_num}/{len(pdf.pages)}\n")
            
            # Save extracted text
            text_output = "extracted_pdfplumber.txt"
            with open(text_output, "w", encoding="utf-8") as f:
                for i, text in enumerate(all_text, 1):
                    f.write(f"===== PAGE {i} =====\n")
                    f.write(text)
                    f.write("\n\n")
            
            combined_text = "\n\n".join(all_text)
            
            # Save tables as JSON if any found
            if all_tables:
                tables_output = "extracted_tables.json"
                with open(tables_output, "w", encoding="utf-8") as f:
                    json.dump(all_tables, f, ensure_ascii=False, indent=2)
                print(f"Tables saved to: {tables_output}")
            
            print(f"\n{'='*60}")
            print(f"✓ Extraction Complete!")
            print(f"{'='*60}")
            print(f"Total pages processed: {len(pdf.pages)}")
            print(f"Total text characters: {len(combined_text)}")
            print(f"Total tables found: {len(all_tables)}")
            print(f"Text output: {text_output}")
            print(f"{'='*60}\n")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def extract_with_layout_analysis():
    """
    Extract PDF with detailed layout analysis
    Similar to pdftohtml's complex HTML output
    """
    print("Detailed Layout Analysis")
    print("=" * 60)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            layout_data = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"Analyzing page {page_num}...")
                
                page_layout = {
                    'page': page_num,
                    'width': page.width,
                    'height': page.height,
                    'text_blocks': [],
                    'lines': len(page.lines),
                    'rects': len(page.rects)
                }
                
                # Extract text with bounding boxes
                text = page.extract_text_dict()
                for item in text.get('top_margin', []):
                    page_layout['text_blocks'].append(item)
                
                layout_data.append(page_layout)
            
            # Save layout analysis
            layout_output = "page_layout_analysis.json"
            with open(layout_output, "w", encoding="utf-8") as f:
                json.dump(layout_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ Layout analysis saved to: {layout_output}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    # Main extraction
    extract_with_pdfplumber()
    
    # Detailed layout analysis
    extract_with_layout_analysis()

if __name__ == "__main__":
    main()
