"""Тесты заморозки отрисовки окна при перестроении интерфейса."""

import sys
import tkinter as tk
import unittest
from unittest import mock

from pharmacy.ui import freeze, sections
from pharmacy.ui.freeze import frozen, frozen_window
from tests.test_ui_shell import ShellTestCase
from tests.test_ui_widgets import WidgetTestCase


class FakeUser32:
    """Подмена системной библиотеки: записывает вызовы вместо настоящих."""

    def __init__(self, lock_result=1):
        self.calls = []
        self.lock_result = lock_result

    def GetParent(self, handle):
        return handle + 1000

    def LockWindowUpdate(self, handle):
        self.calls.append(("lock", handle))
        return self.lock_result if handle else 1

    def RedrawWindow(self, handle, rect, region, flags):
        self.calls.append(("redraw", handle, flags))
        return 1


class FreezeTest(WidgetTestCase):
    def setUp(self):
        super().setUp()
        self.user32 = FakeUser32()
        patcher = mock.patch.object(freeze, "_user32", return_value=self.user32)
        patcher.start()
        self.addCleanup(patcher.stop)
        windows = mock.patch.object(sys, "platform", "win32")
        windows.start()
        self.addCleanup(windows.stop)
        self.assertEqual(freeze._depth, 0)

    def names(self):
        return [call[0] for call in self.user32.calls]

    def test_window_is_locked_during_the_block_and_redrawn_after(self):
        seen = []
        with frozen_window(self.root):
            seen.append(list(self.user32.calls))
        self.assertEqual(self.names(), ["lock", "lock", "redraw"])
        self.assertEqual(seen[0][0][0], "lock")
        self.assertNotEqual(seen[0][0][1], 0)  # во время блока окно заблокировано
        self.assertEqual(self.user32.calls[1], ("lock", 0))  # потом разблокировано
        self.assertEqual(
            self.user32.calls[2][2], freeze._REDRAW_FLAGS
        )  # и нарисовано целиком

    def test_redraw_covers_the_window_and_all_children(self):
        flags = freeze._REDRAW_FLAGS
        for flag in (
            freeze._RDW_INVALIDATE,
            freeze._RDW_ERASE,
            freeze._RDW_ALLCHILDREN,
            freeze._RDW_UPDATENOW,
        ):
            self.assertTrue(flags & flag)

    def test_nested_blocks_lock_and_unlock_only_once(self):
        with frozen_window(self.root):
            with frozen_window(self.root):
                with frozen_window(self.root):
                    pass
        self.assertEqual(self.names(), ["lock", "lock", "redraw"])
        self.assertEqual(freeze._depth, 0)

    def test_failed_lock_just_runs_the_block(self):
        self.user32.lock_result = 0
        ran = []
        with frozen_window(self.root):
            ran.append(1)
        self.assertEqual(ran, [1])
        self.assertEqual(self.names(), ["lock"])  # разблокировать нечего

    def test_error_inside_the_block_still_unfreezes_the_window(self):
        with self.assertRaises(ValueError):
            with frozen_window(self.root):
                raise ValueError("сломалось")
        self.assertEqual(self.names(), ["lock", "lock", "redraw"])
        self.assertEqual(freeze._depth, 0)

    def test_closed_window_does_not_break_the_block(self):
        window = tk.Tk()
        window.destroy()
        ran = []
        with frozen_window(window):
            ran.append(1)
        self.assertEqual(ran, [1])
        self.assertEqual(self.user32.calls, [])

    def test_window_closed_during_the_block_is_safe(self):
        window = tk.Tk()
        with frozen_window(window):
            window.destroy()
        self.assertEqual(freeze._depth, 0)
        self.assertEqual(self.names()[-1], "redraw")

    def test_decorator_runs_the_method_frozen_and_returns_its_value(self):
        class Screen(tk.Frame):
            @frozen
            def rebuild(self, value):
                return value * 2, list(user32.calls)

        user32 = self.user32
        screen = Screen(self.root)
        result, calls_inside = screen.rebuild(21)
        self.assertEqual(result, 42)
        self.assertEqual(calls_inside[0][0], "lock")
        self.assertEqual(self.names(), ["lock", "lock", "redraw"])

    def test_decorator_keeps_the_method_name(self):
        class Screen(tk.Frame):
            @frozen
            def rebuild(self):
                """Описание."""

        self.assertEqual(Screen.rebuild.__name__, "rebuild")
        self.assertEqual(Screen.rebuild.__doc__, "Описание.")


class OtherSystemTest(WidgetTestCase):
    def test_does_nothing_outside_windows(self):
        user32 = FakeUser32()
        with mock.patch.object(freeze, "_user32", return_value=user32):
            with mock.patch.object(sys, "platform", "linux"):
                ran = []
                with frozen_window(self.root):
                    ran.append(1)
        self.assertEqual(ran, [1])
        self.assertEqual(user32.calls, [])


class InTheAppTest(ShellTestCase):
    """Смена экранов и перерисовка списков идут при замороженном окне."""

    def setUp(self):
        super().setUp()
        self.user32 = FakeUser32()
        for patcher in (
            mock.patch.object(freeze, "_user32", return_value=self.user32),
            mock.patch.object(sys, "platform", "win32"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def locks(self):
        return [c for c in self.user32.calls if c[0] == "lock" and c[1] != 0]

    def test_every_section_change_freezes_the_window_once(self):
        for name in sections.ALL:
            before = len(self.locks())
            self.shell.navigate(name)
            self.assertEqual(len(self.locks()) - before, 1, name)

    def test_window_is_always_unfrozen_afterwards(self):
        for name in sections.ALL * 2:
            self.shell.navigate(name)
        unlocks = [c for c in self.user32.calls if c == ("lock", 0)]
        self.assertEqual(len(unlocks), len(self.locks()))
        self.assertEqual(freeze._depth, 0)

    def test_login_and_logout_freeze_too(self):
        before = len(self.locks())
        self.app.sign_out()
        self.assertGreater(len(self.locks()), before)

    def test_table_reload_after_a_filter_is_frozen(self):
        self.shell.navigate(sections.MY_KIT)
        kit = self.shell._current
        before = len(self.locks())
        kit._on_status(None)
        self.assertEqual(len(self.locks()) - before, 1)

    def test_nested_reload_inside_a_screen_change_does_not_lock_twice(self):
        before = len(self.locks())
        self.shell.navigate(sections.NOTIFICATIONS)  # внутри строится список
        self.assertEqual(len(self.locks()) - before, 1)

    def test_other_reloading_screens_are_frozen(self):
        for name, action in (
            (sections.SHOPPING, lambda page: page._on_tab(1)),
            (sections.NOTIFICATIONS, lambda page: page._on_tab(1)),
            (sections.HISTORY, lambda page: page._on_action(None)),
        ):
            self.shell.navigate(name)
            page = self.shell._current
            before = len(self.locks())
            action(page)
            self.assertEqual(len(self.locks()) - before, 1, name)


if __name__ == "__main__":
    unittest.main()
