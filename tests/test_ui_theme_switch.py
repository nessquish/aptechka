"""Тесты переключения темы, ширины фильтров и гладких углов карточек."""

import tkinter as tk

from pharmacy.ui import sections, theme
from pharmacy.ui.fonts import text_width
from pharmacy.ui.screens.settings import SettingsScreen
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.field import ICON_INSET, ICON_SIZE
from pharmacy.ui.widgets.select import Select
from pharmacy.ui.widgets.table import Column, DataTable
from tests.test_ui_shell import ShellTestCase, find_all
from tests.test_ui_widgets import WidgetTestCase


class ThemeSwitchTest(ShellTestCase):
    def labels(self):
        return [w.cget("text") for w in find_all(self.shell, tk.Label)]

    def test_menu_offers_the_dark_theme(self):
        self.assertTrue(any("Тёмная тема" in t for t in self.labels()))

    def toggle(self):
        self.shell.toggle_theme()
        self.settle()

    def test_toggle_switches_to_dark_and_back(self):
        self.toggle()
        self.assertEqual(theme.theme_name(), "dark")
        self.assertEqual(self.app.user.theme, "dark")
        self.assertTrue(any("Светлая тема" in t for t in self.labels()))
        self.toggle()
        self.assertEqual(theme.theme_name(), "light")
        self.assertEqual(self.app.user.theme, "light")

    def test_choice_is_saved_for_the_next_sign_in(self):
        self.toggle()
        saved = self.services.settings.get_user(self.app.user.id)
        self.assertEqual(saved.theme, "dark")

    def test_current_section_is_kept(self):
        self.shell.navigate(sections.HISTORY)
        self.settle()
        self.toggle()
        self.assertEqual(self.shell.section, sections.HISTORY)

    def test_colors_really_change(self):
        before = self.app._screen.cget("bg")
        self.toggle()
        self.assertNotEqual(self.app._screen.cget("bg"), before)
        self.assertEqual(self.app._screen.cget("bg"), theme.DARK.bg)

    def test_other_settings_survive_the_switch(self):
        self.db.execute("UPDATE users SET warning_days = 12, notify_low_stock = 0")
        self.app.user = self.services.settings.get_user(self.app.user.id)
        self.shell.user = self.app.user
        self.toggle()
        saved = self.services.settings.get_user(self.app.user.id)
        self.assertEqual((saved.warning_days, saved.notify_low_stock), (12, False))

    def test_setting_the_same_theme_does_nothing(self):
        shell = self.shell
        shell.set_theme("light")
        self.settle()
        self.assertIs(self.app._screen, shell)

    def test_settings_switch_applies_the_theme_at_once(self):
        self.shell.navigate(sections.SETTINGS)
        self.settle()
        page = self.shell._current
        self.assertIsInstance(page, SettingsScreen)
        page._theme._on_click(type("E", (), {"x": page._theme._spans[1][0] + 5})())
        self.settle()
        self.assertEqual(theme.theme_name(), "dark")
        self.assertIsInstance(self.app._screen._current, SettingsScreen)

    def test_every_screen_builds_in_the_dark_theme(self):
        self.toggle()
        for name in sections.ALL:
            self.app._screen.navigate(name)
            self.settle()
        self.app._screen.open_product_form()
        self.settle()


class CompactSelectWidthTest(WidgetTestCase):
    def test_text_never_runs_under_the_arrow(self):
        options = [("a", "срок годности"), ("b", "дата добавления"), ("c", "имя")]
        for value in ("a", "b", "c"):
            select = Select(
                self.root, options, value, compact=True, prefix="Сортировка: "
            )
            select.pack()
            self.settle()
            text = select._prefix + select._label_of(value)
            needed = (
                select._inset
                + text_width(select, text, "body")
                + ICON_SIZE
                + ICON_INSET
            )
            self.assertGreaterEqual(select._canvas.winfo_width() - 8, needed)
            select.destroy()

    def test_width_follows_the_chosen_value(self):
        select = Select(
            self.root,
            [("a", "имя"), ("b", "очень длинное название")],
            "a",
            compact=True,
        )
        select.pack()
        self.settle()
        short = select._canvas.winfo_width()
        select.set("b")
        self.settle()
        self.assertGreater(select._canvas.winfo_width(), short)


class SelectBorderTest(WidgetTestCase):
    OPTIONS = [(1, "Все категории"), (2, "Лекарства")]

    def make(self):
        select = Select(self.root, self.OPTIONS, 1, compact=True)
        select.pack()
        self.settle()
        return select

    def test_blue_border_only_while_the_list_is_open(self):
        select = self.make()
        self.assertEqual(select._colors()[0], theme.LIGHT.line)
        select._toggle(None)
        self.settle()
        self.assertEqual(select._colors()[0], theme.LIGHT.primary)
        select._popup.close()
        self.settle()
        self.assertEqual(select._colors()[0], theme.LIGHT.line)

    def test_border_is_normal_after_picking(self):
        select = self.make()
        select._toggle(None)
        self.settle()
        select._popup._on_pick(2)
        select._popup.close()
        self.settle()
        self.assertEqual(select._colors()[0], theme.LIGHT.line)

    def test_error_color_wins_over_open_state(self):
        select = self.make()
        select.set_error("Выберите")
        select._toggle(None)
        self.settle()
        self.assertEqual(select._colors()[0], theme.LIGHT.red)
        select._popup.close()

    def test_list_starts_below_the_field_and_does_not_cover_it(self):
        select = self.make()
        select._toggle(None)
        self.settle()
        canvas = select._canvas
        bottom = canvas.winfo_rooty() + canvas.winfo_height()
        self.assertGreaterEqual(select._popup.winfo_rooty(), bottom)
        select._popup.close()


class SmoothCornersTest(WidgetTestCase):
    def make_table(self):
        card = Card(self.root, flush=True)
        card.pack(fill="x")
        table = DataTable(card.body, [Column("Название", 1), Column("Срок", 1)], card)
        table.pack(fill="x")
        table.add_row(["Бинт", "01.01.2027"])
        self.settle()
        return card, table

    def test_card_returns_the_piece_under_a_widget(self):
        card, table = self.make_table()
        piece = card.capture(table._header)
        self.assertIsNotNone(piece)
        self.assertEqual(
            piece.size, (table._header.winfo_width(), table._header.winfo_height())
        )

    def test_capture_is_empty_before_the_card_is_drawn(self):
        card = Card(self.root)
        self.assertIsNone(card.capture(card.body))

    def test_corner_of_the_header_is_not_a_square_patch(self):
        card, table = self.make_table()
        piece = card.capture(table._header)
        # Крайний пиксель угла принадлежит краю карточки (светлее шапки), а не шапке.
        corner = piece.getpixel((0, 0))[:3]
        header = tuple(int(theme.LIGHT.table_head[i : i + 2], 16) for i in (1, 3, 5))
        self.assertNotEqual(corner, header)

    def test_header_redraws_when_the_card_is_redrawn(self):
        card, table = self.make_table()
        before = table._images[0]
        card._on_resize(
            type(
                "E", (), {"width": card.winfo_width(), "height": card.winfo_height()}
            )()
        )
        self.settle()
        self.assertIsNot(table._images[0], before)

    def test_card_paints_the_band_with_smooth_corners(self):
        card, table = self.make_table()
        flat = card._flat
        pad = card._shadow_pad
        head = tuple(int(theme.LIGHT.table_head[i : i + 2], 16) for i in (1, 3, 5))
        # В середине полосы цвет шапки, в самом углу - край карточки, не шапка.
        middle = flat.getpixel((flat.width // 2, pad + 6))[:3]
        self.assertEqual(middle, head)
        corner = flat.getpixel((pad + 1, pad + 1))[:3]
        self.assertNotEqual(corner, head)
        # Ниже полосы заливка карточки.
        below = flat.getpixel((flat.width // 2, pad + table._header_height + 10))[:3]
        self.assertNotEqual(below, head)

    def test_band_can_be_replaced_and_removed(self):
        card, table = self.make_table()
        pad = card._shadow_pad
        card.set_band(30, "#FF0000")
        self.assertEqual(
            card._flat.getpixel((card._flat.width // 2, pad + 5))[:3], (255, 0, 0)
        )
        card.set_band(0, None)
        self.assertNotEqual(
            card._flat.getpixel((card._flat.width // 2, pad + 5))[:3], (255, 0, 0)
        )

    def test_action_bar_takes_over_and_returns_the_band(self):
        from pharmacy.ui.widgets.actionbar import ActionBar

        card, table = self.make_table()
        bar = ActionBar(card.body, card)
        table.set_rounded_top(False)
        bar.show("Выбрано: 2", before=table)
        self.settle()
        pad = card._shadow_pad
        bulk = tuple(int(theme.LIGHT.bulk_bg[i : i + 2], 16) for i in (1, 3, 5))
        self.assertEqual(
            card._flat.getpixel((card._flat.width // 2, pad + 6))[:3], bulk
        )
        bar.hide()
        table.set_rounded_top(True)
        self.settle()
        head = tuple(int(theme.LIGHT.table_head[i : i + 2], 16) for i in (1, 3, 5))
        self.assertEqual(
            card._flat.getpixel((card._flat.width // 2, pad + 6))[:3], head
        )

    def test_highlight_row_has_a_rounded_chip(self):
        from pharmacy.ui.widgets.highlight import Highlight

        row = Highlight(self.root, "#FAFAFF")
        row.pack(fill="x")
        tk.Label(row.body, text="текст", bg="#FAFAFF").pack()
        self.settle()
        self.assertIsNotNone(row._image)
        self.assertEqual(
            row.winfo_height(), row.body.winfo_reqheight() + 2 * Highlight.padding_y
        )

    def test_table_works_without_a_card(self):
        table = DataTable(self.root, [Column("Название", 1)])
        table.pack(fill="x")
        self.settle()
        table.add_row(["Бинт"])
        self.assertTrue(table._header.find_all())
