from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LAParams, LTTextBox
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"c:\Users\ashin\Desktop\hanzards\23269_english_2026-02-05.pdf"

def extract_text_pdfminer():
    """
    Extract text from PDF using pdfminer.six
    """
    print(f"PDF Path: {pdf_path}")
    print(f"Console encoding: {sys.stdout.encoding}\n")
    
    try:
        # Extract all text at once
        print("Extracting text using pdfminer.six...")
        text = extract_text(pdf_path, laparams=LAParams())
        
        if text:
            print(f"✓ Text extraction successful!")
            print(f"Total characters extracted: {len(text)}\n")
            
            # Save to file
            output_file = "extracted_pdfminer.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(text)
            
            print(f"Saved to: {output_file}")
            return text
        else:
            print("❌ No text found in PDF")
            return ""
            
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        return ""

def extract_text_by_pages():
    """
    Extract text page by page for detailed progress
    """
    print("\n" + "="*50)
    print("Page-by-page extraction:")
    print("="*50 + "\n")
    
    try:
        all_text = []
        page_count = 0
        
        for page_num, page_layout in enumerate(extract_pages(pdf_path, laparams=LAParams()), 1):
            print(f"--- Page {page_num} ---")
            
            page_text = ""
            for element in page_layout:
                if isinstance(element, LTTextBox):
                    page_text += element.get_text()
            
            if page_text.strip():
                all_text.append(page_text)
                print(f"✓ Extracted {len(page_text)} characters")
            else:
                print("No text found")
            
            print(f"Progress: {page_num} pages processed\n")
            page_count = page_num
        
        print(f"{'='*50}")
        print(f"Total pages processed: {page_count}")
        print(f"{'='*50}")
        
        return all_text
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def main():
    # Extract all text at once
    full_text = extract_text_pdfminer()
    
    # Extract page by page with progress tracking
    pages_text = extract_text_by_pages()

if __name__ == "__main__":
    main()
