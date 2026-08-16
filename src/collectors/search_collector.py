from __future__ import annotations

import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from utils import save_to_raw

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
if SERPAPI_API_KEY is None:
    raise ValueError("SERPAPI_API_KEY is missing from .env")

SEARCH_URL = "https://serpapi.com/search"

# Full list of search queries for raw discovery
SEARCH_QUERIES = [
    # Russian searches
    "керамогранит импортер Россия",
    "керамическая плитка импортер Россия",
    "керамогранит дистрибьютор Россия",
    "керамическая плитка дистрибьютор Россия",
    "плитка оптовая компания Россия",
    "плитка импортер Москва",
    "керамогранит оптом Москва",
    "керамическая плитка оптом Санкт-Петербург",
    "импортер плитки Россия",
    "дистрибьютор плитки Россия",
    # English searches
    "tile importer Russia",
    "ceramic tile importer Russia",
    "porcelain tile importer Russia",
    "tile distributor Russia",
    "ceramic tile wholesaler Russia",
    "porcelain tile wholesaler Moscow",
]


def run_search(query: str) -> list[dict[str, str]]:
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "num": 10,
        "hl": "en",
        "gl": "ru",
    }

    response = requests.get(
        SEARCH_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    results = []

    for item in data.get("organic_results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
            }
        )

    return results


def main() -> None:
    total_results = 0

    try:
        for query in SEARCH_QUERIES:
            print(f"\nSearching: {query}")

            try:
                results = run_search(query)

                print(f"Results returned: {len(results)}")

                for result in results:
                    title = result.get("title", "")
                    url = result.get("url", "")

                    if not url:
                        continue

                    print(f"  {title}")
                    print(f"  {url}")

                    save_to_raw(
                        company_name=title,
                        source=f"SerpApi | {query}",
                        url_found=url,
                    )

                    total_results += 1

                # Keep requests gentle and avoid unnecessary bursts.
                time.sleep(1)

            except requests.RequestException as exc:
                print(f"Search failed: {exc}")
                continue

            except Exception as exc:
                print(f"Unexpected error for query '{query}': {exc}")
                continue

    except KeyboardInterrupt:
        print("\nCollection interrupted by user. Saved results will remain in the raw CSV.")
        print(f"Results already saved: {total_results}")

    finally:
        print(
            f"\nDiscovery complete. "
            f"Raw results saved: {total_results}"
        )


if __name__ == "__main__":
    main()
