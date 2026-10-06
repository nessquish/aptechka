"""Тесты готовых экранов: повторное открытие раздела мгновенное."""

import sys
import unittest
from unittest import mock

from pharmacy.db.connection import Database
from pharmacy.ui import freeze, sections
from pharmacy.ui.screens import shell as shell_module
from tests.test_ui_freeze import FakeUser32
from tests.test_ui_shell import ShellTestCase


class DataVersionTest(ShellTestCase):
    def test_version_grows_only_when_data_changes(self):
        db = self.services.db
        self.assertIsInstance(db, Database)
        before = self.services.data_version
        db.fetch_all("SELECT * FROM products")
        self.assertEqual(self.services.data_version, before)
        db.execute("UPDATE products SET name = name")
        self.assertGreater(self.services.data_version, before)

    def test_failed_write_does_not_count(self):
        before = self.services.data_version
        with self.assertRaises(Exception):
            self.services.db.execute("INSERT INTO no_such_table VALUES (1)")
        self.assertEqual(self.services.data_version, before)


class ScreenCacheTest(ShellTestCase):
    def setUp(self):
        super().setUp()
        # Построение про запас запускаем вручную, а не по таймеру.
        self.shell.after_cancel(self.shell._prebuild_job)
        self.shell._prebuild_job = None

    def open(self, name):
        self.shell.navigate(name)
        self.settle()
        return self.shell._current

    def test_returning_to_a_section_shows_the_same_screen(self):
        first = self.open(sections.MY_KIT)
        self.open(sections.HISTORY)
        self.assertIs(self.open(sections.MY_KIT), first)

    def test_hidden_screen_is_kept_not_destroyed(self):
        first = self.open(sections.MY_KIT)
        self.open(sections.HISTORY)
        self.assertTrue(first.winfo_exists())
        self.assertFalse(first.winfo_manager())

    def test_only_the_current_screen_is_shown(self):
        self.open(sections.MY_KIT)
        self.open(sections.HISTORY)
        self.open(sections.MY_KIT)
        shown = [c for c in self.shell._content.winfo_children() if c.winfo_manager()]
        self.assertEqual(shown, [self.shell._current])

    def test_changed_data_rebuilds_the_screen(self):
        first = self.open(sections.MY_KIT)
        self.open(sections.HISTORY)
        self.services.db.execute("UPDATE products SET name = name")
        second = self.open(sections.MY_KIT)
        self.assertIsNot(second, first)
        self.assertFalse(first.winfo_exists())  # старый не копится

    def test_new_day_rebuilds_the_screen(self):
        first = self.open(sections.HOME)
        self.open(sections.HISTORY)
        with mock.patch.object(shell_module, "date", mock.Mock(today=lambda: "завтра")):
            self.assertIsNot(self.open(sections.HOME), first)

    def test_fresh_navigation_rebuilds_even_without_changes(self):
        first = self.open(sections.SETTINGS)
        self.shell.navigate(sections.SETTINGS, fresh=True)
        self.settle()
        self.assertIsNot(self.shell._current, first)
        self.assertFalse(first.winfo_exists())

    def test_screens_with_parameters_are_not_reused(self):
        kit = self.open(sections.MY_KIT)
        self.shell.open_product(1)
        card = self.shell._current
        self.shell.navigate(sections.MY_KIT)
        self.settle()
        self.assertFalse(card.winfo_exists())  # карточку не копим
        self.assertIs(self.shell._current, kit)

    def test_filtered_kit_does_not_replace_the_plain_one(self):
        kit = self.open(sections.MY_KIT)
        self.shell.open_kit()
        self.settle()
        self.shell.navigate(sections.HOME)
        self.assertIs(self.open(sections.MY_KIT), kit)

    def test_one_time_notice_screen_is_not_remembered(self):
        self.shell.notice = "Сохранено"
        first = self.open(sections.SETTINGS)
        self.open(sections.HOME)
        self.assertIsNot(self.open(sections.SETTINGS), first)

    def test_sidebar_counter_is_refreshed_for_a_ready_screen(self):
        self.open(sections.HOME)
        self.open(sections.HISTORY)
        with mock.patch.object(self.shell, "refresh_counters") as refresh:
            self.open(sections.HOME)
        refresh.assert_called_once()


class PrebuildTest(ShellTestCase):
    def setUp(self):
        super().setUp()
        self.shell.after_cancel(self.shell._prebuild_job)
        self.shell._prebuild_job = None

    def prebuild_all(self):
        for _ in range(len(self.shell._sections) + 1):
            self.shell._prebuild_next()

    def test_every_section_is_built_ahead(self):
        self.prebuild_all()
        self.assertEqual(set(self.shell._ready), set(self.shell._sections))

    def test_prebuilt_screens_stay_hidden(self):
        self.prebuild_all()
        shown = [c for c in self.shell._content.winfo_children() if c.winfo_manager()]
        self.assertEqual(shown, [self.shell._current])

    def test_opening_a_prebuilt_section_builds_nothing(self):
        self.prebuild_all()
        factory = mock.Mock()
        self.shell._sections[sections.HISTORY] = factory
        self.shell.navigate(sections.HISTORY)
        factory.assert_not_called()
        self.assertTrue(self.shell._current.winfo_manager())

    def test_changed_data_is_rebuilt_in_the_background(self):
        self.prebuild_all()
        old = self.shell._ready[sections.HISTORY][0]
        self.services.db.execute("UPDATE products SET name = name")
        self.prebuild_all()
        self.assertFalse(old.winfo_exists())
        self.assertIn(sections.HISTORY, self.shell._ready)

    def test_current_screen_is_never_rebuilt_under_the_user(self):
        self.prebuild_all()
        current = self.shell._current
        self.services.db.execute("UPDATE products SET name = name")
        self.prebuild_all()
        self.assertTrue(current.winfo_exists())
        self.assertIs(self.shell._current, current)

    def test_prebuild_is_scheduled_after_a_switch_and_chains(self):
        self.shell.navigate(sections.HISTORY)
        self.assertIsNotNone(self.shell._prebuild_job)
        self.shell._prebuild_next()
        self.assertIsNotNone(self.shell._prebuild_job)  # ещё есть что строить

    def test_prebuild_stops_when_everything_is_ready(self):
        self.prebuild_all()
        self.shell._prebuild_job = None
        self.shell._prebuild_next()
        self.assertIsNone(self.shell._prebuild_job)

    def test_prebuild_does_not_freeze_the_window(self):
        user32 = FakeUser32()
        with mock.patch.object(freeze, "_user32", return_value=user32):
            with mock.patch.object(sys, "platform", "win32"):
                self.prebuild_all()
        self.assertEqual(user32.calls, [])

    def test_closing_the_shell_cancels_the_prebuild(self):
        self.shell.navigate(sections.HISTORY)
        job = self.shell._prebuild_job
        self.assertIsNotNone(job)
        self.shell.destroy()
        self.assertIsNone(self.shell._prebuild_job)

    def test_late_timer_after_close_is_harmless(self):
        self.shell.destroy()
        self.shell._prebuild_next()


if __name__ == "__main__":
    unittest.main()
