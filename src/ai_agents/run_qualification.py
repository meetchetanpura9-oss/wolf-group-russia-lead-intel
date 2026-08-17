from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
import pandas as pd

# Add the current directory to sys.path to allow importing qualifier
sys.path.append(str(Path(__file__).resolve().parent))

from qualifier import qualify_company, clean_value

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "data" / "cleaned" / "companies_with_contacts.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "final" / "qualified_leads.csv"


def load_existing_results() -> dict:
    """Load existing results to enable resume capability."""
    if not OUTPUT_FILE.exists():
        return {}

    try:
        df = pd.read_csv(OUTPUT_FILE, dtype=str)
        # Map company name to its parsed row dict
        return {row["company_name"]: row.to_dict() for _, row in df.iterrows()}
    except Exception as e:
        print(f"Warning: Could not load existing output file ({e}). Starting fresh.")
        return {}


def save_leads_to_csv(leads: list[dict]) -> None:
    """Save processed leads back to CSV safely, keeping order consistent."""
    COLUMNS = [
        "company_name", "website", "company_type", "product_category",
        "business_email", "business_phone", "whatsapp", "contact_person", "designation",
        "product_fit_score", "import_activity_score", "company_size_score",
        "market_relevance_score", "recent_activity_score", "decision_maker_score",
        "total_score", "lead_bucket", "buyer_probability", "import_probability",
        "product_relevance", "company_size", "market_relevance", "recent_activity",
        "decision_maker_status", "qualification_status", "qualification_error",
        "reason", "recommended_action", "evidence"
    ]
    output_df = pd.DataFrame(leads)
    
    # Fill missing columns with default None/empty to match schema
    for col in COLUMNS:
        if col not in output_df.columns:
            output_df[col] = ""
            
    output_df = output_df[COLUMNS]
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")


def main():
    parser = argparse.ArgumentParser(description="Wolf Group Production Qualification Pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of verified leads to process")
    args = parser.parse_args()

    if not INPUT_FILE.exists():
        print(f"Error: Input file {INPUT_FILE} does not exist.")
        sys.exit(1)

    print("Loading companies...")
    df = pd.read_csv(INPUT_FILE)
    total_records = len(df)

    # Filter for VERIFIED targets
    df_verified = df[df["verification_status"] == "VERIFIED"].copy()
    verified_records = len(df_verified)

    print(f"Total records: {total_records}")
    print(f"VERIFIED records: {verified_records}")

    # Set up subset to process in this run
    if args.limit is not None:
        df_to_process = df_verified.head(args.limit)
    else:
        df_to_process = df_verified

    process_count = len(df_to_process)
    print(f"Processing: {process_count}\n")

    # Load existing progress
    existing_results = load_existing_results()
    processed_this_run = {}

    success_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, (_, row) in enumerate(df_to_process.iterrows(), 1):
        company_name = row.get("company_name", "Unknown Company")
        
        # Check if already qualified successfully in a previous run (Resume logic)
        if company_name in existing_results and existing_results[company_name].get("qualification_status") == "QUALIFIED":
            print(f"[{idx}/{process_count}] {company_name} | SKIP (Already Qualified) | Score: {existing_results[company_name].get('total_score')} | Bucket: {existing_results[company_name].get('lead_bucket')}")
            processed_this_run[company_name] = existing_results[company_name]
            skipped_count += 1
            continue

        print(f"[{idx}/{process_count}] {company_name}")
        
        # Proactive delay of 3.5 seconds to respect the 20 RPM rate limit
        time.sleep(3.5)

        attempts = 3
        result = None
        error_msg = ""
        qualification_status = "FAILED"

        for attempt in range(1, attempts + 1):
            try:
                result = qualify_company(row.to_dict())
                qualification_status = "QUALIFIED"
                error_msg = ""
                break
            except Exception as e:
                error_msg = str(e)
                error_lower = error_msg.lower()
                
                # Retrieve HTTP status code if present
                status_code = getattr(e, "code", None)
                if status_code is None:
                    # Check for exact word matches of HTTP codes to avoid float collision (e.g. 5.724482403s)
                    match_code = re.search(r"\b(401|403)\b", error_msg)
                    if match_code:
                        status_code = int(match_code.group(1))

                # 1. Check for critical authentication / permission issues to halt early
                is_auth_error = (status_code in (401, 403)) or any(
                    x in error_lower for x in ("unauthenticated", "invalid authentication", "api_key_invalid", "permission_denied", "permission denied")
                )
                if is_auth_error:
                    print("\nGemini authentication/permission error.")
                    print("Check GEMINI_API_KEY and Google Cloud/AI Studio project configuration.\n")
                    
                    # Consolidate and save what we have before exiting
                    save_current_state(df_verified, processed_this_run, existing_results)
                    sys.exit(1)
                
                # 2. Check for QUOTA_EXHAUSTED (daily/project/model quota limit)
                is_quota_exhausted = any(
                    x in error_lower for x in (
                        "quota exceeded", "resource_exhausted", "resource exhausted",
                        "limit: 20", "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                        "generaterequestsperdayperprojectpermodel-freetier", "exceeded your current quota"
                    )
                )
                if is_quota_exhausted:
                    qualification_status = "RETRY_REQUIRED"
                    error_msg = "RESOURCE_EXHAUSTED (Daily quota limits reached)"
                    print("\nGemini quota exhausted.")
                    print(f"Company: {company_name}")
                    print("Status: RETRY_REQUIRED")
                    print("No score assigned.")
                    print("Resume after quota reset or quota upgrade.\n")
                    break  # DO NOT RETRY, DO NOT SLEEP, exit the retry loop immediately!

                # 3. Check for short-term rate limit (HTTP 429 temporary rate limit)
                is_rate_limited = (status_code == 429) or ("429" in error_lower)
                if is_rate_limited:
                    qualification_status = "RETRY_REQUIRED"
                    retry_seconds = 15.0
                    
                    # Parse delay from message string if present
                    match_seconds = re.search(r"retry in (\d+(?:\.\d+)?)s", error_msg, re.IGNORECASE)
                    if match_seconds:
                        retry_seconds = float(match_seconds.group(1))
                    elif hasattr(e, "details") and e.details:
                        for detail in e.details:
                            if isinstance(detail, dict) and "retryDelay" in detail:
                                delay_str = detail["retryDelay"]
                                match_d = re.search(r"(\d+)", delay_str)
                                if match_d:
                                    retry_seconds = float(match_d.group(1))
                                    break
                    
                    if attempt < attempts:
                        print(f"  Attempt {attempt} hit temporary rate limit. Respecting retry delay of {retry_seconds}s...")
                        time.sleep(retry_seconds + 1.0)
                        continue
                    else:
                        break

                # 4. Check for temporary service errors (502, 503, 504, connection errors)
                is_temp_service_error = (status_code in (502, 503, 504)) or any(
                    x in error_lower for x in ("502", "503", "504", "unavailable", "bad gateway", "gateway timeout", "deadline exceeded", "connection error")
                )
                if is_temp_service_error:
                    qualification_status = "RETRY_REQUIRED"
                    if attempt < attempts:
                        backoff_sleep = 5.0 if attempt == 1 else 15.0
                        print(f"  Attempt {attempt} failed (Temporary service error). Sleeping {backoff_sleep}s (exponential backoff)...")
                        time.sleep(backoff_sleep)
                        continue
                    else:
                        break

                # 5. Invalid JSON response from model
                if "json parsing error" in error_lower or isinstance(e, ValueError):
                    qualification_status = "FAILED"
                    break

                # 6. Default fallback for other unknown errors
                qualification_status = "FAILED"
                break

        if qualification_status == "QUALIFIED" and result:
            # Build success row
            qualified_lead = {
                "company_name": company_name,
                "website": clean_value(row.get("url_found")),
                "company_type": result.get("company_type", "UNKNOWN"),
                "product_category": "Porcelain & Ceramic Tiles",
                "business_email": clean_value(row.get("business_email")),
                "business_phone": clean_value(row.get("business_phone")),
                "whatsapp": clean_value(row.get("whatsapp")),
                "contact_person": clean_value(row.get("contact_person")),
                "designation": clean_value(row.get("designation")),
                "product_fit_score": result.get("product_fit_score", 0),
                "import_activity_score": result.get("import_activity_score", 0),
                "company_size_score": result.get("company_size_score", 0),
                "market_relevance_score": result.get("market_relevance_score", 0),
                "recent_activity_score": result.get("recent_activity_score", 0),
                "decision_maker_score": result.get("decision_maker_score", 0),
                "total_score": result.get("total_score", 0),
                "lead_bucket": result.get("lead_bucket", "LOW"),
                "buyer_probability": result.get("buyer_probability", "UNKNOWN"),
                "import_probability": result.get("import_probability", "UNKNOWN"),
                "product_relevance": result.get("product_relevance", "UNKNOWN"),
                "company_size": result.get("company_size", "UNKNOWN"),
                "market_relevance": result.get("market_relevance", "UNKNOWN"),
                "recent_activity": result.get("recent_activity", "UNKNOWN"),
                "decision_maker_status": result.get("decision_maker_status", "UNKNOWN"),
                "qualification_status": "QUALIFIED",
                "qualification_error": "",
                "reason": result.get("reason", ""),
                "recommended_action": result.get("recommended_action", ""),
                "evidence": "; ".join(result.get("evidence", [])) if isinstance(result.get("evidence"), list) else str(result.get("evidence", ""))
            }
            success_count += 1
            print(f"  Gemini: SUCCESS | Score: {qualified_lead['total_score']} | Bucket: {qualified_lead['lead_bucket']}\n")
        else:
            # Build failure row (no score, no bucket)
            qualified_lead = {
                "company_name": company_name,
                "website": clean_value(row.get("url_found")),
                "company_type": "UNKNOWN",
                "product_category": "Porcelain & Ceramic Tiles",
                "business_email": clean_value(row.get("business_email")),
                "business_phone": clean_value(row.get("business_phone")),
                "whatsapp": clean_value(row.get("whatsapp")),
                "contact_person": clean_value(row.get("contact_person")),
                "designation": clean_value(row.get("designation")),
                "product_fit_score": "",
                "import_activity_score": "",
                "company_size_score": "",
                "market_relevance_score": "",
                "recent_activity_score": "",
                "decision_maker_score": "",
                "total_score": "",
                "lead_bucket": "",
                "buyer_probability": "UNKNOWN",
                "import_probability": "UNKNOWN",
                "product_relevance": "UNKNOWN",
                "company_size": "UNKNOWN",
                "market_relevance": "UNKNOWN",
                "recent_activity": "UNKNOWN",
                "decision_maker_status": "UNKNOWN",
                "qualification_status": qualification_status,
                "qualification_error": error_msg,
                "reason": "Failed to qualify due to API/system error.",
                "recommended_action": "Retry run later or check API limits.",
                "evidence": f"Error detail: {error_msg}"
            }
            failed_count += 1
            print(f"  Gemini: FAILED | Status: {qualification_status} | Error: {error_msg}\n")

        processed_this_run[company_name] = qualified_lead
        
        # Save incrementally after every record to protect data progress
        save_current_state(df_verified, processed_this_run, existing_results)

    # Re-save final set to ensure correct format
    save_current_state(df_verified, processed_this_run, existing_results)

    print("Test run complete." if args.limit else "Production run complete.")
    print(f"Qualified successfully: {success_count}")
    print(f"Skipped (Already qualified): {skipped_count}")
    print(f"Failed/Pending Retry: {failed_count}")


def save_current_state(df_verified: pd.DataFrame, processed_this_run: dict, existing_results: dict) -> None:
    """Combine skipped, newly processed, and unprocessed records keeping the original verified leads list order."""
    combined_leads = []
    
    for _, row in df_verified.iterrows():
        name = row["company_name"]
        
        # Prioritize leads processed in the current run
        if name in processed_this_run:
            combined_leads.append(processed_this_run[name])
        # Second, prioritize successfully qualified leads from previous runs
        elif name in existing_results and existing_results[name].get("qualification_status") == "QUALIFIED":
            combined_leads.append(existing_results[name])
        # Third, fall back to retryable or failed results from previous runs
        elif name in existing_results:
            combined_leads.append(existing_results[name])
        # Default fallback: create an empty/unprocessed row for this verified lead
        else:
            unprocessed_lead = {
                "company_name": name,
                "website": clean_value(row.get("url_found")),
                "company_type": "UNKNOWN",
                "product_category": "Porcelain & Ceramic Tiles",
                "business_email": clean_value(row.get("business_email")),
                "business_phone": clean_value(row.get("business_phone")),
                "whatsapp": clean_value(row.get("whatsapp")),
                "contact_person": clean_value(row.get("contact_person")),
                "designation": clean_value(row.get("designation")),
                "product_fit_score": "",
                "import_activity_score": "",
                "company_size_score": "",
                "market_relevance_score": "",
                "recent_activity_score": "",
                "decision_maker_score": "",
                "total_score": "",
                "lead_bucket": "",
                "buyer_probability": "UNKNOWN",
                "import_probability": "UNKNOWN",
                "product_relevance": "UNKNOWN",
                "company_size": "UNKNOWN",
                "market_relevance": "UNKNOWN",
                "recent_activity": "UNKNOWN",
                "decision_maker_status": "UNKNOWN",
                "qualification_status": "RETRY_REQUIRED",
                "qualification_error": "Unprocessed target lead",
                "reason": "Pending qualification run.",
                "recommended_action": "Execute run_qualification script.",
                "evidence": "Unprocessed target lead"
            }
            combined_leads.append(unprocessed_lead)

    save_leads_to_csv(combined_leads)


if __name__ == "__main__":
    main()
