from __future__ import annotations

def calculate_lead_score(ai_data: dict) -> dict:
    """
    Calculate the B2B lead score deterministically using classifications provided by the AI:
    - Product Fit: Weight 25% (HIGH=25, MEDIUM=15, LOW=5, NONE/UNKNOWN=0)
    - Import Activity: Weight 25% (HIGH=25, MEDIUM=15, LOW=5, NONE/UNKNOWN=0)
    - Company Size: Weight 15% (LARGE=15, MEDIUM=10, SMALL=5, UNKNOWN=0)
    - Market Relevance: Weight 15% (HIGH=15, MEDIUM=10, LOW=5, NONE/UNKNOWN=0)
    - Recent Activity: Weight 10% (HIGH=10, MEDIUM=7, LOW=3, NONE/UNKNOWN=0)
    - Decision Maker Found: Weight 10% (FOUND/YES=10, NOT_FOUND/NO/UNKNOWN=0)
    """
    # 1. Product Fit (25%)
    prod_fit = str(ai_data.get("product_relevance", "UNKNOWN")).upper().strip()
    if prod_fit == "HIGH":
        prod_fit_score = 25
    elif prod_fit == "MEDIUM":
        prod_fit_score = 15
    elif prod_fit == "LOW":
        prod_fit_score = 5
    else:
        prod_fit_score = 0

    # 2. Import Activity (25%)
    imp_act = str(ai_data.get("import_probability", "UNKNOWN")).upper().strip()
    if imp_act == "HIGH":
        import_activity_score = 25
    elif imp_act == "MEDIUM":
        import_activity_score = 15
    elif imp_act == "LOW":
        import_activity_score = 5
    else:
        import_activity_score = 0

    # 3. Company Size (15%)
    comp_size = str(ai_data.get("company_size", "UNKNOWN")).upper().strip()
    if comp_size == "LARGE":
        company_size_score = 15
    elif comp_size == "MEDIUM":
        company_size_score = 10
    elif comp_size == "SMALL":
        company_size_score = 5
    else:
        company_size_score = 0

    # 4. Market Relevance (15%)
    mkt_rel = str(ai_data.get("market_relevance", "UNKNOWN")).upper().strip()
    if mkt_rel == "HIGH":
        market_relevance_score = 15
    elif mkt_rel == "MEDIUM":
        market_relevance_score = 10
    elif mkt_rel == "LOW":
        market_relevance_score = 5
    else:
        market_relevance_score = 0

    # 5. Recent Activity (10%)
    rec_act = str(ai_data.get("recent_activity", "UNKNOWN")).upper().strip()
    if rec_act == "HIGH":
        recent_activity_score = 10
    elif rec_act == "MEDIUM":
        recent_activity_score = 7
    elif rec_act == "LOW":
        recent_activity_score = 3
    else:
        recent_activity_score = 0

    # 6. Decision Maker Found (10%)
    dm_status = str(ai_data.get("decision_maker_status", "UNKNOWN")).upper().strip()
    if dm_status in ("FOUND", "YES"):
        decision_maker_score = 10
    else:
        decision_maker_score = 0

    # Calculate final score and clamp to 0-100
    total_score = (
        prod_fit_score +
        import_activity_score +
        company_size_score +
        market_relevance_score +
        recent_activity_score +
        decision_maker_score
    )
    total_score = max(0, min(100, total_score))

    # Lead Bucket Classification
    if total_score >= 80:
        lead_bucket = "HOT"
    elif total_score >= 60:
        lead_bucket = "WARM"
    elif total_score >= 40:
        lead_bucket = "POTENTIAL"
    else:
        lead_bucket = "LOW"

    return {
        "product_fit_score": prod_fit_score,
        "import_activity_score": import_activity_score,
        "company_size_score": company_size_score,
        "market_relevance_score": market_relevance_score,
        "recent_activity_score": recent_activity_score,
        "decision_maker_score": decision_maker_score,
        "total_score": total_score,
        "lead_bucket": lead_bucket
    }
