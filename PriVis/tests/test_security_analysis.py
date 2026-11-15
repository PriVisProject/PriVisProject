from dataclasses import replace
from datetime import date
import unittest

from data_loader import load_dataset
from security_analysis import analyze_findings


class SecurityAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.dataset = load_dataset()
        self.review_date = date(2026, 11, 14)

    def findings(self):
        return analyze_findings(self.dataset, review_date=self.review_date)

    def update_membership(self, user_id, group_id, **values):
        memberships = self.dataset.memberships.copy()
        selected = memberships["user_id"].eq(user_id) & memberships["group_id"].eq(group_id)
        self.assertEqual(selected.sum(), 1)
        for column, value in values.items():
            memberships.loc[selected, column] = value
        self.dataset = replace(self.dataset, memberships=memberships)

    def test_sample_findings_and_order(self):
        findings = self.findings()
        self.assertEqual(
            [(item.severity, item.user_id, item.group_id, item.rule) for item in findings],
            [
                ("Critical", "U003", "G003", "approval_required"),
                ("High", "U001", "G002", "denied_membership"),
                ("High", "U003", None, "expired_account"),
                ("Medium", "U005", "G005", "denied_membership"),
                ("Low", "U010", "G008", "approval_required"),
            ],
        )
        self.assertEqual(findings[0].policy_decision, "Approval Required")
        self.assertIn("time-limited exception", findings[0].policy_reason)
        self.assertIsNone(findings[2].policy_decision)

    def test_end_date_boundary(self):
        self.review_date = date(2026, 11, 1)
        self.assertFalse(any(item.rule == "expired_account" for item in self.findings()))
        self.review_date = date(2026, 11, 2)
        self.assertTrue(any(item.rule == "expired_account" for item in self.findings()))

    def test_disabled_account_is_excluded_from_all_rules(self):
        users = self.dataset.users.copy()
        users.loc[users["user_id"].isin(["U001", "U003"]), "enabled"] = False
        self.dataset = replace(self.dataset, users=users)
        self.assertEqual([item.user_id for item in self.findings()], ["U005", "U010"])

    def test_approval_boundary(self):
        self.review_date = date(2026, 12, 15)
        self.assertFalse(any(item.user_id == "U008" for item in self.findings()))
        self.review_date = date(2026, 12, 16)
        finding = next(item for item in self.findings() if item.user_id == "U008")
        self.assertEqual(finding.rule, "approval_required")
        self.assertIn("expired on 2026-12-15", finding.explanation)

    def test_approved_status_requires_ticket_and_expiry(self):
        for column, missing in (("approval_ticket", ""), ("approval_expires", None)):
            with self.subTest(column=column):
                self.dataset = load_dataset()
                self.update_membership("U008", "G005", **{column: missing})
                finding = next(item for item in self.findings() if item.user_id == "U008")
                self.assertIn("missing a ticket or expiry date", finding.explanation)

    def test_approval_does_not_override_explicit_deny(self):
        self.update_membership(
            "U001", "G002", approval_status="Approved",
            approval_ticket="APR-123", approval_expires=date(2026, 12, 15),
        )
        finding = next(item for item in self.findings() if item.user_id == "U001")
        self.assertEqual(finding.rule, "denied_membership")

    def test_unmatched_policy_yields_no_membership_finding(self):
        policy = self.dataset.access_policy
        keep = ~(policy["role"].eq("Support Rep") & policy["group_id"].eq("G002"))
        self.dataset = replace(self.dataset, access_policy=policy.loc[keep])
        self.assertFalse(any(item.user_id == "U001" for item in self.findings()))

    def test_analysis_does_not_change_input_tables(self):
        tables = vars(self.dataset)
        before = {name: table.copy(deep=True) for name, table in tables.items()}
        first = self.findings()
        self.assertEqual(self.findings(), first)
        for name, table in tables.items():
            self.assertTrue(table.equals(before[name]), name)
