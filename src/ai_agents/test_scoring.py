from __future__ import annotations

import unittest
import sys
from pathlib import Path

# Add directory containing scoring.py to path
sys.path.append(str(Path(__file__).resolve().parent))

from scoring import calculate_lead_score


class TestScoring(unittest.TestCase):

    def test_maximum_score(self):
        # HIGH (25) + HIGH (25) + LARGE (15) + HIGH (15) + HIGH (10) + FOUND (10) = 100
        data = {
            "product_relevance": "HIGH",
            "import_probability": "HIGH",
            "company_size": "LARGE",
            "market_relevance": "HIGH",
            "recent_activity": "HIGH",
            "decision_maker_status": "FOUND"
        }
        res = calculate_lead_score(data)
        self.assertEqual(res["total_score"], 100)
        self.assertEqual(res["lead_bucket"], "HOT")

    def test_minimum_score(self):
        # NONE (0) + NONE (0) + UNKNOWN (0) + NONE (0) + NONE (0) + UNKNOWN (0) = 0
        data = {
            "product_relevance": "NONE",
            "import_probability": "NONE",
            "company_size": "UNKNOWN",
            "market_relevance": "NONE",
            "recent_activity": "NONE",
            "decision_maker_status": "UNKNOWN"
        }
        res = calculate_lead_score(data)
        self.assertEqual(res["total_score"], 0)
        self.assertEqual(res["lead_bucket"], "LOW")

    def test_medium_score(self):
        # MEDIUM (15) + MEDIUM (15) + MEDIUM (10) + MEDIUM (10) + MEDIUM (7) + NOT_FOUND (0) = 57
        data = {
            "product_relevance": "MEDIUM",
            "import_probability": "MEDIUM",
            "company_size": "MEDIUM",
            "market_relevance": "MEDIUM",
            "recent_activity": "MEDIUM",
            "decision_maker_status": "NOT_FOUND"
        }
        res = calculate_lead_score(data)
        self.assertEqual(res["total_score"], 57)
        self.assertEqual(res["lead_bucket"], "POTENTIAL")

    def test_boundaries(self):
        # Target 37 (LOW)
        res_37 = calculate_lead_score({
            "product_relevance": "LOW", "import_probability": "LOW", "company_size": "MEDIUM",
            "market_relevance": "MEDIUM", "recent_activity": "MEDIUM", "decision_maker_status": "UNKNOWN"
        })
        self.assertEqual(res_37["total_score"], 37)
        self.assertEqual(res_37["lead_bucket"], "LOW")

        # Target 40 (POTENTIAL)
        res_40 = calculate_lead_score({
            "product_relevance": "LOW", "import_probability": "LOW", "company_size": "MEDIUM",
            "market_relevance": "MEDIUM", "recent_activity": "HIGH", "decision_maker_status": "UNKNOWN"
        })
        self.assertEqual(res_40["total_score"], 40)
        self.assertEqual(res_40["lead_bucket"], "POTENTIAL")

        # Target 58 (POTENTIAL)
        res_58 = calculate_lead_score({
            "product_relevance": "MEDIUM", "import_probability": "MEDIUM", "company_size": "LARGE",
            "market_relevance": "MEDIUM", "recent_activity": "LOW", "decision_maker_status": "UNKNOWN"
        })
        self.assertEqual(res_58["total_score"], 58)
        self.assertEqual(res_58["lead_bucket"], "POTENTIAL")

        # Target 62 (WARM)
        res_62 = calculate_lead_score({
            "product_relevance": "MEDIUM", "import_probability": "MEDIUM", "company_size": "LARGE",
            "market_relevance": "MEDIUM", "recent_activity": "MEDIUM", "decision_maker_status": "UNKNOWN"
        })
        self.assertEqual(res_62["total_score"], 62)
        self.assertEqual(res_62["lead_bucket"], "WARM")

        # Target 77 (WARM)
        res_77 = calculate_lead_score({
            "product_relevance": "HIGH", "import_probability": "MEDIUM", "company_size": "LARGE",
            "market_relevance": "HIGH", "recent_activity": "MEDIUM", "decision_maker_status": "UNKNOWN"
        })
        self.assertEqual(res_77["total_score"], 77)
        self.assertEqual(res_77["lead_bucket"], "WARM")

        # Target 80 (HOT)
        res_80 = calculate_lead_score({
            "product_relevance": "HIGH", "import_probability": "MEDIUM", "company_size": "LARGE",
            "market_relevance": "HIGH", "recent_activity": "HIGH", "decision_maker_status": "UNKNOWN"
        })
        self.assertEqual(res_80["total_score"], 80)
        self.assertEqual(res_80["lead_bucket"], "HOT")


if __name__ == "__main__":
    unittest.main()
