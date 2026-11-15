from time import monotonic, sleep
import unittest

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from main_window import MainWindow


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.addCleanup(self.window.close)
        self.window.show()
        deadline = monotonic() + 5
        while self.window._load_thread is not None and monotonic() < deadline:
            self.app.processEvents()
            sleep(0.005)

    def test_sidebar_opens_each_section_and_updates_selection(self):
        expected = ["Overview", "Users", "Groups", "Findings", "Simulations", "Advanced"]
        self.assertEqual(self.window.pages.count(), len(expected))
        self.assertEqual(self.window.pages.currentIndex(), 0)
        self.assertEqual(self.window.navigation.checkedId(), 0)
        for index in (1, 2, 3, 4, 5, 0):
            with self.subTest(section=expected[index]):
                button = self.window.navigation.button(index)
                self.assertEqual(button.text(), expected[index])
                QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                self.assertEqual(self.window.pages.currentIndex(), index)
                self.assertEqual(self.window.navigation.checkedId(), index)
                heading = self.window.pages.currentWidget().findChild(QLabel, "pageTitle")
                self.assertEqual(heading.text(), "Access Overview" if index == 0 else expected[index])
