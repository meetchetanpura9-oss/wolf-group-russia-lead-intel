from __future__ import annotations

import csv
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "data" / "cleaned" / "companies_cleaned.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "cleaned" / "companies_verified.csv"

GENERIC_DOMAINS = {
    "yandex.ru", "yandex.com", "google.com", "google.ru", "2gis.ru", "maps.yandex.ru",
    "supl.biz", "optomtovar.ru", "productcenter.ru", "pulscen.ru", "yell.ru", "yp.ru",
    "spravker.ru", "trademo.com", "tradeimex.in", "exportgenius.in", "zauba.com",
    "seair.co.in", "marketinsidedata.com", "scribd.com", "mordorintelligence.com",
    "ite-expo.ru", "mosbuild.com", "vk.com", "t.me", "instagram.com", "facebook.com",
    "linkedin.com", "youtube.com", "vc.ru", "tass.ru", "rbc.ru", "rg.ru", "cnews.ru",
    "kommersant.ru", "vedomosti.ru"
}

TILE_KEYWORDS = [
    "плитка", "керамогранит", "керамика", "кафель", "мозаика", "клинкер",
    "tile", "porcelain", "ceramic", "granite", "surfaces", "flooring", "slab", "clinker"
]

RUSSIA_KEYWORDS = [
    "россия", "москва", "петербург", "спб", "рф", "екатеринбург", "краснодар", "новосибирск",
    "russia", "moscow", "petersburg", "novosibirsk", "ekaterinburg", "krasnodar"
]


def check_relevance(text: str) -> tuple[str, str]:
    """Check text for tile and Russia keywords and return relevance values."""
    text_lower = text.lower()

    tile_relevant = "NO"
    if any(k in text_lower for k in TILE_KEYWORDS):
        tile_relevant = "YES"

    russia_relevant = "NO"
    if any(k in text_lower for k in RUSSIA_KEYWORDS):
        russia_relevant = "YES"

    return tile_relevant, russia_relevant


def verify_single_url(row: dict) -> dict:
    url = row.get("url_found", "").strip()
    result_type = row.get("result_type", "").strip()
    domain = row.get("domain_normalized", "").strip()

    # Pre-populate defaults
    verified_row = row.copy()
    verified_row.update({
        "website_status": "UNKNOWN",
        "page_title": "",
        "russia_relevant": "UNKNOWN",
        "tile_relevant": "UNKNOWN",
        "company_type": "UNKNOWN",
        "verification_status": "NEEDS_REVIEW",
        "verification_source": "Web Verification",
        "verification_date": datetime.now().strftime("%Y-%m-%d"),
        "data_confidence": "LOW",
        "verification_notes": ""
    })

    # 1. Filter out obvious directory/map/news listings
    if result_type in ["DIRECTORY", "MAP", "NEWS_ARTICLE", "BLOG"] or domain in GENERIC_DOMAINS:
        verified_row.update({
            "website_status": "ACTIVE",
            "company_type": "DIRECTORY" if result_type in ["DIRECTORY", "MAP"] else "UNKNOWN",
            "verification_status": "REJECTED",
            "data_confidence": "LOW",
            "verification_notes": f"Rejected: Auto-classified as {result_type} domain/listing."
        })

        # Check simple title relevance since we aren't fetching the URL
        tile_rel, russ_rel = check_relevance(row.get("company_name", ""))
        verified_row["tile_relevant"] = tile_rel
        verified_row["russia_relevant"] = russ_rel
        return verified_row

    if not url:
        verified_row.update({
            "website_status": "NOT_ACCESSIBLE",
            "verification_status": "REJECTED",
            "verification_notes": "Rejected: Missing website URL."
        })
        return verified_row

    # 2. Try fetching the webpage
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
        status_code = response.status_code

        if status_code >= 400:
            verified_row.update({
                "website_status": "BLOCKED" if status_code in [403, 401] else "NOT_ACCESSIBLE",
                "verification_status": "NEEDS_REVIEW",
                "verification_notes": f"HTTP {status_code} error returned."
            })
            return verified_row

        verified_row["website_status"] = "ACTIVE"

        # Parse HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract title
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        title = re.sub(r"\s+", " ", title)
        verified_row["page_title"] = title

        # Extract page text
        text_content = ""
        if soup.body:
            for script in soup(["script", "style"]):
                script.decompose()
            text_content = soup.body.get_text(separator=" ")
            text_content = re.sub(r"\s+", " ", text_content)

        # Combine title and body text for checks
        full_text = f"{row.get('company_name', '')} {title} {text_content}"

        tile_relevant, russia_relevant = check_relevance(full_text)

        # Domain-based Russia checks
        if domain.endswith(".ru") or domain.endswith(".su") or domain.endswith(".xn--p1ai"):
            russia_relevant = "YES"

        verified_row["tile_relevant"] = tile_relevant
        verified_row["russia_relevant"] = russia_relevant

        # Check classification status
        if tile_relevant == "YES" and russia_relevant == "YES":
            text_lower = full_text.lower()
            company_type = "UNKNOWN"
            if any(w in text_lower for w in ["дистрибьютор", "дистрибуция", "distributor"]):
                company_type = "DISTRIBUTOR"
            elif any(w in text_lower for w in ["импорт", "импортер", "importer"]):
                company_type = "IMPORTER"
            elif any(w in text_lower for w in ["опт", "оптом", "wholesaler", "wholesale"]):
                company_type = "WHOLESALER"
            elif any(w in text_lower for w in ["салон", "шоурум", "showroom"]):
                company_type = "SHOWROOM"
            elif any(w in text_lower for w in ["магазин", "розница", "retailer"]):
                company_type = "RETAILER"
            elif any(w in text_lower for w in ["застройщик", "строитель", "строительная", "developer", "construction"]):
                company_type = "CONSTRUCTION"
            elif any(w in text_lower for w in ["производитель", "завод", "фабрика", "manufacturer"]):
                company_type = "MANUFACTURER"
            else:
                company_type = "COMPANY"

            verified_row.update({
                "company_type": company_type,
                "verification_status": "VERIFIED",
                "data_confidence": "HIGH",
                "verification_notes": "Verified active site with matching tile and Russian relevance keywords."
            })
        else:
            verified_row.update({
                "verification_status": "NEEDS_REVIEW",
                "data_confidence": "MEDIUM",
                "verification_notes": f"Missing indicators. Tile: {tile_relevant}, Russia: {russia_relevant}."
            })

    except requests.RequestException as e:
        russia_rel = "YES" if (domain.endswith(".ru") or domain.endswith(".su") or domain.endswith(".xn--p1ai")) else "UNKNOWN"
        verified_row.update({
            "website_status": "NOT_ACCESSIBLE",
            "russia_relevant": russia_rel,
            "verification_status": "NEEDS_REVIEW",
            "data_confidence": "LOW",
            "verification_notes": f"Connection failed: {type(e).__name__}."
        })

    return verified_row


def main() -> None:
    if not INPUT_FILE.exists():
        print(f"Error: Input file does not exist: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)
    records = df.to_dict(orient="records")

    print(f"Starting website relevance and verification check for {len(records)} records...")

    verified_records = []

    # Run with a thread pool to perform network requests concurrently
    max_workers = 15
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(verify_single_url, r): r for r in records}

        completed_count = 0
        for future in as_completed(futures):
            res = future.result()
            verified_records.append(res)
            completed_count += 1
            if completed_count % 10 == 0 or completed_count == len(records):
                print(f"  Processed {completed_count}/{len(records)} sites...")

    # Save the verified output
    COLUMNS = [
        "company_name", "company_name_normalized", "source", "url_found",
        "url_normalized", "domain_normalized", "date_discovered", "result_type",
        "website_status", "page_title", "russia_relevant", "tile_relevant",
        "company_type", "verification_status", "verification_source",
        "verification_date", "data_confidence", "verification_notes"
    ]

    verified_df = pd.DataFrame(verified_records)
    verified_df = verified_df[COLUMNS]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    verified_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\nVerification complete.")
    print(f"Input rows: {len(df)}")
    print(f"Output rows: {len(verified_df)}")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nVerification Status Breakdown:")
    print(verified_df["verification_status"].value_counts())
    print("\nWebsite Status Breakdown:")
    print(verified_df["website_status"].value_counts())


if __name__ == "__main__":
    main()
