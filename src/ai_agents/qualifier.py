from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

from scoring import calculate_lead_score

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing from .env. "
        "Please configure a valid API key in your .env."
    )

# Initialize the Gemini client using the working SDK client pattern
client = genai.Client(api_key=GEMINI_API_KEY)

QUALIFICATION_SCHEMA = """
{
  "company_type": "IMPORTER | DISTRIBUTOR | WHOLESALER | RETAILER | SHOWROOM | CONSTRUCTION | DEVELOPER | MANUFACTURER | DIRECTORY | UNKNOWN",
  "product_relevance": "HIGH | MEDIUM | LOW | NONE",
  "buyer_probability": "HIGH | MEDIUM | LOW | NONE",
  "import_probability": "HIGH | MEDIUM | LOW | NONE",
  "company_size": "LARGE | MEDIUM | SMALL | UNKNOWN",
  "market_relevance": "HIGH | MEDIUM | LOW | NONE",
  "recent_activity": "HIGH | MEDIUM | LOW | NONE",
  "decision_maker_status": "FOUND | NOT_FOUND | UNKNOWN",
  "evidence": [
    "String detailing specific evidence found in page title or content."
  ],
  "reason": "Clear rationale string summarizing findings.",
  "recommended_action": "Proposed next outreach or validation action"
}
"""

SYSTEM_PROMPT = f"""You are a professional B2B lead qualification agent. Your task is to analyze the provided company evidence and classify it for a building materials exporter (Wolf Group India, specializing in porcelain and ceramic tiles).

You must return a raw JSON object matching this schema:
{QUALIFICATION_SCHEMA}

CRITICAL RULES:
1. Never invent or assume company information. If evidence is unavailable, return UNKNOWN or NOT_FOUND.
2. Every conclusion must be strictly supported by the provided source evidence.
3. Do not infer:
   - import activity from general words like "international" or "import" unless it specifies import of building/tile products or direct import operations.
   - WhatsApp status from a phone number.
   - decision maker identity from a generic email.
   - company size solely from website aesthetics.
   - recent activity without explicit dated evidence.
"""


def clean_value(value: object) -> str:
    """Clean pandas NaN, None, and empty strings to 'NOT_FOUND' to keep evidence explicit."""
    if pd.isna(value) or value is None:
        return "NOT_FOUND"
    val_str = str(value).strip()
    if val_str.lower() in ("nan", ""):
        return "NOT_FOUND"
    return val_str


def parse_json_response(text: str) -> dict:
    """Parse JSON output from Gemini, stripping any markdown code block wrappers if present."""
    clean_text = text.strip()
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```(?:json)?\s*\n?", "", clean_text)
        clean_text = re.sub(r"\n?\s*```$", "", clean_text)
    return json.loads(clean_text.strip())


def qualify_company(company_data: dict) -> dict:
    """Send structured company evidence to Gemini, parse classifications, and run deterministic scoring in Python."""
    evidence_text = f"""
Company Name: {clean_value(company_data.get('company_name'))}
Website: {clean_value(company_data.get('url_found'))}
Page Title: {clean_value(company_data.get('page_title'))}
Result Type: {clean_value(company_data.get('result_type'))}
Website Status: {clean_value(company_data.get('website_status'))}
Tile Relevant Flag: {clean_value(company_data.get('tile_relevant'))}
Russia Relevant Flag: {clean_value(company_data.get('russia_relevant'))}
Business Email: {clean_value(company_data.get('business_email'))}
Business Phone: {clean_value(company_data.get('business_phone'))}
WhatsApp: {clean_value(company_data.get('whatsapp'))}
Decision Maker: {clean_value(company_data.get('contact_person'))}
Designation: {clean_value(company_data.get('designation'))}
Notes / Verification Notes: {clean_value(company_data.get('verification_notes'))}
"""

    prompt = f"Analyze this company and return the qualification JSON:\n\n{evidence_text}"

    # Let exceptions (429, 503) propagate to the batch processor for retry handling
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json"
        )
    )

    try:
        result = parse_json_response(response.text)
    except Exception as e:
        raise ValueError(f"JSON parsing error: {e}. Raw response: {response.text}")

    # Validate that the required output fields exist
    required_fields = [
        "company_type", "product_relevance", "buyer_probability",
        "import_probability", "company_size", "market_relevance",
        "recent_activity", "decision_maker_status", "evidence",
        "reason", "recommended_action"
    ]
    for field in required_fields:
        if field not in result:
            result[field] = "UNKNOWN"

    # Deterministically calculate scores in Python using the classification fields
    scores = calculate_lead_score(result)
    result.update(scores)

    return result


if __name__ == "__main__":
    # Test with one company
    input_file = PROJECT_ROOT / "data" / "cleaned" / "companies_with_contacts.csv"
    if not input_file.exists():
        print(f"Error: Input file {input_file} does not exist.")
        exit(1)

    df = pd.read_csv(input_file)
    df_v = df[df["verification_status"] == "VERIFIED"]
    if df_v.empty:
        print("No verified companies found to test.")
        exit(1)

    test_company = df_v.iloc[0].to_dict()
    print(f"Testing qualifier with company: {test_company['company_name']}\n")

    # Display structured evidence with cleaned NaN values
    print("Structured Evidence:")
    print(f"- Website: {clean_value(test_company.get('url_found'))}")
    print(f"- Tile Relevant: {clean_value(test_company.get('tile_relevant'))}")
    print(f"- Russia Relevant: {clean_value(test_company.get('russia_relevant'))}")
    print(f"- Email: {clean_value(test_company.get('business_email'))}")
    print(f"- Phone: {clean_value(test_company.get('business_phone'))}")

    print("\nCalling LLM...")
    try:
        start_time = time.time()
        result = qualify_company(test_company)
        duration = time.time() - start_time
        print("Gemini request success.")
        print(f"\nAI Qualification (took {duration:.2f} seconds):")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\nQualification successful.")
    except Exception as e:
        print(f"Execution failed: {e}")
