from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEARCH_FILE = PROJECT_ROOT / "data" / "raw" / "companies_raw.csv"
TRADE_FILE = PROJECT_ROOT / "data" / "raw" / "trade_leads.csv"
COMBINED_FILE = PROJECT_ROOT / "data" / "raw" / "companies_raw.csv"


def classify_url(url: str, title: str) -> str:
    """Classify the URL/title into a result type based on heuristics."""
    url_lower = url.lower()
    title_lower = title.lower()

    # 1. MAP
    if "yandex" in url_lower and "maps" in url_lower:
        return "MAP"
    if "google" in url_lower and "maps" in url_lower:
        return "MAP"

    # 2. DIRECTORY
    directories = [
        "supl.biz", "optomtovar.ru", "productcenter.ru", "pulscen.ru", "yell.ru",
        "yp.ru", "spravker.ru", "2gis.ru", "trademo.com", "tradeimex.in",
        "exportgenius.in", "zauba.com", "seair.co.in", "marketinsidedata.com",
        "scribd.com", "mordorintelligence.com", "ite-expo.ru", "mosbuild.com"
    ]
    if any(d in url_lower for d in directories):
        return "DIRECTORY"
    if "каталог" in title_lower or "поставщики" in title_lower or "справочник" in title_lower:
        return "DIRECTORY"

    # 3. NEWS_ARTICLE
    news_domains = ["vc.ru", "tass.ru", "rbc.ru", "rg.ru", "cnews.ru", "kommersant.ru", "vedomosti.ru"]
    if any(n in url_lower for n in news_domains):
        return "NEWS_ARTICLE"
    if "новость" in title_lower or "статья" in title_lower or "обзор рынка" in title_lower:
        return "NEWS_ARTICLE"

    # 4. BLOG
    if "blog" in url_lower or "/blog/" in url_lower:
        return "BLOG"

    # 5. PRODUCT_PAGE
    path = url_lower.replace("https://", "").replace("http://", "").split("/")
    if len(path) > 2 and any(p in url_lower for p in ["product", "tovar", "catalog", "kollekciya", "shop"]):
        return "PRODUCT_PAGE"

    # 6. COMPANY
    if len(path) <= 2 or (len(path) == 3 and path[-1] == "") or "contact" in url_lower or "contacts" in url_lower:
        return "COMPANY"

    return "UNKNOWN"


def consolidate() -> None:
    unique_leads = {}

    # 1. Read existing search results if search file exists
    if SEARCH_FILE.exists():
        try:
            with SEARCH_FILE.open("r", newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    url = row.get("url_found", "").strip()
                    if not url:
                        continue

                    sources = [s.strip() for s in row.get("source", "").split(";")]
                    unique_leads[url] = {
                        "company_name": row.get("company_name", "").strip(),
                        "sources": set(sources),
                        "date_discovered": row.get("date_discovered", "").strip() or datetime.now().isoformat(timespec="seconds"),
                    }
        except Exception as e:
            print(f"Warning: Failed to read search file: {e}")

    # 2. Read manual trade leads
    trade_count = 0
    if TRADE_FILE.exists():
        try:
            with TRADE_FILE.open("r", newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    url = row.get("source_url", "").strip()
                    if not url:
                        continue

                    company_name = row.get("company_name", "").strip()
                    trade_source = f"Manual Trade Research | {row.get('source', '').strip()}"

                    if url in unique_leads:
                        unique_leads[url]["sources"].add(trade_source)
                        search_name = unique_leads[url]["company_name"]
                        if len(search_name) > len(company_name) + 15 or ":" in search_name:
                            unique_leads[url]["company_name"] = company_name
                    else:
                        unique_leads[url] = {
                            "company_name": company_name,
                            "sources": {trade_source},
                            "date_discovered": datetime.now().isoformat(timespec="seconds"),
                        }
                    trade_count += 1
        except Exception as e:
            print(f"Warning: Failed to read trade file: {e}")

    # 3. Classify and prepare rows
    combined_rows = []
    for url, data in unique_leads.items():
        sources_str = "; ".join(sorted(list(data["sources"])))
        res_type = classify_url(url, data["company_name"])
        combined_rows.append({
            "company_name": data["company_name"],
            "source": sources_str,
            "url_found": url,
            "date_discovered": data["date_discovered"],
            "result_type": res_type
        })

    # 4. Write combined dataset back to companies_raw.csv
    COLUMNS = ["company_name", "source", "url_found", "date_discovered", "result_type"]

    COMBINED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with COMBINED_FILE.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(combined_rows)

    print(f"Consolidation complete.")
    print(f"Read {trade_count} manual trade leads.")
    print(f"Saved {len(combined_rows)} unique consolidated candidate rows to {COMBINED_FILE}.")


if __name__ == "__main__":
    consolidate()
