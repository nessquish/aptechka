"""Тесты размера текста, предпочтений и сворачивания боковой панели."""

import json
import tempfile
import unittest
from pathlib import Path

from pharmacy.ui import fonts, sections, theme
from pharmacy.ui.preferences import Preferences
from pharmacy.ui.screens.settings import SettingsScreen
from pharmacy.ui.widgets.iconbutton import IconButton
from tests.test_ui_shell import ShellTestCase, find_all
from tests.test_ui_widgets import WidgetTestCase


class PreferencesTest(unittest.TestCase):
    def path(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name) / "preferences.json"

    def test_defaults_when_nothing_is_saved(self):
        prefs = Preferences(self.path())
        self.assertEqual(prefs.get(1, "text_size", "normal"), "normal")
        self.assertIsNone(prefs.get(1, "anything"))

    def test_saves_to_file_and_loads_back(self):
        path = self.path()
        Preferences(path).set(1, "text_size", "large")
        self.assertEqual(Preferences(path).get(1, "text_size"), "large")
        self.assertEqual(
            json.loads(path.read_text(encoding="utf-8"))["1"]["text_size"], "large"
        )

    def test_every_user_has_own_values(self):
        prefs = Preferences(self.path())
        prefs.set(1, "text_size", "large")
        prefs.set(2, "text_size", "medium")
        self.assertEqual(prefs.get(1, "text_size"), "large")
        self.assertEqual(prefs.get(2, "text_size"), "medium")
        self.assertIsNone(prefs.get(3, "text_size"))

    def test_keys_do_not_overwrite_each_other(self):
        prefs = Preferences(self.path())
        prefs.set(1, "text_size", "large")
        prefs.set(1, "sidebar_collapsed", True)
        self.assertEqual(prefs.get(1, "text_size"), "large")
        self.assertTrue(prefs.get(1, "sidebar_collapsed"))

    def test_in_memory_mode_writes_nothing(self):
        prefs = Preferences()
        prefs.set(1, "text_size", "large")
        self.assertEqual(prefs.get(1, "text_size"), "large")

    def test_broken_file_is_ignored(self):
        path = self.path()
        path.write_text("{не json", encoding="utf-8")
        prefs = Preferences(path)
        self.assertEqual(prefs.get(1, "text_size", "normal"), "normal")
        prefs.set(1, "text_size", "large")  # и после этого всё работает
        self.assertEqual(Preferences(path).get(1, "text_size"), "large")

    def test_unexpected_json_shape_is_ignored(self):
        path = self.path()
        path.write_text(json.dumps(["не", "словарь"]), encoding="utf-8")
        self.assertIsNone(Preferences(path).get(1, "text_size"))
        path.write_text(json.dumps({"1": "строка"}), encoding="utf-8")
        self.assertIsNone(Preferences(path).get(1, "text_size"))

    def test_creates_missing_folder(self):
        path = self.path().parent / "nested" / "p.json"
        Preferences(path).set(1, "k", 1)
        self.assertTrue(path.is_file())


class TextScaleTest(unittest.TestCase):
    def tearDown(self):
        theme.set_text_size("normal")

    def test_normal_keeps_the_design_sizes(self):
        theme.set_text_size("normal")
        for size in (10, 11, 12, 13, 18, 21):
            self.assertEqual(theme.scaled(size), size)

    def test_larger_sizes_grow_modestly(self):
        theme.set_text_size("medium")
        medium = theme.scaled(12)
        theme.set_text_size("large")
        large = theme.scaled(12)
        self.assertEqual((medium, large), (13, 14))
        self.assertLessEqual(large, 12 * 1.25)

    def test_every_style_gets_bigger_with_each_step(self):
        for style, (size, _weight) in theme.TYPOGRAPHY.items():
            theme.set_text_size("normal")
            normal = theme.scaled(size)
            theme.set_text_size("medium")
            medium = theme.scaled(size)
            theme.set_text_size("large")
            large = theme.scaled(size)
            self.assertLess(normal, medium, style)
            self.assertLessEqual(medium, large, style)

    def test_unknown_size_is_rejected(self):
        with self.assertRaises(ValueError):
            theme.set_text_size("huge")
        self.assertEqual(theme.text_size_name(), "normal")

    def test_font_spec_follows_the_size(self):
        theme.set_text_size("normal")
        normal = fonts.font_spec("body")[1]
        theme.set_text_size("large")
        self.assertEqual(fonts.font_spec("body")[1], -theme.scaled(12))
        self.assertLess(
            fonts.font_spec("body")[1], normal
        )  # размер отрицательный: пиксели

    def test_window_and_sidebar_grow_with_text(self):
        theme.set_text_size("normal")
        base = (theme.window_width(), theme.sidebar_width())
        self.assertEqual(base, (theme.WINDOW_WIDTH, theme.SIDEBAR_WIDTH))
        theme.set_text_size("large")
        self.assertGreater(theme.window_width(), base[0])
        self.assertGreater(theme.sidebar_width(), base[1])


class TextSizeInAppTest(ShellTestCase):
    def tearDown(self):
        theme.set_text_size("normal")

    def pick(self, index):
        page = self.shell._current
        page._text_size._on_click(
            type("E", (), {"x": page._text_size._spans[index][0] + 5})()
        )
        self.settle()

    def open_settings(self):
        self.shell.navigate(sections.SETTINGS)
        self.settle()

    def test_settings_offer_three_sizes(self):
        self.open_settings()
        page = self.shell._current
        self.assertIsInstance(page, SettingsScreen)
        self.assertEqual(page._text_size._items, ["Обычный", "Средний", "Большой"])
        self.assertEqual(page._text_size.active, 0)

    def test_choice_applies_at_once_and_is_remembered(self):
        self.open_settings()
        self.pick(2)
        self.assertEqual(theme.text_size_name(), "large")
        self.assertEqual(
            self.app.preferences.get(self.app.user.id, "text_size"), "large"
        )
        self.assertEqual(self.app._screen.section, sections.SETTINGS)
        self.assertEqual(self.app._screen._current._text_size.active, 2)

    def test_window_widens_for_larger_text(self):
        self.open_settings()
        before = self.app.winfo_width()
        self.pick(2)
        self.assertGreater(self.app.winfo_width(), before)
        self.assertGreaterEqual(
            self.app.winfo_width(),
            min(theme.window_width(), self.app.winfo_screenwidth() - 40),
        )

    def test_text_really_gets_bigger(self):
        before = fonts.font_spec("body", self.app)[1]
        self.open_settings()
        self.pick(1)
        self.assertLess(fonts.font_spec("body", self.app)[1], before)

    def test_selecting_the_same_size_does_nothing(self):
        self.open_settings()
        shell = self.app._screen
        shell.set_text_size("normal")
        self.assertIs(self.app._screen, shell)

    def test_size_is_restored_at_the_next_sign_in(self):
        self.open_settings()
        self.pick(1)
        self.app.sign_out()
        self.settle()
        self.assertEqual(theme.text_size_name(), "normal")  # на экране входа обычный
        user = self.services.auth.login("nessquish", "demo12345")
        self.app.sign_in(user, "demo12345")
        self.settle()
        self.assertEqual(theme.text_size_name(), "medium")

    def test_broken_saved_value_falls_back_to_normal(self):
        self.app.preferences.set(self.app.user.id, "text_size", "gigantic")
        self.app.apply_user_changes(self.app.user, start=sections.HOME)
        self.settle()
        self.assertEqual(theme.text_size_name(), "normal")

    def test_every_screen_builds_at_the_largest_size(self):
        self.open_settings()
        self.pick(2)
        shell = self.app._screen
        for name in sections.ALL:
            shell.navigate(name)
            self.settle()
        shell.open_product_form()
        self.settle()


class SidebarCollapseTest(ShellTestCase):
    def collapse_button(self):
        return [w for w in find_all(self.shell._sidebar, IconButton)][0]

    def test_sidebar_is_open_by_default(self):
        self.assertFalse(self.shell.sidebar_collapsed)
        self.assertTrue(self.shell._sidebar.winfo_ismapped())
        self.assertFalse(self.shell._rail.winfo_ismapped())

    def test_collapse_hides_the_sidebar_and_shows_the_rail(self):
        self.collapse_button()._command()
        self.settle()
        self.assertTrue(self.shell.sidebar_collapsed)
        self.assertFalse(self.shell._sidebar.winfo_ismapped())
        self.assertTrue(self.shell._rail.winfo_ismapped())

    def test_rail_button_expands_it_back(self):
        self.shell.set_sidebar_collapsed(True)
        self.settle()
        rail_button = find_all(self.shell._rail, IconButton)[0]
        rail_button._command()
        self.settle()
        self.assertFalse(self.shell.sidebar_collapsed)
        self.assertTrue(self.shell._sidebar.winfo_ismapped())
        self.assertFalse(self.shell._rail.winfo_ismapped())

    def test_content_gets_the_freed_space(self):
        before = self.shell._scroll.winfo_width()
        self.shell.set_sidebar_collapsed(True)
        self.settle()
        self.assertGreater(self.shell._scroll.winfo_width(), before + 100)

    def test_choice_is_remembered_and_restored(self):
        self.shell.set_sidebar_collapsed(True)
        self.assertTrue(self.app.preferences.get(self.app.user.id, "sidebar_collapsed"))
        self.app.apply_user_changes(self.app.user, start=sections.HOME)
        self.settle()
        self.assertTrue(self.app._screen.sidebar_collapsed)
        self.assertTrue(self.app._screen._rail.winfo_ismapped())

    def test_collapsing_twice_changes_nothing(self):
        self.shell.set_sidebar_collapsed(True)
        self.shell.set_sidebar_collapsed(True)
        self.settle()
        self.assertTrue(self.shell._rail.winfo_ismapped())

    def test_navigation_keeps_working_when_collapsed(self):
        self.shell.set_sidebar_collapsed(True)
        self.shell.navigate(sections.HISTORY)
        self.settle()
        self.assertEqual(self.shell.section, sections.HISTORY)

    def test_other_users_keep_their_own_state(self):
        self.shell.set_sidebar_collapsed(True)
        self.assertFalse(self.app.preferences.get(999, "sidebar_collapsed", False))


class IconButtonTest(WidgetTestCase):
    def test_click_runs_the_command(self):
        calls = []
        button = IconButton(self.root, "panel-left", lambda: calls.append(1))
        button.pack()
        self.settle()
        button.event_generate("<Button-1>", x=5, y=5)
        self.assertEqual(calls, [1])

    def test_hover_changes_the_look(self):
        button = IconButton(self.root, "panel-left", lambda: None)
        button.pack()
        self.settle()
        quiet = len(button.find_all())
        button.event_generate("<Enter>")
        self.assertGreater(len(button.find_all()), quiet)
        button.event_generate("<Leave>")
        self.assertEqual(len(button.find_all()), quiet)
