from __future__ import annotations

import csv
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "data" / "cleaned" / "companies_verified.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "cleaned" / "companies_with_contacts.csv"

# Target designations to search for in team/about sections
DESIGNATION_PATTERNS = [
    (r"(генеральный директор|гендиректор|директор|general director|ceo|руководитель)", "CEO / General Director"),
    (r"(коммерческий директор|commercial director)", "Commercial Director"),
    (r"(директор по закупкам|purchasing director|head of purchasing|руководитель отдела закупок)", "Purchasing Director"),
    (r"(менеджер по закупкам|закупки|purchasing manager|purchasing director)", "Purchasing Manager"),
    (r"(директор по импорту|руководитель вэд|вэд|import director|import manager)", "Import Director"),
    (r"(экспорт|export manager|export director)", "Export Manager"),
    (r"(директор по продажам|sales director|head of sales)", "Sales Director"),
    (r"(развитие бизнеса|business development|bdm)", "Business Development Manager")
]


def normalize_phone(phone_str: str) -> str:
    """Normalize a phone number to +7XXXXXXXXXX format if it's a Russian number, or keep it clean."""
    digits = re.sub(r"\D", "", phone_str)
    if not digits:
        return ""
    if len(digits) == 11:
        if digits.startswith("8") or digits.startswith("7"):
            return f"+7{digits[1:]}"
    elif len(digits) == 10:
        return f"+7{digits}"
    elif len(digits) > 11 and digits.startswith("7"):
        return f"+{digits}"
    return f"+{digits}"


def extract_contacts_from_text(text: str, url: str) -> dict:
    """Scan text and html content for email, phone, social, and whatsapp indicators."""
    results = {
        "emails": [],
        "phones": [],
        "whatsapp": [],
        "vk": [],
        "telegram": [],
        "linkedin": [],
        "decision_maker": None,
        "designation": None
    }

    # 1. Emails
    email_matches = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}", text)
    for email in email_matches:
        email = email.lower().strip()
        # Filter out obvious image/asset extension matches or invalid domains
        if not any(email.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]):
            if email not in results["emails"]:
                results["emails"].append(email)

    # 2. Phones & WhatsApp
    # Look for phone patterns
    phone_matches = re.findall(r"(?:\+7|7|8)(?:\s*\(?\d{3}\)?\s*\d{3}(?:\s*|-)\d{2}(?:\s*|-)\d{2}|\s*\d{3}\s*\d{3}\s*\d{4}|\s*\d{10})", text)
    for p in phone_matches:
        norm = normalize_phone(p)
        if norm and norm not in results["phones"]:
            results["phones"].append(norm)

    # 3. Decision Makers
    # Scan for designations and try to find nearby names (e.g. Ivan Petrov)
    text_lines = text.split("\n")
    for line in text_lines:
        line_clean = re.sub(r"\s+", " ", line).strip()
        for pattern, role in DESIGNATION_PATTERNS:
            match = re.search(pattern, line_clean, flags=re.IGNORECASE)
            if match:
                results["designation"] = role
                # Try finding a name nearby in this line (typically Capitalized words like "Иван Иванов")
                # Look for Capitalized Firstname Lastname
                name_match = re.search(r"([А-Я][а-я]+\s+[А-Я][а-я]+(?:\s+[А-Я][а-я]+)?)", line_clean)
                if not name_match:
                    # Try English name match
                    name_match = re.search(r"([A-Z][a-z]+\s+[A-Z][a-z]+)", line_clean)
                
                if name_match:
                    results["decision_maker"] = name_match.group(1)
                else:
                    results["decision_maker"] = "Unknown"
                break
        if results["decision_maker"]:
            break

    return results


def crawl_site_contacts(homepage_url: str) -> dict:
    """Crawl homepage and contact subpages of a website to gather contact details."""
    crawled_data = {
        "emails": [], "phones": [], "whatsapp": [],
        "vk": [], "telegram": [], "linkedin": [],
        "decision_maker": "Unknown", "designation": "",
        "email_source": "", "phone_source": "",
        "whatsapp_source": "", "decision_maker_source": "",
        "social_source": "", "contact_page_url": homepage_url
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    urls_to_visit = [homepage_url]
    visited_urls = set()

    # Step 1: Visit homepage to scrape contacts and find contact page links
    try:
        response = requests.get(homepage_url, headers=headers, timeout=6, allow_redirects=True)
        if response.status_code < 400:
            visited_urls.add(homepage_url)
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Scrape homepage text
            homepage_text = soup.get_text(separator="\n")
            contacts = extract_contacts_from_text(homepage_text, homepage_url)
            
            # Update crawled data
            for k in ["emails", "phones", "vk", "telegram", "linkedin"]:
                for item in contacts[k]:
                    if item not in crawled_data[k]:
                        crawled_data[k].append(item)
                        if not crawled_data[f"{k[:-1] if k.endswith('s') else k}_source"]:
                            crawled_data[f"{k[:-1] if k.endswith('s') else k}_source"] = homepage_url
                            
            if contacts["decision_maker"] and crawled_data["decision_maker"] == "Unknown":
                crawled_data["decision_maker"] = contacts["decision_maker"]
                crawled_data["designation"] = contacts["designation"]
                crawled_data["decision_maker_source"] = homepage_url

            # Scrape links to find about/contacts pages
            for link in soup.find_all("a", href=True):
                href = link["href"].strip()
                text = link.get_text().lower()
                full_link = urljoin(homepage_url, href)
                
                # Check link domain matches homepage domain
                if urlparse(full_link).netloc != urlparse(homepage_url).netloc:
                    # Scan for socials
                    href_lower = href.lower()
                    if "vk.com" in href_lower:
                        # Extract clean VK link
                        clean_vk = re.sub(r"\?.*$", "", full_link)
                        if clean_vk not in crawled_data["vk"]:
                            crawled_data["vk"].append(clean_vk)
                            crawled_data["social_source"] = homepage_url
                    elif "t.me" in href_lower:
                        clean_tg = re.sub(r"\?.*$", "", full_link)
                        if clean_tg not in crawled_data["telegram"]:
                            crawled_data["telegram"].append(clean_tg)
                            crawled_data["social_source"] = homepage_url
                    elif "linkedin.com" in href_lower:
                        clean_li = re.sub(r"\?.*$", "", full_link)
                        if clean_li not in crawled_data["linkedin"]:
                            crawled_data["linkedin"].append(clean_li)
                            crawled_data["social_source"] = homepage_url
                    continue
                
                # Check if it's a contact or about page link
                contact_match = any(k in href.lower() for k in ["contact", "about", "company", "team", "rekvizity", "kontakty", "personal"])
                text_match = any(k in text for k in ["контакт", "о компании", "руководство", "команда", "реквизиты", "о-нас", "about"])
                
                if (contact_match or text_match) and full_link not in visited_urls:
                    if len(urls_to_visit) < 4:  # limit to 3 subpages
                        urls_to_visit.append(full_link)

    except requests.RequestException:
        pass

    # Step 2: Visit discovered subpages
    for url in urls_to_visit[1:]:
        if url in visited_urls:
            continue
        try:
            response = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
            if response.status_code < 400:
                visited_urls.add(url)
                soup = BeautifulSoup(response.content, "html.parser")
                page_text = soup.get_text(separator="\n")
                
                contacts = extract_contacts_from_text(page_text, url)
                
                # Merge contacts
                for k in ["emails", "phones", "vk", "telegram", "linkedin"]:
                    for item in contacts[k]:
                        if item not in crawled_data[k]:
                            crawled_data[k].append(item)
                            # Set source to this subpage where it was first seen
                            if not crawled_data[f"{k[:-1] if k.endswith('s') else k}_source"]:
                                crawled_data[f"{k[:-1] if k.endswith('s') else k}_source"] = url
                                
                if contacts["decision_maker"] and crawled_data["decision_maker"] == "Unknown":
                    crawled_data["decision_maker"] = contacts["decision_maker"]
                    crawled_data["designation"] = contacts["designation"]
                    crawled_data["decision_maker_source"] = url
                
                # Scan a tags for whatsapp or socials on this subpage
                for link in soup.find_all("a", href=True):
                    href = link["href"].strip().lower()
                    full_link = urljoin(url, href)
                    if "wa.me/" in href or "api.whatsapp.com/send" in href:
                        # Extract phone number
                        match_num = re.search(r"(\d+)", href)
                        if match_num:
                            wa_num = f"+{match_num.group(1)}"
                            if wa_num not in crawled_data["whatsapp"]:
                                crawled_data["whatsapp"].append(wa_num)
                                crawled_data["whatsapp_source"] = url

        except requests.RequestException:
            pass

    return crawled_data


def process_verified_leads(row: dict) -> dict:
    verification_status = row.get("verification_status", "").strip()
    homepage_url = row.get("url_found", "").strip()
    
    # Pre-populate default empty contact fields
    contact_row = row.copy()
    contact_row.update({
        "business_email": "",
        "email_status": "UNKNOWN",
        "email_source_url": "",
        "business_phone": "",
        "phone_status": "UNKNOWN",
        "phone_source_url": "",
        "whatsapp": "",
        "whatsapp_status": "UNKNOWN",
        "whatsapp_source_url": "",
        "contact_person": "",
        "contact_person_status": "UNKNOWN",
        "designation": "",
        "decision_maker_source_url": "",
        "linkedin": "",
        "linkedin_status": "UNKNOWN",
        "vk": "",
        "vk_status": "UNKNOWN",
        "telegram": "",
        "telegram_status": "UNKNOWN",
        "social_source_url": "",
        "contact_quality_score": "LOW"
    })

    if verification_status != "VERIFIED":
        return contact_row

    # Crawl website for contacts
    crawled = crawl_site_contacts(homepage_url)

    # Update row with discovered values
    # Email
    if crawled["emails"]:
        contact_row["business_email"] = crawled["emails"][0]
        contact_row["email_status"] = "FOUND"
        contact_row["email_source_url"] = crawled["email_source"]
    else:
        contact_row["email_status"] = "NOT_FOUND"

    # Phone
    if crawled["phones"]:
        contact_row["business_phone"] = crawled["phones"][0]
        contact_row["phone_status"] = "FOUND"
        contact_row["phone_source_url"] = crawled["phone_source"]
    else:
        contact_row["phone_status"] = "NOT_FOUND"

    # WhatsApp
    if crawled["whatsapp"]:
        contact_row["whatsapp"] = crawled["whatsapp"][0]
        contact_row["whatsapp_status"] = "FOUND"
        contact_row["whatsapp_source_url"] = crawled["whatsapp_source"]
    else:
        contact_row["whatsapp_status"] = "NOT_FOUND"

    # Decision Maker
    if crawled["decision_maker"] and crawled["decision_maker"] != "Unknown":
        contact_row["contact_person"] = crawled["decision_maker"]
        contact_row["contact_person_status"] = "FOUND"
        contact_row["designation"] = crawled["designation"]
        contact_row["decision_maker_source_url"] = crawled["decision_maker_source"]
    else:
        contact_row["contact_person_status"] = "NOT_FOUND" if crawled["decision_maker"] == "Unknown" else "UNKNOWN"

    # Socials
    if crawled["linkedin"]:
        contact_row["linkedin"] = crawled["linkedin"][0]
        contact_row["linkedin_status"] = "FOUND"
        contact_row["social_source_url"] = crawled["social_source"] or homepage_url
    else:
        contact_row["linkedin_status"] = "NOT_FOUND"

    if crawled["vk"]:
        contact_row["vk"] = crawled["vk"][0]
        contact_row["vk_status"] = "FOUND"
        contact_row["social_source_url"] = crawled["social_source"] or homepage_url
    else:
        contact_row["vk_status"] = "NOT_FOUND"

    if crawled["telegram"]:
        contact_row["telegram"] = crawled["telegram"][0]
        contact_row["telegram_status"] = "FOUND"
        contact_row["social_source_url"] = crawled["social_source"] or homepage_url
    else:
        contact_row["telegram_status"] = "NOT_FOUND"

    # Contact Quality Scoring
    has_email = contact_row["email_status"] == "FOUND"
    has_phone = contact_row["phone_status"] == "FOUND"
    has_dm = contact_row["contact_person_status"] == "FOUND"
    
    # We define quality
    if has_email and has_phone and has_dm:
        contact_row["contact_quality_score"] = "HIGH"
    elif has_email or has_phone:
        contact_row["contact_quality_score"] = "MEDIUM"
    else:
        contact_row["contact_quality_score"] = "LOW"

    return contact_row


def main() -> None:
    if not INPUT_FILE.exists():
        print(f"Error: Input file does not exist: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)
    records = df.to_dict(orient="records")

    # Filter verified companies
    verified_records = [r for r in records if r.get("verification_status") == "VERIFIED"]
    other_records = [r for r in records if r.get("verification_status") != "VERIFIED"]

    print(f"Loaded {len(records)} companies.")
    print(f"Starting Contact Intelligence collection for {len(verified_records)} VERIFIED companies...")

    processed_records = []
    max_workers = 10
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_verified_leads, r): r for r in verified_records}
        
        completed_count = 0
        for future in as_completed(futures):
            res = future.result()
            processed_records.append(res)
            completed_count += 1
            if completed_count % 5 == 0 or completed_count == len(verified_records):
                print(f"  Processed {completed_count}/{len(verified_records)} verified targets...")

    # Re-merge other non-verified records to preserve the intermediate layers
    for r in other_records:
        empty_contact = r.copy()
        empty_contact.update({
            "business_email": "", "email_status": "UNKNOWN", "email_source_url": "",
            "business_phone": "", "phone_status": "UNKNOWN", "phone_source_url": "",
            "whatsapp": "", "whatsapp_status": "UNKNOWN", "whatsapp_source_url": "",
            "contact_person": "", "contact_person_status": "UNKNOWN", "designation": "",
            "decision_maker_source_url": "", "linkedin": "", "linkedin_status": "UNKNOWN",
            "vk": "", "vk_status": "UNKNOWN", "telegram": "", "telegram_status": "UNKNOWN",
            "social_source_url": "", "contact_quality_score": "LOW"
        })
        processed_records.append(empty_contact)

    # Columns configuration
    COLUMNS = [
        "company_name", "company_name_normalized", "source", "url_found",
        "url_normalized", "domain_normalized", "date_discovered", "result_type",
        "website_status", "page_title", "russia_relevant", "tile_relevant",
        "company_type", "verification_status", "verification_source",
        "verification_date", "data_confidence", "verification_notes",
        "business_email", "email_status", "email_source_url",
        "business_phone", "phone_status", "phone_source_url",
        "whatsapp", "whatsapp_status", "whatsapp_source_url",
        "contact_person", "contact_person_status", "designation", "decision_maker_source_url",
        "linkedin", "linkedin_status", "vk", "vk_status", "telegram", "telegram_status",
        "social_source_url", "contact_quality_score"
    ]

    output_df = pd.DataFrame(processed_records)
    output_df = output_df[COLUMNS]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\nContact Intelligence collection complete.")
    print(f"Saved {len(output_df)} rows to: {OUTPUT_FILE}")
    print("\nContact Quality Score Distribution:")
    print(output_df[output_df["verification_status"] == "VERIFIED"]["contact_quality_score"].value_counts())


if __name__ == "__main__":
    main()
