from hashlib import sha256
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

from startup import StartupDialog


class StartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        passwords = {"01021999": "FirstDemo123!", "12345678": "SecondDemo123"}
        credentials = {user: sha256(password.encode()).hexdigest() for user, password in passwords.items()}
        replacement = patch("startup.ADMIN_PASSWORD_DIGESTS", credentials)
        replacement.start()
        self.addCleanup(replacement.stop)

    def test_demo_startup_and_sign_in(self):
        dialog = StartupDialog()
        self.addCleanup(dialog.close)
        dialog.animation.setDuration(20)
        dialog.show()
        self.assertFalse(dialog.progress.isTextVisible())
        self.assertIsNot(dialog.pages.currentWidget(), dialog.login)
        QTest.qWait(120)
        self.assertEqual(dialog.progress.value(), 100)
        self.assertIs(dialog.pages.currentWidget(), dialog.mode)
        dialog.demo_button.click()
        self.assertIs(dialog.pages.currentWidget(), dialog.login)
        self.assertFalse(dialog.start_empty)

        QTest.keyClicks(dialog.user_id, "a0102 19990")
        self.assertEqual(dialog.user_id.text(), "01021999")
        dialog.password.setText("short")
        QTest.keyClick(dialog.password, Qt.Key.Key_Return)
        self.assertEqual(dialog.error.text(), "Invalid User ID or Password")
        self.assertTrue(dialog.isVisible())

        dialog.password.setText("SecondDemo123")
        QTest.keyClick(dialog.password, Qt.Key.Key_Return)
        self.assertEqual(dialog.error.text(), "Invalid User ID or Password")
        dialog.password.setText("FirstDemo123!")
        QTest.keyClick(dialog.password, Qt.Key.Key_Return)
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(dialog.password.text(), "")

    def test_new_import_mode_carries_choice_through_sign_in(self):
        dialog = StartupDialog()
        self.addCleanup(dialog.close)
        dialog.show_mode()
        dialog.import_button.click()
        dialog.user_id.setText("12345678")
        dialog.password.setText("SecondDemo123")
        dialog.validate_login()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertTrue(dialog.start_empty)
