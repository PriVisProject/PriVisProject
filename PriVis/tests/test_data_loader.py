from datetime import date
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from data_loader import DEFAULT_DATA_FOLDER, DataValidationError, load_dataset


class DataLoaderTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name) / "sample"
        shutil.copytree(DEFAULT_DATA_FOLDER, self.folder)

    def replace_text(self, name, old, new):
        path = self.folder / name
        contents = path.read_text(encoding="utf-8")
        self.assertIn(old, contents)
        path.write_text(contents.replace(old, new, 1), encoding="utf-8")

    def append_row(self, name, row):
        with (self.folder / name).open("a", encoding="utf-8", newline="") as source:
            source.write(row + "\r\n")

    def test_sample_values_and_read_only_load(self):
        before = {file: file.read_bytes() for file in self.folder.iterdir()}
        data = load_dataset(self.folder)
        self.assertEqual(
            [len(data.users), len(data.groups), len(data.memberships), len(data.access_policy)],
            [12, 8, 30, 26],
        )
        users = data.users.set_index("user_id")
        self.assertFalse(users.loc["U012", "enabled"])
        self.assertEqual(users.loc["U003", "end_date"], date(2026, 11, 1))
        self.assertIsNone(users.loc["U001", "end_date"])
        approval = data.memberships.set_index(["user_id", "group_id"]).loc[("U008", "G005")]
        self.assertEqual(approval["approval_ticket"], "APR-2026-014")
        self.assertEqual(approval["approval_expires"], date(2026, 12, 15))
        self.assertEqual(before, {file: file.read_bytes() for file in self.folder.iterdir()})

    def test_missing_file(self):
        (self.folder / "users.csv").unlink()
        with self.assertRaisesRegex(DataValidationError, "users.csv.*expected a CSV file"):
            load_dataset(self.folder)

    def test_invalid_header(self):
        self.replace_text("groups.csv", "group_name", "group_id")
        with self.assertRaisesRegex(DataValidationError, "groups.csv.*expected these columns"):
            load_dataset(self.folder)

    def test_invalid_boolean_and_date(self):
        self.replace_text("users.csv", "TRUE,2026-11-01", "yes,2026-02-30")
        with self.assertRaisesRegex(DataValidationError, "users.csv:4: enabled"):
            load_dataset(self.folder)
        self.replace_text("users.csv", "yes,2026-02-30", "TRUE,2026-02-30")
        with self.assertRaisesRegex(DataValidationError, "users.csv:4: end_date"):
            load_dataset(self.folder)

    def test_duplicate_membership(self):
        self.append_row("memberships.csv", "U001,G001,Not Required,,")
        with self.assertRaisesRegex(DataValidationError, "memberships.csv:32: duplicate key"):
            load_dataset(self.folder)

    def test_duplicate_policy(self):
        self.append_row("access_policy.csv", "Support Rep,G001,Denied,Conflicting rule")
        with self.assertRaisesRegex(DataValidationError, "access_policy.csv:28: duplicate key"):
            load_dataset(self.folder)

    def test_unknown_group(self):
        self.append_row("memberships.csv", "U001,G999,Missing,,")
        with self.assertRaisesRegex(DataValidationError, "memberships.csv:32: group_id"):
            load_dataset(self.folder)

    def test_invalid_utf8(self):
        (self.folder / "users.csv").write_bytes(b"\xff")
        with self.assertRaisesRegex(DataValidationError, "users.csv.*UTF-8"):
            load_dataset(self.folder)

    def test_malformed_csv(self):
        self.append_row("groups.csv", 'G009,"unterminated')
        with self.assertRaisesRegex(DataValidationError, "groups.csv.*invalid CSV"):
            load_dataset(self.folder)

    def test_approval_evidence_can_be_missing(self):
        self.replace_text("memberships.csv", "APR-2026-014,2026-12-15", ",")
        data = load_dataset(self.folder)
        approval = data.memberships.set_index(["user_id", "group_id"]).loc[("U008", "G005")]
        self.assertEqual(approval["approval_status"], "Approved")
        self.assertEqual(approval["approval_ticket"], "")
        self.assertIsNone(approval["approval_expires"])
