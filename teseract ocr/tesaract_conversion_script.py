"""
Hansard OCR Pipeline using Tesseract
====================================
Converts Sri Lankan Parliamentary Hansard PDFs (Sinhala/Tamil/English)
into clean, structured Markdown.

QUICK START
-----------
1) Install Python dependencies:
    pip install pytesseract pdf2image Pillow

2) Install OCR tools:
    Linux:
        sudo apt-get install tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam poppler-utils
    macOS:
        brew install tesseract tesseract-lang poppler
    Windows (recommended):
        winget install -e --id UB-Mannheim.TesseractOCR
        winget install -e --id oschwartz10612.Poppler

WINDOWS NOTES (IMPORTANT)
-------------------------
- Do NOT paste markdown links into PowerShell. Use plain command text only.
- If Sinhala/Tamil are not installed in Tesseract, create a local `.tessdata` folder
  and set `TESSDATA_PREFIX` to that folder.
- In a new terminal, you may need to expose Poppler/Tesseract on PATH before running.

Example for current PowerShell session:
    $popBin = "C:\\Users\\<you>\\AppData\\Local\\Microsoft\\WinGet\\Packages\\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\\poppler-25.07.0\\Library\\bin"
    $env:Path = "C:\\Program Files\\Tesseract-OCR;$popBin;" + $env:Path
    $env:TESSDATA_PREFIX = (Resolve-Path ".tessdata").Path

USAGE
-----
    python tesaract_conversion_script.py input.pdf output.md
    python tesaract_conversion_script.py input.pdf output.md --lang eng
    python tesaract_conversion_script.py input.pdf output.md --lang sin+tam+eng

PAGES
-----
    --pages 20      => only page 20
    --pages 1-20    => pages 1 through 20

Examples:
    python tesaract_conversion_script.py 23270_english_2026-02-06.pdf output.md --lang sin+tam+eng
    python tesaract_conversion_script.py 23270_english_2026-02-06.pdf output.md --lang sin+tam+eng --pages 1-20
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
except ImportError:
    print("Missing dependencies. Run: pip install pytesseract pdf2image Pillow")
    sys.exit(1)


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

# Language string for Tesseract.
# Use "sin+tam+eng" for full trilingual, "eng" for English-only Hansards.
DEFAULT_LANG = "sin+tam+eng"

# DPI for rendering PDF pages to images. 300 is the minimum for good OCR.
# Use 400 for older/smaller print Hansards.
DPI = 300

# Tesseract page segmentation mode.
# 6 = "Assume a single uniform block of text" — works well for Hansard columns.
# 3 = "Fully automatic page segmentation" — try if 6 gives bad results.
PSM = 6


# ---------------------------------------------------------------------------
# NOISE PATTERNS TO STRIP
# ---------------------------------------------------------------------------

# These regexes match common Hansard page headers/footers to remove.
NOISE_PATTERNS = [
    # Column numbers (e.g. "395", "396 " at start of line)
    r'^\s*\d{3,4}\s*$',
    # "PARLIAMENTARY DEBATES" header
    r'PARLIAMENTARY\s+DEBATES',
    # "HANSARD" header
    r'^\s*HANSARD\s*$',
    # "(HANSARD)" footer
    r'\(HANSARD\)',
    # Sinhala header: හැන්සාඩ්
    r'හැන්සාඩ්',
    # Tamil header: ஹன்சாட்
    r'ஹன்சாட்',
    # Repeated date lines (e.g. "Friday, 06th February, 2026")
    r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+\d+\w+\s+\w+,\s+\d{4}\s*$',
    # Tamil date lines
    r'^(திங்கள்|செவ்வாய்|புதன்|வியாழன்|வெள்ளி|சனி|ஞாயிறு),\s',
    # Sinhala date lines
    r'^(සඳුදා|අඟහරුවාදා|බදාදා|බ්‍රහස්පතින්දා|සිකුරාදා|සෙනසුරාදා|ඉරිදා),\s',
    # "OFFICIAL REPORT" line
    r'OFFICIAL\s+REPORT',
    # Volume/number line
    r'Volume\s+\d+\s*-\s*No\.\s*\d+',
]

NOISE_RE = re.compile('|'.join(NOISE_PATTERNS), re.MULTILINE | re.IGNORECASE)


# ---------------------------------------------------------------------------
# SPEAKER DETECTION
# ---------------------------------------------------------------------------

# Patterns that indicate a speaker attribution line.
# Hansards use "The Hon. X:" or "Hon. X (Title):" patterns.
SPEAKER_PATTERNS = [
    # English: "The Hon. Firstname Lastname" or "MR./MRS./DR. NAME"
    r'^(The\s+Hon\.|Hon\.|MR\.|MRS\.|MS\.|DR\.|GEN\.|LT\.)',
    # Sinhala: ගරු / ගු
    r'^(ගරු|ගු\.?)\s+',
    # Tamil: மாண்புமிகு
    r'^மாண்புமிகு\s+',
    # Speaker himself: "MR. SPEAKER" / "THE SPEAKER"
    r'^(MR\.\s+SPEAKER|THE\s+SPEAKER|ගු කථානායකුරමා|செொநொயகர்)',
]

SPEAKER_RE = re.compile('|'.join(SPEAKER_PATTERNS), re.MULTILINE)


# ---------------------------------------------------------------------------
# SECTION HEADER DETECTION
# ---------------------------------------------------------------------------

# Known section titles to promote to Markdown headers (##).
SECTION_KEYWORDS = [
    'ANNOUNCEMENTS', 'ORAL ANSWERS TO QUESTIONS', 'WRITTEN ANSWERS TO QUESTIONS',
    'QUESTIONS', 'PETITIONS', 'PAPERS PRESENTED', 'PRIVILEGE MOTIONS',
    'MINISTERIAL CONSULTATIVE COMMITTEE', 'PUBLIC SECURITY ORDINANCE',
    'ESSENTIAL PUBLIC SERVICES', 'RESOLUTION',
    # Sinhala
    'නිවේදන', 'ප්‍රශ්නවල', 'ලිඛිත', 'පපේශ',
    # Tamil
    'அறிவிப்புகள்', 'வினாக்கள்', 'மனுக்கள்',
]

SECTION_RE = re.compile(
    r'^(' + '|'.join(re.escape(k) for k in SECTION_KEYWORDS) + r')',
    re.IGNORECASE | re.MULTILINE
)


# ---------------------------------------------------------------------------
# TIMESTAMP DETECTION
# ---------------------------------------------------------------------------

# Preserve timestamps like [පූ.භා. 9.30] or [9.30 a.m.]
TIMESTAMP_RE = re.compile(
    r'[\[\(]'
    r'(පූ\.භා\.|ප\.ව\.|மு\.ப\.|பி\.ப\.|a\.m\.|p\.m\.)'
    r'\s*\d{1,2}[\.:]\d{2}'
    r'[\]\)]'
)


# ---------------------------------------------------------------------------
# CORE FUNCTIONS
# ---------------------------------------------------------------------------

def pdf_to_images(pdf_path: str, page_range: tuple = None, dpi: int = DPI):
    """Convert PDF pages to PIL Images."""
    kwargs = {"dpi": dpi, "fmt": "jpeg", "jpegopt": {"quality": 95}}
    if page_range:
        kwargs["first_page"] = page_range[0]
        kwargs["last_page"] = page_range[1]

    print(f"  Rendering PDF at {dpi} DPI...", flush=True)
    images = convert_from_path(pdf_path, **kwargs)
    print(f"  Got {len(images)} page image(s).")
    return images


def ocr_image(image: Image.Image, lang: str = DEFAULT_LANG, psm: int = PSM) -> str:
    """Run Tesseract OCR on a single page image."""
    config = f"--psm {psm} --oem 1"  # oem 1 = LSTM neural net engine
    return pytesseract.image_to_string(image, lang=lang, config=config)


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Light preprocessing to improve OCR accuracy.
    Converts to grayscale and increases contrast slightly.
    """
    import PIL.ImageOps
    import PIL.ImageFilter

    image = image.convert("L")           # Grayscale
    image = PIL.ImageOps.autocontrast(image, cutoff=1)  # Auto contrast
    # Mild sharpening helps with slightly blurry scans
    image = image.filter(PIL.ImageFilter.SHARPEN)
    return image


def clean_text(raw: str) -> str:
    """Strip noise patterns from raw OCR text."""
    lines = raw.splitlines()
    cleaned = []
    for line in lines:
        # Skip lines that are pure noise
        if NOISE_RE.search(line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def format_as_markdown(text: str, page_num: int) -> str:
    """
    Apply Markdown formatting:
    - Section titles → ## headers
    - Speaker lines → **bold**
    - Timestamps → preserved in [brackets]
    """
    lines = text.splitlines()
    output = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            output.append("")
            continue

        # Section headers
        if SECTION_RE.match(stripped) and len(stripped) < 80:
            output.append(f"\n## {stripped}\n")
            continue

        # Speaker lines — bold them
        if SPEAKER_RE.match(stripped):
            # Remove trailing colon if present, then re-add
            speaker = stripped.rstrip(":")
            output.append(f"\n**{speaker}:**")
            continue

        # Timestamps — keep as-is (already bracketed)
        output.append(line)

    return "\n".join(output)


def parse_page_range(s: str):
    """Parse '5-20' or '5' into (start, end) tuple."""
    if not s:
        return None
    parts = s.split("-")
    if len(parts) == 1:
        p = int(parts[0])
        return (p, p)
    return (int(parts[0]), int(parts[1]))


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

def process_hansard(pdf_path: str, output_path: str, lang: str, page_range=None):
    print(f"\n📄 Input:    {pdf_path}")
    print(f"📝 Output:   {output_path}")
    print(f"🌐 Language: {lang}")
    if page_range:
        print(f"📑 Pages:    {page_range[0]}–{page_range[1]}")
    print()

    # Step 1: Render PDF → images
    images = pdf_to_images(pdf_path, page_range=page_range)

    all_markdown = []
    all_markdown.append("# Parliamentary Debates — Hansard\n")
    all_markdown.append(f"*Source: {Path(pdf_path).name}*\n")
    all_markdown.append("---\n")

    for i, image in enumerate(images):
        page_num = (page_range[0] + i) if page_range else (i + 1)
        print(f"  OCR page {page_num}...", end=" ", flush=True)

        # Step 2: Preprocess
        processed = preprocess_image(image)

        # Step 3: OCR
        raw_text = ocr_image(processed, lang=lang)

        # Step 4: Clean noise
        clean = clean_text(raw_text)

        # Step 5: Format as Markdown
        md = format_as_markdown(clean, page_num)

        if md.strip():
            all_markdown.append(f"\n<!-- Page {page_num} -->\n")
            all_markdown.append(md)

        print("✓")

    # Step 6: Write output
    final = "\n".join(all_markdown)
    Path(output_path).write_text(final, encoding="utf-8")
    print(f"\n✅ Done! Markdown saved to: {output_path}")
    print(f"   Total characters: {len(final):,}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="OCR Sri Lankan Hansard PDF → Markdown using Tesseract"
    )
    parser.add_argument("input",  help="Path to input PDF")
    parser.add_argument("output", help="Path to output .md file")
    parser.add_argument(
        "--lang",
        default=DEFAULT_LANG,
        help=f"Tesseract language string (default: {DEFAULT_LANG}). "
        "Use 'eng' for English-only files."
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="Page range, e.g. '1-20' or '5'. Default: all pages."
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DPI,
        help=f"Rendering DPI (default: {DPI}). Use 400 for small/old print."
    )

    args = parser.parse_args()

    page_range = parse_page_range(args.pages)

    process_hansard(
        pdf_path=args.input,
        output_path=args.output,
        lang=args.lang,
        page_range=page_range,
    )


if __name__ == "__main__":
    main()
