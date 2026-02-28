import easyocr
import pdf2image
import sys
import os
from pathlib import Path
import cv2
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"C:\Users\SAMPR\OneDrive\Desktop\GitHub Projects\Hanzards\23269_english_2026-02-05.pdf"


def convert_pdf_to_images_pymupdf(pdf_path, output_dir, dpi=200, max_pages=None, start_page=1):
    """Convert PDF to images using PyMuPDF (no poppler required)."""
    if fitz is None:
        print("❌ PyMuPDF not installed. Install with: pip install pymupdf")
        return []

    os.makedirs(output_dir, exist_ok=True)
    try:
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        last_page = total_pages
        if max_pages is not None:
            last_page = min(total_pages, start_page + max_pages - 1)

        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        image_paths = []

        for page_index in range(start_page - 1, last_page):
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            image_path = os.path.join(
                output_dir, f"page_{page_index + 1:03d}.png")
            pix.save(image_path)
            image_paths.append(image_path)

        print(
            f"✓ Converted {len(image_paths)} pages to images using PyMuPDF\n")
        return image_paths
    except Exception as e:
        print(f"❌ Error converting with PyMuPDF: {e}")
        return []


def convert_pdf_to_images(pdf_path, output_dir="pdf_images", dpi=200, max_pages=None, start_page=1):
    """Convert PDF to images for OCR processing"""
    print("Converting PDF to images...")
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Convert PDF pages to images
        last_page = None
        if max_pages is not None:
            last_page = start_page + max_pages - 1
        images = pdf2image.convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=start_page,
            last_page=last_page,
        )
        print(f"✓ Converted {len(images)} pages to images\n")

        # Save images
        image_paths = []
        for i, image in enumerate(images, start_page):
            image_path = os.path.join(output_dir, f"page_{i:03d}.png")
            image.save(image_path, "PNG")
            image_paths.append(image_path)

        return image_paths
    except Exception as e:
        print(f"❌ Error converting PDF: {e}")
        print("Falling back to PyMuPDF renderer...")
        return convert_pdf_to_images_pymupdf(
            pdf_path,
            output_dir=output_dir,
            dpi=dpi,
            max_pages=max_pages,
            start_page=start_page,
        )


def get_cached_images(output_dir, max_pages=None, start_page=1):
    """Return cached images if available"""
    image_paths = sorted(Path(output_dir).glob("page_*.png"))
    if not image_paths:
        return []
    if start_page > 1:
        image_paths = [p for p in image_paths if int(
            p.stem.split("_")[-1]) >= start_page]
    if max_pages is not None:
        image_paths = image_paths[:max_pages]
    return [str(p) for p in image_paths]


def extract_text_with_ocr(pdf_path, languages=['en'], max_pages=None, start_page=1, dpi=200):
    """
    Extract text from PDF using EasyOCR
    Supports Sinhala ('si') and English ('en')
    """
    print("PDF Extraction with OCR (EasyOCR)")
    print("=" * 60)
    print(f"PDF Path: {pdf_path}")
    print(f"Languages: {languages}")
    print(f"Console encoding: {sys.stdout.encoding}\n")

    output_dir = "pdf_images"
    image_paths = get_cached_images(
        output_dir, max_pages=max_pages, start_page=start_page)
    if image_paths:
        print(f"Using cached images from: {output_dir}\n")
    else:
        # Convert PDF to images
        image_paths = convert_pdf_to_images(
            pdf_path,
            output_dir=output_dir,
            dpi=dpi,
            max_pages=max_pages,
            start_page=start_page,
        )

    if not image_paths:
        print("❌ Failed to convert PDF to images")
        return

    # Initialize OCR reader for Sinhala and English
    print("Initializing OCR reader (downloading language models)...")
    print("This may take a few minutes on first run...\n")

    try:
        reader = easyocr.Reader(languages, gpu=False)
    except Exception as e:
        print(f"❌ Error initializing OCR: {e}")
        return

    all_text = []

    print("Starting OCR extraction...\n")

    for idx, image_path in enumerate(image_paths, 1):
        page_num = start_page + idx - 1
        print(f"--- Page {page_num} ---")

        try:
            # Read image
            image = cv2.imread(image_path)

            # Perform OCR
            results = reader.readtext(image, detail=1)

            if results:
                # Extract text from OCR results
                page_text = ""
                confidence_scores = []

                for detection in results:
                    text = detection[1]
                    confidence = detection[2]
                    page_text += text + " "
                    confidence_scores.append(confidence)

                all_text.append(page_text.strip())

                avg_confidence = sum(
                    confidence_scores) / len(confidence_scores) if confidence_scores else 0

                print(f"✓ Text extracted: {len(page_text)} characters")
                print(f"✓ Detected elements: {len(results)}")
                print(f"✓ Average confidence: {avg_confidence:.2%}")
            else:
                print("No text detected")
                all_text.append("")

            print(f"Progress: {idx}/{len(image_paths)}\n")

        except Exception as e:
            print(f"❌ Error processing page {page_num}: {e}\n")
            all_text.append("")

    # Save OCR results
    ocr_output = "extracted_ocr_easyocr.txt"
    with open(ocr_output, "w", encoding="utf-8") as f:
        for i, text in enumerate(all_text, start_page):
            f.write(f"===== PAGE {i} =====\n")
            f.write(text)
            f.write("\n\n")

    combined_text = "\n\n".join(all_text)

    print(f"\n{'='*60}")
    print(f"✓ OCR Extraction Complete!")
    print(f"{'='*60}")
    print(f"Total pages processed: {len(image_paths)}")
    print(f"Total text characters: {len(combined_text)}")
    print(f"Output file: {ocr_output}")
    print(f"Image cache: {os.path.dirname(image_paths[0])}")
    print(f"{'='*60}")


def extract_with_detailed_analysis(pdf_path, max_pages=10, start_page=1):
    """
    Extract with detailed analysis for first N pages
    Shows confidence scores and bounding boxes
    """
    print("\n" + "=" * 60)
    print("Detailed OCR Analysis (First Pages)")
    print("=" * 60 + "\n")

    image_paths = get_cached_images(
        "pdf_images", max_pages=max_pages, start_page=start_page)

    if not image_paths:
        print("No images found. Run main extraction first.")
        return

    try:
        reader = easyocr.Reader(['en'], gpu=False)

        for image_path in image_paths:
            print(f"Analyzing: {Path(image_path).name}")

            image = cv2.imread(str(image_path))
            results = reader.readtext(image, detail=1)

            print(f"Detected {len(results)} text elements:")
            # Show first 5
            for i, (bbox, text, confidence) in enumerate(results[:5], 1):
                print(f"  {i}. '{text}' (confidence: {confidence:.2%})")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    max_pages = os.getenv("OCR_MAX_PAGES")
    start_page = os.getenv("OCR_START_PAGE")
    dpi = os.getenv("OCR_DPI")
    max_pages = int(max_pages) if max_pages else None
    start_page = int(start_page) if start_page else 1
    dpi = int(dpi) if dpi else 200

    # Main OCR extraction
    extract_text_with_ocr(pdf_path, max_pages=max_pages,
                          start_page=start_page, dpi=dpi)

    # Detailed analysis
    extract_with_detailed_analysis(
        pdf_path, max_pages=5, start_page=start_page)


if __name__ == "__main__":
    main()
