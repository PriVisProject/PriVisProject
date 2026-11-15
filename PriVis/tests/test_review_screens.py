from datetime import date
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest

from PySide6.QtWidgets import QApplication

from data_loader import DEFAULT_DATA_FOLDER
from main_window import MainWindow


class ReviewScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow(review_date=date(2026, 11, 14))
        self.addCleanup(self.window.close)
        self.window.show()
        self.wait_for_load()

    def wait_for_load(self):
        deadline = monotonic() + 5
        while self.window._load_thread is not None and monotonic() < deadline:
            self.app.processEvents()
            sleep(0.005)
        self.assertIsNone(self.window._load_thread)

    def test_overview_metrics_and_risk_distribution(self):
        overview = self.window.overview
        self.assertEqual([label.text() for label in overview.metrics], ["12", "8", "5", "3"])
        self.assertEqual([label.text() for label in overview.legend.values()],
                         ["Critical · 1", "High · 2", "Medium · 1", "Low · 1"])

    def test_user_search_and_status_filter(self):
        users = self.window.users
        users.search.setText("TMORGAN")
        self.assertEqual(users.proxy.rowCount(), 1)
        self.assertIn("Server-Admins", users.detail.toPlainText())
        self.assertIn("Findings (2)", users.detail.toPlainText())
        users.category.setCurrentText("Disabled")
        self.assertEqual(users.proxy.rowCount(), 0)
        self.assertEqual(users.detail.toPlainText(), "No matching rows.")
        users.search.clear()
        self.assertEqual(users.proxy.rowCount(), 1)
        self.assertIn("Devon Reed", users.detail.toPlainText())

    def test_group_members_and_policy_details(self):
        groups = self.window.groups
        groups.search.setText("server-admins")
        self.assertEqual(groups.proxy.rowCount(), 1)
        self.assertIn("Taylor Morgan (tmorgan)", groups.detail.toPlainText())
        findings = self.window.findings
        findings.category.setCurrentText("Critical")
        self.assertEqual(findings.proxy.rowCount(), 1)
        self.assertIn("IT Contractor / G003 / Approval Required", findings.detail.toPlainText())
        for label in ("Account:", "Group:", "Matching Rule:", "Explanation:", "Review Recommendation:"):
            with self.subTest(label=label):
                text = findings.detail.document().find(label)
                self.assertFalse(text.isNull())
                self.assertGreaterEqual(text.charFormat().fontWeight(), 700)
        body = findings.detail.document().find("Taylor Morgan")
        self.assertLess(body.charFormat().fontWeight(), 700)

    def test_invalid_folder_preserves_last_successful_review(self):
        with TemporaryDirectory() as folder:
            self.window.load_folder(folder)
            self.wait_for_load()
        self.assertIn("users.csv", self.window.load_error.text())
        self.assertEqual(self.window.users.proxy.rowCount(), 12)
        self.assertEqual(self.window.data_folder, DEFAULT_DATA_FOLDER)
        self.assertTrue(self.window.open_folder.isEnabled())

    def test_simulation_preview_and_reset_preserve_live_findings(self):
        simulator = self.window.simulations
        simulator.user.setCurrentIndex(simulator.user.findData("U003"))
        self.assertEqual(simulator.membership.count(), 3)
        simulator.membership.setCurrentIndex(simulator.membership.findData("G003"))
        simulator.preview_button.click()
        self.assertIn("5 before → 4 after", simulator.summary.text())
        self.assertIn("Selected account after (1):\nHigh · Expired enabled account",
                      simulator.details.toPlainText())
        document = simulator.details.document()
        self.assertGreaterEqual(document.find("Selected account after (1):").charFormat().fontWeight(), 700)
        self.assertLess(document.find("Expired enabled account").charFormat().fontWeight(), 700)
        self.assertEqual(self.window.findings.proxy.rowCount(), 5)
        simulator.reset_button.click()
        self.assertIn("Baseline: 5 findings", simulator.summary.text())
        self.assertEqual(simulator.details.toPlainText(), "")
        self.assertFalse(simulator.preview_button.isEnabled())

    def test_advanced_shows_policy_and_approval_evidence_for_selected_membership(self):
        page = self.window.advanced
        self.assertEqual(page.evidence.proxy.rowCount(), 30)
        self.assertIn("30 of 30", page.coverage_summary.text())
        self.assertEqual(page.gaps.proxy.rowCount(), 0)
        page.evidence.search.setText("tmorgan")
        page.evidence.category.setCurrentText("Approval Required")
        self.assertEqual(page.evidence.proxy.rowCount(), 1)
        detail = page.evidence.detail.toPlainText()
        self.assertIn("IT Contractor / G003 / Approval Required", detail)
        self.assertIn("Status: Missing", detail)
        self.assertIn("Critical · Approval required", detail)
        self.assertNotIn("Expired enabled account", detail)

    def test_advanced_coverage_lists_membership_without_policy(self):
        from dataclasses import replace

        from data_loader import load_dataset
        from review_pages import ReviewData

        dataset = load_dataset()
        policy = dataset.access_policy
        keep = ~(policy["role"].eq("IT Contractor") & policy["group_id"].eq("G003"))
        review = ReviewData(replace(dataset, access_policy=policy.loc[keep]), date(2026, 11, 14))
        page = self.window.advanced
        page.set_data(review)
        self.assertIn("29 of 30", page.coverage_summary.text())
        self.assertEqual(page.gaps.proxy.rowCount(), 1)
        self.assertIn("Server-Admins", page.gaps.detail.toPlainText())
        self.assertIn("No matching policy", page.gaps.detail.toPlainText())
        self.assertIn("No finding linked", page.gaps.detail.toPlainText())

    def test_advanced_executes_selected_and_all_fixes_only_in_sandbox(self):
        page = self.window.advanced.solutions
        original = page.review.dataset
        page.actions.category.setCurrentText("Critical")
        self.assertEqual(page.actions.proxy.rowCount(), 1)
        page.highlighted.click()
        self.assertIn("5 before → 4 after", page.results.text())
        self.assertIn("expired_account", [finding.rule for finding in page.remaining])
        page.all_fixes.click()
        self.assertIn("4 before → 0 after", page.results.text())
        self.assertFalse(page.all_fixes.isEnabled())
        self.assertEqual(self.window.findings.proxy.rowCount(), 5)
        self.assertEqual(len(original.memberships), 30)
        self.assertTrue(original.users.set_index("user_id").loc["U003", "enabled"])
        page.set_data(page.review)
        self.assertEqual(len(page.remaining), 5)
