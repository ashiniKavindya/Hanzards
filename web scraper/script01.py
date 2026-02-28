import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "https://www.parliament.lk/en/business-of-parliament/hansards"

HEADERS = {
    "User-Agent": "CS3121-Research-Bot/1.0 (University Academic Research)"
}


def get_pdf_links(page=1):
    url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
    print(f"\n[STAGE 1] Checking page {page}: {url}")

    try:
        print("[STAGE 2] Sending request to server...")
        start_time = time.time()
        response = requests.get(url, headers=HEADERS, timeout=10)
        elapsed = time.time() - start_time
        print(f"[STAGE 3] Response received in {elapsed:.2f} seconds")
        print(f"[STAGE 4] HTTP Status Code: {response.status_code}")
        response.raise_for_status()

        print(
            f"[STAGE 5] Parsing HTML content (size: {len(response.text)} bytes)...")
        soup = BeautifulSoup(response.text, "html.parser")
        print(f"[STAGE 6] HTML parsed successfully")

        all_links = soup.find_all("a", href=True)
        print(f"[STAGE 7] Found {len(all_links)} total links on page")

        pdf_links = []
        for idx, a in enumerate(all_links):
            href = a["href"]

            # strict filtering
            if "/uploads/businessdocs/" in href and href.endswith(".pdf"):
                pdf_links.append(href)
                print(f"  - Found PDF #{len(pdf_links)}: {href}")

        print(
            f"[STAGE 8] Filtering complete. PDF links found: {len(pdf_links)}")
        return pdf_links

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request failed: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return []


if __name__ == "__main__":
    print("=" * 60)
    print("Starting Parliament Hansards PDF Scraper")
    print("=" * 60)

    pdf_links = get_pdf_links(1)

    print("\n" + "=" * 60)
    print(f"FINAL RESULT: Total PDFs found on page 1: {len(pdf_links)}")
    print("=" * 60)

    if pdf_links:
        print("\nFirst 5 PDF links:")
        for i, link in enumerate(pdf_links[:5], 1):
            print(f"{i}. {link}")
    else:
        print("\n[WARNING] No PDF links found!")

    print("\nScraping complete.")
