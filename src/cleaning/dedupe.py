from __future__ import annotations

import csv
from pathlib import Path
import pandas as pd
from rapidfuzz import fuzz

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "data" / "cleaned" / "companies_normalized.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "cleaned" / "companies_cleaned.csv"
REVIEW_FILE = PROJECT_ROOT / "data" / "cleaned" / "duplicate_review.csv"

GENERIC_DOMAINS = {
    "yandex.ru", "yandex.com", "google.com", "google.ru", "2gis.ru", "maps.yandex.ru",
    "supl.biz", "optomtovar.ru", "productcenter.ru", "pulscen.ru", "yell.ru", "yp.ru",
    "spravker.ru", "trademo.com", "tradeimex.in", "exportgenius.in", "zauba.com",
    "seair.co.in", "marketinsidedata.com", "scribd.com", "mordorintelligence.com",
    "ite-expo.ru", "mosbuild.com", "vk.com", "t.me", "instagram.com", "facebook.com",
    "linkedin.com", "youtube.com", "vc.ru", "tass.ru", "rbc.ru", "rg.ru", "cnews.ru",
    "kommersant.ru", "vedomosti.ru"
}


def merge_records(rec1: dict, rec2: dict) -> dict:
    """Merge two candidate records into one, combining sources and metadata."""
    # Combine sources
    sources1 = [s.strip() for s in rec1.get("source", "").split(";")]
    sources2 = [s.strip() for s in rec2.get("source", "").split(";")]
    combined_sources = sorted(list(set(sources1 + sources2)))

    # Choose cleanest company name (shortest non-empty or preferred)
    name1 = rec1.get("company_name", "").strip()
    name2 = rec2.get("company_name", "").strip()
    is_manual1 = "Manual" in rec1.get("source", "")
    is_manual2 = "Manual" in rec2.get("source", "")

    if is_manual1 and not is_manual2:
        chosen_name = name1
    elif is_manual2 and not is_manual1:
        chosen_name = name2
    else:
        if ":" in name1 and ":" not in name2:
            chosen_name = name2
        elif ":" in name2 and ":" not in name1:
            chosen_name = name1
        else:
            chosen_name = name1 if len(name1) <= len(name2) else name2

    # Choose earliest date
    date1 = rec1.get("date_discovered", "")
    date2 = rec2.get("date_discovered", "")
    chosen_date = min(date1, date2) if date1 and date2 else (date1 or date2)

    # Result type preference: COMPANY > others
    type1 = rec1.get("result_type", "")
    type2 = rec2.get("result_type", "")
    if type1 == "COMPANY":
        chosen_type = "COMPANY"
    elif type2 == "COMPANY":
        chosen_type = "COMPANY"
    else:
        chosen_type = type1 or type2

    # Choose URL: prefer the one that is not generic or just URL 1
    url1 = rec1.get("url_found", "")
    url2 = rec2.get("url_found", "")
    domain1 = rec1.get("domain_normalized", "")
    domain2 = rec2.get("domain_normalized", "")
    is_generic1 = domain1 in GENERIC_DOMAINS
    is_generic2 = domain2 in GENERIC_DOMAINS

    if is_generic1 and not is_generic2:
        chosen_url = url2
        chosen_url_norm = rec2.get("url_normalized", "")
        chosen_domain = domain2
    else:
        chosen_url = url1
        chosen_url_norm = rec1.get("url_normalized", "")
        chosen_domain = domain1

    return {
        "company_name": chosen_name,
        "company_name_normalized": rec1.get("company_name_normalized", ""),
        "source": "; ".join(combined_sources),
        "url_found": chosen_url,
        "url_normalized": chosen_url_norm,
        "domain_normalized": chosen_domain,
        "date_discovered": chosen_date,
        "result_type": chosen_type
    }


def main() -> None:
    if not INPUT_FILE.exists():
        print(f"Error: Input file does not exist: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)
    records = df.to_dict(orient="records")

    print(f"Starting deduplication of {len(records)} records...")

    # Pass 1: Deduplicate by exact URL
    url_groups = {}
    for r in records:
        url = r.get("url_normalized", "")
        if url:
            url_groups.setdefault(url, []).append(r)
        else:
            url_groups.setdefault(r.get("url_found", ""), []).append(r)

    records_after_pass1 = []
    for group in url_groups.values():
        merged = group[0]
        for item in group[1:]:
            merged = merge_records(merged, item)
        records_after_pass1.append(merged)

    print(f"Pass 1 (Exact URL) completed: {len(records_after_pass1)} active records remaining.")

    # Pass 2: Deduplicate by non-generic domain
    domain_groups = {}
    remaining_records = []
    for r in records_after_pass1:
        domain = r.get("domain_normalized", "")
        if domain and domain not in GENERIC_DOMAINS:
            domain_groups.setdefault(domain, []).append(r)
        else:
            remaining_records.append(r)

    records_after_pass2 = []
    for domain, group in domain_groups.items():
        merged = group[0]
        for item in group[1:]:
            merged = merge_records(merged, item)
        records_after_pass2.append(merged)

    records_after_pass2.extend(remaining_records)
    print(f"Pass 2 (Domain) completed: {len(records_after_pass2)} active records remaining.")

    # Pass 3: Deduplicate by exact normalized company name
    name_groups = {}
    remaining_records = []
    for r in records_after_pass2:
        name = r.get("company_name_normalized", "")
        if name:
            name_groups.setdefault(name, []).append(r)
        else:
            remaining_records.append(r)

    records_after_pass3 = []
    for name, group in name_groups.items():
        merged = group[0]
        for item in group[1:]:
            merged = merge_records(merged, item)
        records_after_pass3.append(merged)

    records_after_pass3.extend(remaining_records)
    print(f"Pass 3 (Exact Name) completed: {len(records_after_pass3)} active records remaining.")

    # Pass 4: Fuzzy Matching with RapidFuzz
    final_records = list(records_after_pass3)
    review_rows = []
    merged_indices = set()

    i = 0
    while i < len(final_records):
        if i in merged_indices:
            i += 1
            continue

        name_i = final_records[i].get("company_name_normalized", "")
        if not name_i:
            i += 1
            continue

        j = i + 1
        while j < len(final_records):
            if j in merged_indices:
                j += 1
                continue

            name_j = final_records[j].get("company_name_normalized", "")
            if not name_j:
                j += 1
                continue

            score = fuzz.token_sort_ratio(name_i, name_j)

            if score >= 92:
                print(f"Auto-merging duplicates (Score: {score:.0f}):")
                print(f"  1. {final_records[i]['company_name']} ({final_records[i]['url_found']})")
                print(f"  2. {final_records[j]['company_name']} ({final_records[j]['url_found']})")
                final_records[i] = merge_records(final_records[i], final_records[j])
                merged_indices.add(j)
            elif score >= 80:
                review_rows.append({
                    "company_name_1": final_records[i]["company_name"],
                    "url_1": final_records[i]["url_found"],
                    "domain_1": final_records[i]["domain_normalized"],
                    "company_name_2": final_records[j]["company_name"],
                    "url_2": final_records[j]["url_found"],
                    "domain_2": final_records[j]["domain_normalized"],
                    "similarity_score": round(score, 1),
                    "status": "PENDING"
                })

            j += 1
        i += 1

    deduplicated_records = [r for idx, r in enumerate(final_records) if idx not in merged_indices]

    # Save outputs
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(deduplicated_records).to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    review_df = pd.DataFrame(review_rows)
    if review_df.empty:
        review_df = pd.DataFrame(columns=[
            "company_name_1", "url_1", "domain_1",
            "company_name_2", "url_2", "domain_2",
            "similarity_score", "status"
        ])
    review_df.to_csv(REVIEW_FILE, index=False, encoding="utf-8-sig")

    print(f"\nDeduplication complete.")
    print(f"Active records saved to: {OUTPUT_FILE} ({len(deduplicated_records)} rows)")
    print(f"Ambiguous cases saved to: {REVIEW_FILE} ({len(review_rows)} rows)")


if __name__ == "__main__":
    main()
