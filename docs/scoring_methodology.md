# Lead Scoring & Qualification Methodology

This document outlines the lead scoring framework designed for the **Wolf Group Russia B2B Buyer Intelligence** project. 

---

## 1. Architectural Rationale: Deterministic vs. AI-Scoring

In standard AI implementations, LLMs are frequently asked to output a final lead score directly (e.g., *"give this company a B2B score out of 100"*). We **deliberately avoid** this design pattern because:
- **Reproducibility:** LLM scores are non-deterministic, varying across calls even with temperature set to 0. 
- **Explainability:** An arbitrary AI score (e.g., "73") is not auditable. By separating classification from calculation, we can explain exactly *why* a company received a specific score down to the point values.
- **Auditability:** We can adjust weights and point models globally in Python code without having to re-run and re-prompt the LLM.

### The Pipeline Architecture
```
VERIFIED LEAD
     │
     ▼
Evidence Builder (Sanitize Pandas NaN/None)
     │
     ▼
Gemini AI (Classifies company parameters in structured JSON)
     │
     ▼
Python Scoring Engine (Applies deterministic point formulas)
     │
     ▼
HOT / WARM / POTENTIAL / LOW Classification
```

---

## 2. Lead Scoring Matrix

The final lead score is a weighted combination of six distinct factors normalized on a scale from `0` to `100`.

### Weighted Factors

| Factor | Weight | Description |
| :--- | :---: | :--- |
| **Product Fit** | 25% | Core relevance of porcelain and ceramic tile products to the company's business model. |
| **Import Activity** | 25% | Verified evidence of direct overseas sourcing or importing. |
| **Company Size** | 15% | Scale of the operation (e.g., national network, regional branches, or local showroom). |
| **Market Relevance** | 15% | Fit of the target company's location and B2B profile with Russia's commercial landscape. |
| **Recent Activity** | 10% | Business signals indicating active operations (recent exhibitions, catalogs, or website updates). |
| **Decision Maker Found** | 10% | Verified presence of a target purchasing or procurement contact. |
| **Total** | **100%** | |

---

## 3. Score Value Mapping

Each factor assigns points based on qualitative ratings returned by the AI:

### 1. Product Fit (Max 25 pts)
- **`HIGH`** (25 pts): Porcelain/ceramic tile is their core business.
- **`MEDIUM`** (15 pts): Strong tile or building-material focus (tiles are a major product line).
- **`LOW`** (5 pts): Tiles are one of many general construction products.
- **`NONE` / `UNKNOWN`** (0 pts): Weak relevance or unverified.

### 2. Import Activity (Max 25 pts)
- **`HIGH`** (25 pts): Explicit importer or active customs data.
- **`MEDIUM`** (15 pts): Strong international sourcing indications on the website.
- **`LOW`** (5 pts): Distributor of foreign brands, indicating indirect import relationship.
- **`NONE` / `UNKNOWN`** (0 pts): Local-only sourcing or no import indicators found.

### 3. Company Size (Max 15 pts)
- **`LARGE`** (15 pts): National or multi-city network/operations.
- **`MEDIUM`** (10 pts): Established regional dealer/showroom chain.
- **`SMALL`** (5 pts): Single-location local retail shop or construction office.
- **`UNKNOWN`** (0 pts): Stated scale cannot be verified from public info.

### 4. Market Relevance (Max 15 pts)
- **`HIGH`** (15 pts): Clear Russian B2B tile distribution/import target.
- **`MEDIUM`** (10 pts): Regional B2B building-material focus.
- **`LOW`** (5 pts): Mixed B2B/B2C showroom or weak commercial footprint.
- **`NONE` / `UNKNOWN`** (0 pts): Weak commercial target.

### 5. Recent Activity (Max 10 pts)
- **`HIGH`** (10 pts): Stated updates within the current year (recent exhibitions, trade shows, catalogs).
- **`MEDIUM`** (7 pts): Website is active, with steady catalog/collection updates.
- **`LOW`** (3 pts): Limited recent updates.
- **`NONE` / `UNKNOWN`** (0 pts): Stale site or no verifiable indicators.

### 6. Decision Maker Found (Max 10 pts)
- **`FOUND` / `YES`** (10 pts): Stated procurement/import contact person is identified on their team pages.
- **`NOT_FOUND` / `UNKNOWN`** (0 pts): Generic emails or no specific person listed.

---

## 4. Lead Classification Buckets

After Python calculates the cumulative sum of the scoring categories, the lead is assigned to one of four priority buckets:

- **`HOT` Lead (80 - 100):** Direct targets. Importers/large distributors with high product match and active operations. Priority 1 outreach.
- **`WARM` Lead (60 - 79):** Intermediate targets. Active building-materials distributors or showrooms with indirect import history. Priority 2 outreach.
- **`POTENTIAL` Lead (40 - 59):** Prospects requiring further manual research (e.g., regional showrooms or smaller commercial buyers).
- **`LOW` Lead (0 - 39):** Non-targets (directories, news posts, or companies with no contact data or relevance).

---

## 5. Strict Data Integrity: UNKNOWN Handling

To maintain an auditable pipeline:
- **No Positive Assumptions:** Missing fields or unconfirmed ratings are always mapped to `UNKNOWN` or `NONE`, translating to `0` points for that factor.
- **Evidence-First Rule:** The LLM is instructed in `SYSTEM_PROMPT` to only assign classifications when explicit evidence is present in the scraped context. If no dates or explicit import statements are found, the rating is kept as `UNKNOWN` rather than guessed.
