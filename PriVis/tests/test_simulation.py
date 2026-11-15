from dataclasses import replace
from datetime import date
import unittest

from data_loader import load_dataset
from security_analysis import analyze_findings
from simulation import preview_removal


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.dataset = load_dataset()
        self.review_date = date(2026, 11, 14)

    def test_removal_matches_full_reanalysis_and_preserves_memberships(self):
        original = self.dataset.memberships.copy()
        mask = original["user_id"].eq("U003") & original["group_id"].eq("G003")
        simulated = replace(self.dataset, memberships=original.loc[~mask])
        result = preview_removal(
            self.dataset, user_id="U003", group_id="G003", review_date=self.review_date,
        )
        self.assertEqual(len(result.before), 5)
        self.assertEqual(result.after, tuple(analyze_findings(simulated, review_date=self.review_date)))
        self.assertEqual([f.rule for f in result.cleared], ["approval_required"])
        self.assertTrue(any(f.rule == "expired_account" for f in result.after))
        self.assertEqual(result.added, ())
        self.assertTrue(self.dataset.memberships.equals(original))

    def test_allowed_membership_removal_leaves_findings_unchanged(self):
        baseline = tuple(analyze_findings(self.dataset, review_date=self.review_date))
        result = preview_removal(
            self.dataset, user_id="U002", group_id="G003",
            review_date=self.review_date, baseline=baseline,
        )
        self.assertEqual(result.after, baseline)
        self.assertEqual(result.cleared, ())

    def test_invalid_membership_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "current direct membership"):
            preview_removal(
                self.dataset, user_id="U003", group_id="G002", review_date=self.review_date,
            )
