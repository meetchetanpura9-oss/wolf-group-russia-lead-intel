from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

LEGAL_SUFFIXES = [
    "общество с ограниченной ответственностью",
    "товарищество с ограниченной ответственностью",
    "ооо",
    "ooo",
    "llc",
    "ltd",
    "inc",
]


def normalize_text(value: object) -> str:
    """Normalize general text while preserving Cyrillic characters."""
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()

    # Replace non-breaking spaces and repeated whitespace.
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    # Normalize common punctuation separators.
    text = text.replace("ё", "е")

    return text


def normalize_company_name(value: object) -> str:
    """Normalize a company name for matching."""
    text = normalize_text(value)

    # Remove legal suffixes from the end of the name.
    for suffix in sorted(LEGAL_SUFFIXES, key=len, reverse=True):
        pattern = rf"(?:^|\s|\(|,){re.escape(suffix)}$"
        text = re.sub(pattern, "", text).strip(" ,.-()")

    # Normalize punctuation for comparison.
    text = re.sub(r"[\"'«»„“”]", "", text)
    text = re.sub(r"[^\w\s-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_url(value: object) -> str:
    """Normalize a URL while preserving the original separately."""
    if pd.isna(value):
        return ""

    url = str(value).strip()

    if not url:
        return ""

    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        
        path = parsed.path.lower().rstrip("/")
        normalized = f"https://{netloc}{path}"
        return normalized
    except Exception:
        return url.lower()


def extract_domain(value: object) -> str:
    """Extract and normalize the domain from a URL."""
    if pd.isna(value):
        return ""

    url = str(value).strip()
    if not url:
        return ""

    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if ":" in netloc:
            netloc = netloc.split(":")[0]
        return netloc
    except Exception:
        return ""


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    input_file = project_root / "data" / "raw" / "companies_raw.csv"
    output_dir = project_root / "data" / "cleaned"
    output_file = output_dir / "companies_normalized.csv"

    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        print(f"Error: Input file does not exist: {input_file}")
        return

    df = pd.read_csv(input_file)

    # Add normalized fields
    df["company_name_normalized"] = df["company_name"].apply(normalize_company_name)
    df["url_normalized"] = df["url_found"].apply(normalize_url)
    df["domain_normalized"] = df["url_found"].apply(extract_domain)

    df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print("Normalization complete.")
    print(f"Input rows: {len(df)}")
    print(f"Output rows: {len(df)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
