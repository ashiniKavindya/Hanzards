"""
Hansard Batch OCR Pipeline
==========================
Reads PDF paths from hansards.csv, runs Tesseract OCR on each,
saves Markdown output to a separate folder, and writes the output
path back into the CSV.

USAGE
-----
    python ocr_pipeline.py

    # Process only specific languages:
    python ocr_pipeline.py --lang eng
    python ocr_pipeline.py --lang sin+tam+eng

    # Limit pages per PDF (useful for testing):
    python ocr_pipeline.py --pages 1-5

    # Use a different CSV:
    python ocr_pipeline.py --csv "web scraper/hansards.csv"

WINDOWS — run these first in the same PowerShell session:
    $env:Path = "C:\\Program Files\\Tesseract-OCR;C:\\Users\\SAMPR\\AppData\\Local\\Microsoft\\WinGet\\Packages\\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\\poppler-25.07.0\\Library\\bin;" + $env:Path
    $env:TESSDATA_PREFIX = "c:\\Users\\SAMPR\\OneDrive\\Desktop\\GitHub Projects\\Hanzards\\teseract ocr\\.tessdata"
    python ocr_pipeline.py
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import pandas as pd
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    import PIL.ImageOps
    import PIL.ImageFilter
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install pytesseract pdf2image Pillow pandas")
    sys.exit(1)


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
CSV_PATH = SCRIPT_DIR / "web scraper" / "hansards.csv"
OUTPUT_DIR = SCRIPT_DIR / "teseract ocr" / "ocr_output"

# ---------------------------------------------------------------------------
# OCR CONFIG
# ---------------------------------------------------------------------------

DEFAULT_LANG = "sin+tam+eng"
DPI = 300
PSM = 1   # Auto page segmentation with OSD — handles multi-column layouts


# ---------------------------------------------------------------------------
# NOISE / FORMATTING PATTERNS  (same as tesaract_conversion_script_v2.py)
# ---------------------------------------------------------------------------

NOISE_PATTERNS = [
    r'^\s*\d{3,4}\s*$',
    r'PARLIAMENTARY\s+DEBATES',
    r'^\s*HANSARD\s*$',
    r'\(HANSARD\)',
    r'හැන්සාඩ්',
    r'ஹன்சாட்',
    r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+\d+\w+\s+\w+,\s+\d{4}\s*$',
    r'^(திங்கள்|செவ்வாய்|புதன்|வியாழன்|வெள்ளி|சனி|ஞாயிறு),\s',
    r'^(සඳුදා|අඟහරුවාදා|බදාදා|බ්‍රහස්පතින්දා|සිකුරාදා|සෙනසුරාදා|ඉරිදා),\s',
    r'OFFICIAL\s+REPORT',
    r'Volume\s+\d+\s*-\s*No\.\s*\d+',
]
NOISE_RE = re.compile('|'.join(NOISE_PATTERNS), re.MULTILINE | re.IGNORECASE)

SPEAKER_PATTERNS = [
    r'^(The\s+Hon\.|Hon\.|MR\.|MRS\.|MS\.|DR\.|GEN\.|LT\.)',
    r'^(ගරු|ගු\.?)\s+',
    r'^மாண்புமிகு\s+',
    r'^(MR\.\s+SPEAKER|THE\s+SPEAKER|ගු කථානායකුරමා|செொநொயகர்)',
]
SPEAKER_RE = re.compile('|'.join(SPEAKER_PATTERNS), re.MULTILINE)

SECTION_KEYWORDS = [
    'ANNOUNCEMENTS', 'ORAL ANSWERS TO QUESTIONS', 'WRITTEN ANSWERS TO QUESTIONS',
    'QUESTIONS', 'PETITIONS', 'PAPERS PRESENTED', 'PRIVILEGE MOTIONS',
    'MINISTERIAL CONSULTATIVE COMMITTEE', 'PUBLIC SECURITY ORDINANCE',
    'ESSENTIAL PUBLIC SERVICES', 'RESOLUTION',
    'නිවේදන', 'ප්‍රශ්නවල', 'ලිඛිත', 'පපේශ',
    'அறிவிப்புகள்', 'வினாக்கள்', 'மனுக்கள்',
]
SECTION_RE = re.compile(
    r'^(' + '|'.join(re.escape(k) for k in SECTION_KEYWORDS) + r')',
    re.IGNORECASE | re.MULTILINE
)


# ---------------------------------------------------------------------------
# OCR HELPERS
# ---------------------------------------------------------------------------

def pdf_to_images(pdf_path: str, page_range=None, dpi: int = DPI):
    kwargs = {"dpi": dpi, "fmt": "jpeg", "jpegopt": {"quality": 95}}
    if page_range:
        kwargs["first_page"] = page_range[0]
        kwargs["last_page"] = page_range[1]
    return convert_from_path(pdf_path, **kwargs)


def preprocess_image(image: Image.Image) -> Image.Image:
    image = image.convert("L")
    image = PIL.ImageOps.autocontrast(image, cutoff=1)
    image = image.filter(PIL.ImageFilter.SHARPEN)
    return image


def ocr_image(image: Image.Image, lang: str, psm: int = PSM) -> str:
    config = f"--psm {psm} --oem 1"
    return pytesseract.image_to_string(image, lang=lang, config=config)


def clean_text(raw: str) -> str:
    lines = raw.splitlines()
    return "\n".join(line for line in lines if not NOISE_RE.search(line))


def format_as_markdown(text: str) -> str:
    lines = text.splitlines()
    output = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            output.append("")
            continue
        if SECTION_RE.match(stripped) and len(stripped) < 80:
            output.append(f"\n## {stripped}\n")
            continue
        if SPEAKER_RE.match(stripped):
            output.append(f"\n**{stripped.rstrip(':')}:**")
            continue
        output.append(line)
    return "\n".join(output)


def parse_page_range(s: str):
    if not s:
        return None
    parts = s.split("-")
    if len(parts) == 1:
        p = int(parts[0])
        return (p, p)
    return (int(parts[0]), int(parts[1]))


# ---------------------------------------------------------------------------
# SINGLE PDF → MARKDOWN
# ---------------------------------------------------------------------------

def process_pdf(pdf_path: str, output_path: str, lang: str, page_range=None, dpi: int = DPI):
    images = pdf_to_images(pdf_path, page_range=page_range, dpi=dpi)

    all_md = [
        "# Parliamentary Debates — Hansard\n",
        f"*Source: {Path(pdf_path).name}*\n",
        "---\n",
    ]

    for i, image in enumerate(images):
        page_num = (page_range[0] + i) if page_range else (i + 1)
        print(f"    page {page_num}...", end=" ", flush=True)

        processed = preprocess_image(image)
        raw = ocr_image(processed, lang=lang)
        clean = clean_text(raw)
        md = format_as_markdown(clean)

        if md.strip():
            all_md.append(f"\n<!-- Page {page_num} -->\n")
            all_md.append(md)

        print("✓", flush=True)

    final = "\n".join(all_md)
    Path(output_path).write_text(final, encoding="utf-8")
    return final


# ---------------------------------------------------------------------------
# BATCH PIPELINE
# ---------------------------------------------------------------------------

def run_batch(csv_path: Path, output_dir: Path, lang: str, page_range=None, dpi: int = DPI):
    if not csv_path.exists():
        print(f"[ERROR] CSV not found: {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path)

    # Add ocr_path column if it doesn't exist
    if "ocr_path" not in df.columns:
        df["ocr_path"] = None

    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(df)
    skipped = 0
    processed = 0
    failed = 0

    sep = "=" * 60
    print(f"\n{sep}")
    print("  Hansard Batch OCR Pipeline")
    print(sep)
    print(f"  CSV:        {csv_path}")
    print(f"  Output dir: {output_dir}")
    print(f"  Language:   {lang}")
    print(f"  PSM:        {PSM} (multi-column OSD)")
    print(f"  DPI:        {dpi}")
    print(f"  Total rows: {total}")
    print(f"{sep}\n")

    for count, (idx, row) in enumerate(df.iterrows(), start=1):
        pdf_path = row.get("local_path")
        filename = row.get("filename", f"row_{idx}.pdf")

        # Already processed — skip
        existing_ocr = row.get("ocr_path")
        if pd.notna(existing_ocr) and Path(str(existing_ocr)).exists():
            print(f"  [{count}/{total}] SKIP (already done): {filename}")
            skipped += 1
            continue

        # No local PDF available
        if pd.isna(pdf_path) or not Path(str(pdf_path)).exists():
            print(f"  [{count}/{total}] SKIP (PDF not found): {filename}")
            skipped += 1
            continue

        # Derive output .md path
        stem = Path(filename).stem
        md_path = output_dir / f"{stem}.md"

        print(f"  [{count}/{total}] OCR: {filename}")
        try:
            process_pdf(str(pdf_path), str(md_path),
                        lang=lang, page_range=page_range, dpi=dpi)
            char_count = md_path.stat().st_size
            print(f"    → Saved: {md_path.name} ({char_count:,} bytes)")
            df.at[idx, "ocr_path"] = str(md_path)
            processed += 1
        except (OSError, RuntimeError, ValueError) as e:
            print(f"    → FAILED: {e}")
            failed += 1

        # Save CSV after every file so progress is not lost
        df.to_csv(csv_path, index=False)

    print(f"\n{sep}")
    print(
        f"  Done.  Processed: {processed}  Skipped: {skipped}  Failed: {failed}")
    print(f"  CSV updated: {csv_path}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Batch OCR all Hansard PDFs listed in hansards.csv"
    )
    parser.add_argument(
        "--csv",
        default=str(CSV_PATH),
        help=f"Path to hansards.csv (default: {CSV_PATH})"
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help=f"Folder for .md output files (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--lang",
        default=DEFAULT_LANG,
        help=f"Tesseract language string (default: {DEFAULT_LANG})"
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="Page range per PDF, e.g. '1-20' or '5'. Default: all pages."
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DPI,
        help=f"Rendering DPI (default: {DPI})"
    )

    args = parser.parse_args()

    run_batch(
        csv_path=Path(args.csv),
        output_dir=Path(args.output_dir),
        lang=args.lang,
        page_range=parse_page_range(args.pages),
        dpi=args.dpi,
    )


if __name__ == "__main__":
    main()
