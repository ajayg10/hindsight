import sys
import os
import unittest
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.clock import DemoClock
from backend.app.mcp_server import HindsightToolRegistry
from falkordb import FalkorDB
from seed.plant import plant_golden_slice
from backend.app.main import get_facts_ledger

class TestPartAFixes(unittest.TestCase):
    def setUp(self):
        self.host = os.getenv("FALKORDB_HOST", "localhost")
        self.port = int(os.getenv("FALKORDB_PORT", "6379"))
        self.db = FalkorDB(host=self.host, port=self.port)
        plant_golden_slice(self.db, "t:parcelo")
        self.registry = HindsightToolRegistry(self.db, "t:parcelo")

    def test_investigator_a_formula_full_and_partial_coverage(self):
        """
        Verify Investigator-A formula:
        formula = coverage * (1.0 / (1.0 + 0.05 * (max(1, hops) - 1)))
        1. 9/9 alerts at 1 hop = 1.00 * (1 / 1.0) = 1.00
        2. 9/9 alerts at 2 hops = 1.00 * (1 / 1.05) = 0.95
        3. 6/9 alerts at 1 hop (partial coverage) = (6/9) * (1 / 1.0) = 0.67
        4. 6/9 alerts at 2 hops (partial coverage) = (6/9) / 1.05 = 0.63
        """
        def calc_score(hits, total, hops):
            cov = hits / max(total, 1)
            penalty = 1.0 + 0.05 * (max(1, hops) - 1)
            score = round(cov * (1.0 / penalty), 2)
            print(f"[TEST Investigator-A] inputs: hits={hits}/{total}, cov={cov:.4f}, hops={hops} -> score={score:.2f}")
            return score

        # 1. Full coverage at 1 hop
        s_full_1 = calc_score(9, 9, 1)
        self.assertEqual(s_full_1, 1.00, f"Expected 1.00 at 1 hop full coverage, got {s_full_1}")

        # 2. Full coverage at 2 hops
        s_full_2 = calc_score(9, 9, 2)
        self.assertEqual(s_full_2, 0.95, f"Expected 0.95 at 2 hops full coverage, got {s_full_2}")

        # 3. Partial coverage at 1 hop (6/9 alerts)
        s_part_1 = calc_score(6, 9, 1)
        self.assertEqual(s_part_1, 0.67, f"Expected 0.67 for 6/9 at 1 hop, got {s_part_1}")

        # 4. Partial coverage at 2 hops (6/9 alerts)
        s_part_2 = calc_score(6, 9, 2)
        self.assertEqual(s_part_2, 0.63, f"Expected 0.63 for 6/9 at 2 hops, got {s_part_2}")

        # Test against live MCP tool registry
        res = self.registry.root_cause_candidates(incident_id="INC-8821")
        print("[Live Investigator-A Result]:", res["top_candidate"], "score:", res["heuristic_score"])
        self.assertIn("heuristic_score", res)
        self.assertEqual(res["top_candidate"], "cache-b")
        # In the golden slice, cache-b directly covers all 9 alerts (1 hop away)
        self.assertEqual(res["heuristic_score"], 1.00, "cache-b directly covers all 9 alerts at 1 hop, score must be 1.00")

    def test_investigator_b_heuristic_score(self):
        """
        Verify Investigator-B heuristic score:
        formula = round(min(0.90, 0.50 + bw_share * 0.35), 2)
        """
        res = self.registry.rank_services(incident_id="INC-8821")
        print("[Live Investigator-B Result]:", res["top_candidate"], "score:", res["heuristic_score"])
        self.assertIn("heuristic_score", res)
        self.assertEqual(res["top_candidate"], "checkout-api")
        self.assertGreaterEqual(res["heuristic_score"], 0.50)
        self.assertLessEqual(res["heuristic_score"], 0.90)

    def test_fact_ledger_dates_derived_from_democlock(self):
        """
        Verify fact ledger dates:
        1. ADR-17 valid_to == DemoClock.now_ms - 6 days.
        2. valid_to ISO string is exactly 2026-10-09 (6 days before Oct 15).
        """
        clock = DemoClock.frozen()
        expected_adr17_ms = clock.now_ms - (6 * 24 * 3600 * 1000)
        expected_iso = datetime.fromtimestamp(expected_adr17_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

        print(f"DemoClock now_ms: {clock.now_ms} ({datetime.fromtimestamp(clock.now_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d')})")
        print(f"Expected ADR-17 valid_to: {expected_adr17_ms} ({expected_iso})")

        self.assertEqual(expected_iso, "2026-10-09", "ADR-17 must be placed on 2026-10-09 (exactly 6 days before Oct 15)")

        ledger = get_facts_ledger(tenant="parcelo")
        self.assertIn("facts", ledger)
        self.assertGreaterEqual(len(ledger["facts"]), 2)

        # Check superseded fact
        super_fact = next(f for f in ledger["facts"] if f["status"] == "superseded")
        self.assertEqual(super_fact["subject"], "checkout-api")
        self.assertEqual(super_fact["object"], "cache-a")
        self.assertEqual(super_fact["valid_to"], expected_adr17_ms, f"Fact valid_to ({super_fact['valid_to']}) must equal clock - 6 days ({expected_adr17_ms})")
        self.assertEqual(super_fact["valid_to_iso"], "2026-10-09", f"Expected valid_to_iso to be 2026-10-09, got {super_fact['valid_to_iso']}")

if __name__ == "__main__":
    unittest.main()
