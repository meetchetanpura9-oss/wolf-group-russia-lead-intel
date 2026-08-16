from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_FILE = RAW_DIR / "companies_raw.csv"

RAW_COLUMNS = [
    "company_name",
    "source",
    "url_found",
    "date_discovered",
]


def save_to_raw(
    company_name: str,
    source: str,
    url_found: str,
) -> None:
    """Save one discovered company to the raw CSV, avoiding duplicate URLs and appending sources."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    url_found = url_found.strip()
    source = source.strip()
    company_name = company_name.strip()

    rows = []
    url_exists = False
    file_exists = RAW_FILE.exists()

    if file_exists:
        try:
            with RAW_FILE.open("r", newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                if reader.fieldnames:
                    unique_rows = {}
                    for row in reader:
                        url = row.get("url_found")
                        if url:
                            if url in unique_rows:
                                existing_sources = [s.strip() for s in unique_rows[url].get("source", "").split(";")]
                                new_sources = [s.strip() for s in row.get("source", "").split(";")]
                                for s in new_sources:
                                    if s not in existing_sources:
                                        existing_sources.append(s)
                                unique_rows[url]["source"] = "; ".join(existing_sources)
                            else:
                                unique_rows[url] = row
                    
                    if url_found in unique_rows:
                        url_exists = True
                        existing_sources = [s.strip() for s in unique_rows[url_found].get("source", "").split(";")]
                        if source not in existing_sources:
                            existing_sources.append(source)
                            unique_rows[url_found]["source"] = "; ".join(existing_sources)
                    
                    rows = list(unique_rows.values())
        except Exception:
            pass

    if not url_exists:
        new_row = {
            "company_name": company_name,
            "source": source,
            "url_found": url_found,
            "date_discovered": datetime.now().isoformat(timespec="seconds"),
        }
        rows.append(new_row)

    with RAW_FILE.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=RAW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    print(f"Raw discovery file: {RAW_FILE}")
