import subprocess
import sys
import os
from pathlib import Path
import xml.etree.ElementTree as ET

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"23269_english_2026-02-05.pdf"


def check_pdftohtml_installed():
    """Check if pdftohtml is installed"""
    try:
        result = subprocess.run(['pdftohtml', '-v'],
                                capture_output=True, text=True)
        return True
    except FileNotFoundError:
        return False


def extract_with_pdftohtml():
    """Extract PDF using pdftohtml converting to XML"""
    print("PDF to HTML/XML Extraction")
    print("=" * 50)
    print(f"PDF Path: {pdf_path}")
    print(f"Console encoding: {sys.stdout.encoding}\n")

    # Check if pdftohtml is available
    if not check_pdftohtml_installed():
        print("❌ pdftohtml not found. Installing poppler-utils...")
        try:
            subprocess.run(['choco', 'install', 'poppler', '-y'], check=True)
            print("✓ Poppler installed successfully\n")
        except:
            print("⚠ Could not install poppler automatically.")
            print("Please install manually: choco install poppler -y\n")
            return

    # Create output directory
    output_dir = "pdf_html_output"
    os.makedirs(output_dir, exist_ok=True)

    print(f"Converting PDF to HTML/XML format...")
    print(f"Output directory: {output_dir}\n")

    try:
        # Convert PDF to XML (most detailed format)
        output_prefix = os.path.join(output_dir, "output")

        # Run pdftohtml with XML output
        cmd = [
            'pdftohtml',
            '-c',           # Generate complex HTML
            '-hidden',      # Include hidden text
            '-xml',         # Output XML format (most detailed)
            pdf_path,
            output_prefix
        ]

        print(f"Running: {' '.join(cmd)}\n")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✓ PDF conversion successful!\n")

            # Find generated files
            xml_files = list(Path(output_dir).glob("output*.xml"))
            print(f"Generated {len(xml_files)} XML files\n")

            # Extract text from XML files
            all_text = []
            for xml_file in sorted(xml_files):
                print(f"Processing: {xml_file.name}")
                try:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()

                    # Extract all text from XML
                    text_elements = root.findall('.//text')
                    page_text = ""
                    for elem in text_elements:
                        if elem.text:
                            page_text += elem.text + "\n"

                    if page_text.strip():
                        all_text.append(page_text)
                        print(f"  ✓ Extracted {len(page_text)} characters")
                    else:
                        print(f"  No text found")
                except Exception as e:
                    print(f"  ❌ Error parsing {xml_file}: {e}")

            # Save combined text
            output_file = "extracted_pdftohtml.txt"
            combined_text = "\n\n".join(all_text)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(combined_text)

            print(f"\n{'='*50}")
            print(f"✓ Extraction complete!")
            print(f"Total characters: {len(combined_text)}")
            print(f"Saved to: {output_file}")
            print(f"HTML/XML files saved in: {output_dir}")
            print(f"{'='*50}")

        else:
            print(f"❌ Conversion failed: {result.stderr}")

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    extract_with_pdftohtml()


if __name__ == "__main__":
    main()
