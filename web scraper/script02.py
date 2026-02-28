import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os

BASE_URL = "https://www.parliament.lk/en/business-of-parliament/hansards"

HEADERS = {
    "User-Agent": "CS3121-Research-Bot/1.0 (University of Moratuwa Academic Project)"
}

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "downloads")


def extract_date_from_url(url):
    """Extract date from PDF filename e.g. 23270_english_2026-02-06.pdf -> 2026-02-06"""
    match = re.search(r"(\d{4}-\d{2}-\d{2})", url)
    return match.group(1) if match else None


def extract_language_from_url(url):
    """Extract language from PDF filename e.g. english, sinhala, tamil"""
    match = re.search(r"\d+_(\w+)_\d{4}-\d{2}-\d{2}\.pdf", url)
    return match.group(1) if match else None


def download_pdf(url, folder):
    """Download a PDF to the given folder. Returns local file path."""
    os.makedirs(folder, exist_ok=True)
    filename = url.split("/")[-1]
    local_path = os.path.join(folder, filename)

    if os.path.exists(local_path):
        print(f"    [SKIP] Already downloaded: {filename}")
        return local_path

    print(f"    [DOWNLOADING] {filename} ...", end=" ", flush=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(r.content)
        size_kb = len(r.content) / 1024
        print(f"done ({size_kb:.1f} KB)")
        time.sleep(1)  # polite delay
        return local_path
    except Exception as e:
        print(f"FAILED ({e})")
        return None


def get_pdf_links_from_page(page):
    url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
    print(f"\n  [Page {page}] Fetching: {url}")

    try:
        start_time = time.time()
        response = requests.get(url, headers=HEADERS, timeout=15)
        elapsed = time.time() - start_time
        print(
            f"  [Page {page}] Response: HTTP {response.status_code} in {elapsed:.2f}s")
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        all_links = soup.find_all("a", href=True)

        results = []
        for a in all_links:
            href = a["href"]
            if "/uploads/businessdocs/" in href and href.endswith(".pdf"):
                date = extract_date_from_url(href)
                language = extract_language_from_url(href)
                filename = href.split("/")[-1]
                results.append({
                    "filename": filename,
                    "date": date,
                    "language": language,
                    "page_scraped": page,
                    "url": href,
                    "local_path": None,
                })

        print(f"  [Page {page}] Found {len(results)} PDF(s)")
        return results

    except requests.exceptions.RequestException as e:
        print(f"  [Page {page}] ERROR: {e}")
        return []


def get_page_input(prompt, default):
    while True:
        try:
            value = input(prompt).strip()
            return int(value) if value else default
        except ValueError:
            print("  Please enter a valid integer.")


if __name__ == "__main__":
    print("=" * 60)
    print("  Parliament Hansards PDF Scraper")
    print("=" * 60)

    start_page = get_page_input("Enter start page [default: 1]: ", 1)
    end_page = get_page_input(
        f"Enter end page   [default: {start_page}]: ", start_page)

    if start_page > end_page:
        start_page, end_page = end_page, start_page
        print(f"  (Swapped to range: {start_page} - {end_page})")

    print(f"\nScraping pages {start_page} to {end_page}...")
    print("-" * 60)

    all_records = []
    for page in range(start_page, end_page + 1):
        records = get_pdf_links_from_page(page)
        all_records.extend(records)
        if page < end_page:
            time.sleep(0.5)

    print("\n" + "=" * 60)
    print(f"Total PDFs found: {len(all_records)}")
    print("=" * 60)

    if not all_records:
        print("\n[WARNING] No PDFs found. Exiting.")
    else:
        print(f"\nDownloading PDFs to: {DOWNLOAD_FOLDER}")
        print("-" * 60)

        for record in all_records:
            local_path = download_pdf(record["url"], DOWNLOAD_FOLDER)
            record["local_path"] = local_path

        df = pd.DataFrame(all_records)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date", ascending=False).reset_index(drop=True)

        print("\nPreview (first 10 rows):")
        print(df[["date", "language", "filename", "local_path"]].head(
            10).to_string(index=False))

        output_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(output_dir, "hansards.csv")
        df.to_csv(csv_path, index=False)

        downloaded = df["local_path"].notna().sum()
        print(f"\n[SAVED] CSV -> {csv_path}")
        print(
            f"        Rows: {len(df)} | Downloaded: {downloaded} | Failed: {len(df) - downloaded}")

    print("\nScraping complete.")

    # Save to CSV
    output_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(output_dir, "hansards.csv")
    df.to_csv(csv_path, index=False)
    print(f"\n[SAVED] CSV -> {csv_path}")
    print(f"        Rows: {len(df)} | Columns: {list(df.columns)}")

    print("\nScraping complete.")
