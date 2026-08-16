# Phase 2 — Data Discovery: Raw Lead Candidates

This document details the data discovery phase for the **Wolf Group Russia B2B Buyer Intelligence** project. During this phase, we established a pipeline to aggregate automated search engine results and manual trade-intelligence leads into a single, structured raw candidate dataset.

---

## 1. Methodology Summary

### Collection Summary
- **Collection Date:** August 16, 2026
- **Total Raw Search Results:** 144 records
- **Total Unique Search Records:** 79 unique URL rows
- **Total Manual Trade Records:** 32 unique URL rows
- **Final Combined Unique Candidates:** 111 unique URL rows
- **Status:** All records successfully saved and auto-classified.

---

## 2. Automated Search Collection

### API Used
We used **SerpApi (Google Search Engine Engine)**. 
- Using SerpApi ensures compliance with search engine Terms of Service.
- Direct scraping of search engine pages was **deliberately avoided** to prevent IP blocks, CAPTCHAs, and to ensure stable, reliable, and compliant access to query results.

### Search Queries
We ran 16 search queries across Russian and English keywords to capture both local-language B2B activities and global import directories:

#### Russian Queries (Cyrillic)
1. `керамогранит импортер Россия`
2. `керамическая плитка импортер Россия`
3. `керамогранит дистрибьютор Россия`
4. `керамическая плитка дистрибьютор Россия`
5. `плитка оптовая компания Россия`
6. `плитка импортер Москва`
7. `керамогранит оптом Москва`
8. `керамическая плитка оптом Санкт-Петербург`
9. `импортер плитки Россия`
10. `дистрибьютор плитки Россия`

#### English Queries
11. `tile importer Russia`
12. `ceramic tile importer Russia`
13. `porcelain tile importer Russia`
14. `tile distributor Russia`
15. `ceramic tile wholesaler Russia`
16. `porcelain tile wholesaler Moscow`

---

## 3. Manual Trade Research

To complement the automated web search results, we manually researched and recorded **32 authoritative trade leads** from public industry platforms:
- **MosBuild Exhibitor List:** The premier trade exhibition for construction and finishing materials in Russia (e.g. Kerama Marazzi, Estima, Unitile, Creto, Global Tile, Kerranova).
- **Supl.biz & OptomTovar.ru Directories:** Leading Russian B2B wholesale marketplaces containing verified profiles of importers and warehouse distributors (e.g., Plitka-Podolsk, Cerammax).

### Attribution Discipline
To maintain standard professional data integrity:
- Every manually researched company contains a verified company name, product category (e.g. *Porcelain & Ceramic Tiles*), source, and direct public URL.
- The `research_method` field is explicitly set to `"Manual Public Research"` to distinguish these from API-discovered records.
- We do not claim access to proprietary or commercial customs transaction databases.

---

## 4. Duplicate & Merging Strategy

If two different search queries, or a manual trade lead and a search query, discover the same URL:
- We preserve the discovery context by **collapsing the rows** into a single row keyed by `url_found`.
- The `source` field is dynamically updated to append new sources/queries separated by a semicolon (`; `) (e.g., `SerpApi | query A; SerpApi | query B; Manual Trade Research | MosBuild`).
- The earliest `date_discovered` timestamp is preserved.
- This creates an auditable record of how many separate channels led to the same candidate without cluttering the pipeline with duplicate rows.

---

## 5. Raw Result Classification (`result_type`)

Rather than deleting irrelevant rows during the raw discovery phase (which would destroy our data audit trail), we added a `result_type` column to classify candidates using automated rules:
- **`COMPANY`:** General homepages or simple contact pages of tile/building companies.
- **`DIRECTORY`:** Trade directories, portals, and aggregator lists.
- **`MAP`:** Navigation and mapping portals (Yandex Maps, Google Maps).
- **`NEWS_ARTICLE`:** Market reviews, articles, and general press releases.
- **`PRODUCT_PAGE`:** Direct deep-links to specific product collections.
- **`BLOG` / `UNKNOWN`:** Blogs and generic pages that require further sanitization.

### Combined Dataset Breakdown
- **COMPANY:** 65
- **DIRECTORY:** 16
- **UNKNOWN:** 15
- **PRODUCT_PAGE:** 9
- **MAP:** 4
- **NEWS_ARTICLE:** 1
- **BLOG:** 1

---

## 6. Limitations & Considerations

### Data Limitations
- Raw search titles often contain marketing copy (e.g., `"Керамогранит - купить в Москве по цене производителя..."`) instead of clean legal names. Name cleaning and extraction will be handled during Phase 3.
- Directory results (e.g. `supl.biz`) are useful indicators but are not direct buyers. They are preserved for lead verification.

### Ethical & Compliance Considerations
- All contact information must be publicly displayed on the target sites.
- Automated collection was throttled (1-second delays between searches) to keep requests gentle.
- Personal data protection rules (GDPR / FZ-152) are respected: public company pages and general business contact info are mapped for B2B intelligence purposes; any outreach sequences in Phase 6 will be decoupled and subject to separate consent validation.
