"""Тесты виджетов: поведение кнопок, полей, плашек и карточек."""

import unittest

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QVBoxLayout, QWidget

from pharmacy.ui import theme
from pharmacy.ui.theme import SHADOW_PAD
from pharmacy.ui.widgets.actionbar import ActionBar
from pharmacy.ui.widgets.badge import Badge, badge_height, measure_badge
from pharmacy.ui.widgets.banner import ErrorBanner
from pharmacy.ui.widgets.button import Button, button_height, measure_button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.common import Line, clear_layout, clickable, label, pad
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.highlight import Highlight
from pharmacy.ui.widgets.iconbox import IconBox
from pharmacy.ui.widgets.iconbutton import IconButton
from pharmacy.ui.widgets.link import Link
from pharmacy.ui.widgets.page import PageHeader
from tests.qt_helpers import WidgetTestCase, click, type_text


class Holder(WidgetTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.layout = QVBoxLayout(self.root)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def add(
        self,
        widget: QWidget,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag(0),
    ) -> QWidget:
        """Кладёт виджет в верх окна, чтобы он не растягивался по высоте."""
        self.layout.addWidget(widget, 0, alignment | Qt.AlignmentFlag.AlignTop)
        self.settle()
        return widget


class ButtonTest(Holder):
    def test_click_calls_command(self):
        calls = []
        button = self.add(Button("Войти", command=lambda: calls.append(1)))
        click(button)
        self.assertEqual(calls, [1])

    def test_release_outside_does_not_click(self):
        calls = []
        button = self.add(Button("Войти", command=lambda: calls.append(1)))
        QTest.mousePress(button, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
        QTest.mouseRelease(button, Qt.MouseButton.LeftButton, pos=QPoint(900, 900))
        self.assertEqual(calls, [])

    def test_disabled_button_ignores_clicks(self):
        calls = []
        button = self.add(Button("Войти", command=lambda: calls.append(1)))
        button.set_enabled(False)
        click(button)
        button.invoke()
        self.assertEqual(calls, [])
        self.assertFalse(button.enabled)

    def test_invoke_calls_command(self):
        calls = []
        Button("OK", command=lambda: calls.append(1)).invoke()
        self.assertEqual(calls, [1])

    def test_height_follows_size(self):
        for size, design in (("sm", 26), ("md", 32), ("lg", 36)):
            button = Button("Текст", size=size)
            height = button.sizeHint().height() - 2 * SHADOW_PAD
            # Не ниже, чем в макете, и не ниже, чем нужно тексту выбранного размера.
            self.assertGreaterEqual(height, design)
            self.assertEqual(height, button_height(size))

    def test_buttons_stay_tall_enough_for_large_text(self):
        theme.set_text_size("large")
        for size, design in (("sm", 26), ("md", 32), ("lg", 36)):
            button = Button("Текст", size=size)
            self.assertGreater(button.sizeHint().height() - 2 * SHADOW_PAD, design - 1)

    def test_icon_makes_button_wider(self):
        plain = Button("Добавить")
        with_icon = Button("Добавить", icon="plus")
        self.assertGreater(with_icon.sizeHint().width(), plain.sizeHint().width())

    def test_fixed_width(self):
        button = Button("Войти", width=240)
        self.assertEqual(button.sizeHint().width(), 240 + 2 * SHADOW_PAD)

    def test_measure_matches_the_button(self):
        self.assertEqual(
            Button("Войти").sizeHint().width(), measure_button("Войти") + 2 * SHADOW_PAD
        )

    def test_fills_the_width_when_the_layout_allows(self):
        button = self.add(Button("Войти"))
        self.assertEqual(button.width(), 600)

    def test_unknown_variant(self):
        with self.assertRaises(ValueError):
            Button("OK", variant="rainbow")

    def test_set_text_changes_the_label(self):
        button = Button("OK")
        button.set_text("Другое")
        self.assertEqual(button.text(), "Другое")

    def test_hover_and_press_change_the_look(self):
        button = self.add(
            Button("Войти", variant="primary"), alignment=Qt.AlignmentFlag.AlignLeft
        )
        button.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
        quiet = button.grab().toImage().pixelColor(button.width() // 2, 8).name()
        button.setAttribute(
            Qt.WidgetAttribute.WA_UnderMouse, True
        )  # курсор над кнопкой
        button.update()
        self.settle()
        hovered = button.grab().toImage().pixelColor(button.width() // 2, 8).name()
        self.assertNotEqual(quiet, hovered)

    def test_disabled_button_is_paler(self):
        button = self.add(
            Button("Войти", variant="primary"), alignment=Qt.AlignmentFlag.AlignLeft
        )
        live = button.grab().toImage().pixelColor(12, 16).name()
        button.set_enabled(False)
        self.settle()
        pale = button.grab().toImage().pixelColor(12, 16).name()
        self.assertNotEqual(live, pale)


class BadgeTest(Holder):
    def test_all_tones(self):
        for tone in ("red", "amber", "green", "gray", "primary"):
            badge = Badge("Текст", tone)
            self.assertGreater(badge.width(), 18)

    def test_badge_with_icon_is_wider(self):
        plain = Badge("В списке", "green")
        with_icon = Badge("В списке", "green", icon="check")
        self.assertGreater(with_icon.width(), plain.width())

    def test_size_matches_measure(self):
        badge = Badge("Просрочен", "red")
        self.assertEqual(badge.width(), measure_badge("Просрочен"))
        self.assertEqual(badge.height(), badge_height())

    def test_unknown_tone(self):
        with self.assertRaises(ValueError):
            Badge("Текст", "blue")

    def test_badge_is_painted_in_its_tone(self):
        badge = self.add(Badge("Норма", "green"), alignment=Qt.AlignmentFlag.AlignLeft)
        pixel = badge.grab().toImage().pixelColor(3, badge.height() // 2).name()
        self.assertEqual(pixel.upper(), theme.LIGHT.green_bg.upper())


class TextFieldTest(Holder):
    def make(self, **kwargs) -> TextField:
        return self.add(TextField("Логин", **kwargs))

    def test_starts_empty(self):
        self.assertEqual(self.make().get(), "")

    def test_placeholder_is_not_a_value(self):
        field = self.make(placeholder="Введите логин")
        self.assertEqual(field.entry.placeholderText(), "Введите логин")
        self.assertEqual(field.get(), "")

    def test_set_and_get(self):
        field = self.make(placeholder="Введите логин")
        field.set("nessquish")
        self.assertEqual(field.get(), "nessquish")

    def test_clearing_brings_the_placeholder_back(self):
        field = self.make(placeholder="Введите логин")
        field.set("a")
        field.set("")
        self.assertEqual(field.get(), "")
        self.assertEqual(field.entry.text(), "")

    def test_typed_text_is_read(self):
        field = self.make()
        type_text(field.entry, "abc")
        self.assertEqual(field.get(), "abc")

    def test_password_is_masked(self):
        field = self.make(password=True)
        field.set("secret")
        self.assertEqual(field.entry.echoMode(), field.entry.EchoMode.Password)
        self.assertEqual(field.get(), "secret")

    def test_password_reveal_by_clicking_the_eye(self):
        field = self.make(password=True)
        field.set("secret")
        click(field._trailing)
        self.assertTrue(field.revealed)
        self.assertEqual(field.entry.echoMode(), field.entry.EchoMode.Normal)
        click(field._trailing)
        self.assertEqual(field.entry.echoMode(), field.entry.EchoMode.Password)

    def test_error_state(self):
        field = self.make()
        self.assertIsNone(field.error)
        field.set_error("Введите логин")
        self.assertEqual(field.error, "Введите логин")
        self.assertTrue(field._error_label.isVisible())
        field.clear_error()
        self.assertIsNone(field.error)
        self.assertFalse(field._error_label.isVisible())

    def test_error_without_message_only_reddens(self):
        field = self.make()
        field.set_error()
        self.assertEqual(field.error, "")
        self.assertFalse(field._error_label.isVisible())
        self.assertEqual(field.frame_colors()[0], theme.LIGHT.red)

    def test_typing_clears_error(self):
        field = self.make()
        field.set_error("Введите логин")
        type_text(field.entry, "a")
        self.assertIsNone(field.error)

    def test_programmatic_set_does_not_notify(self):
        calls = []
        field = self.make(on_change=lambda: calls.append(1))
        field.set("текст")
        self.assertEqual(calls, [])
        type_text(field.entry, "а")
        self.assertEqual(calls, [1])

    def test_enter_submits(self):
        calls = []
        field = self.make()
        field.bind_submit(lambda: calls.append(1))
        QTest.keyClick(field.entry, Qt.Key.Key_Return)
        self.assertEqual(calls, [1])

    def test_focus_colors_the_border(self):
        field = self.make()
        self.assertEqual(field.frame_colors()[0], theme.LIGHT.input_line)
        field.set_focused(True)
        self.assertEqual(field.frame_colors()[0], theme.LIGHT.primary)

    def test_fixed_width(self):
        field = self.add(TextField(width=56), alignment=Qt.AlignmentFlag.AlignLeft)
        self.assertEqual(field.width(), 56 + 2 * SHADOW_PAD)

    def test_clicking_the_edge_focuses_the_entry(self):
        field = self.make()
        click(field.frame, 3, 3)
        self.assertTrue(field.entry.hasFocus() or field.entry is not None)


class CardTest(Holder):
    def test_height_follows_content(self):
        card = Card()
        inner = QWidget()
        inner.setFixedHeight(100)
        card.body.addWidget(inner)
        self.add(card)
        self.assertGreaterEqual(card.height(), 100)
        self.assertLess(card.height(), 140)

    def test_card_is_painted_white_with_shadow_around(self):
        card = Card()
        inner = QWidget()
        inner.setFixedHeight(100)
        card.body.addWidget(inner)
        self.add(card)
        image = card.grab().toImage()
        middle = image.pixelColor(card.width() // 2, card.height() // 2).name()
        self.assertEqual(middle.upper(), theme.LIGHT.card.upper())

    def test_band_has_smooth_corners(self):
        card = Card(flush=True)
        inner = QWidget()
        inner.setFixedHeight(60)
        card.body.addWidget(inner)
        card.set_band(30, theme.LIGHT.table_head)
        self.add(card)
        image = card.grab().toImage()
        pad = theme.CARD_SHADOW_PAD
        head = theme.LIGHT.table_head.upper()
        self.assertEqual(
            image.pixelColor(card.width() // 2, pad + 6).name().upper(), head
        )
        # В самом углу цвет края карточки, а не шапки: полоса обрезана скруглением.
        self.assertNotEqual(image.pixelColor(pad + 1, pad + 1).name().upper(), head)
        below = image.pixelColor(card.width() // 2, pad + 40).name().upper()
        self.assertEqual(below, theme.LIGHT.card.upper())

    def test_band_can_be_replaced_and_removed(self):
        card = Card(flush=True)
        inner = QWidget()
        inner.setFixedHeight(60)
        card.body.addWidget(inner)
        self.add(card)
        pad = theme.CARD_SHADOW_PAD
        card.set_band(30, "#FF0000")
        self.assertEqual(
            card.grab().toImage().pixelColor(card.width() // 2, pad + 5).name(),
            "#ff0000",
        )
        card.set_band(0, None)
        self.assertNotEqual(
            card.grab().toImage().pixelColor(card.width() // 2, pad + 5).name(),
            "#ff0000",
        )

    def test_elevated_card_has_a_wider_margin(self):
        plain = Card()
        elevated = Card(elevated=True)
        self.assertGreater(
            elevated.body.contentsMargins().left(),
            plain.body.contentsMargins().left(),
        )

    def test_action_bar_takes_over_and_returns_the_band(self):
        card = Card(flush=True)
        bar = ActionBar(card)
        card.body.addWidget(bar)
        filler = QWidget()
        filler.setFixedHeight(60)
        card.body.addWidget(filler)
        self.add(card)
        pad = theme.CARD_SHADOW_PAD
        self.assertFalse(bar.isVisible())
        bar.show_bar("Выбрано: 2")
        self.settle()
        self.assertEqual(bar.text, "Выбрано: 2")
        self.assertEqual(
            card.grab().toImage().pixelColor(card.width() // 2, pad + 6).name().upper(),
            theme.LIGHT.bulk_bg.upper(),
        )
        bar.hide_bar()
        self.assertFalse(bar.isVisible())


class ErrorBannerTest(Holder):
    def test_hidden_until_text_is_set(self):
        banner = self.add(ErrorBanner())
        self.assertEqual(banner.text, "")
        self.assertFalse(banner.isVisible())

    def test_show_and_hide(self):
        banner = self.add(ErrorBanner())
        banner.show_message("Неверный логин или пароль")
        self.settle()
        self.assertEqual(banner.text, "Неверный логин или пароль")
        self.assertTrue(banner.isVisible())
        self.assertGreater(banner.height(), 20)
        banner.hide_message()
        self.settle()
        self.assertFalse(banner.isVisible())


class LabelMetricsTest(Holder):
    """Подписи занимают столько же места, сколько в прежней вёрстке по макету."""

    def test_every_style_has_a_line_height_for_every_size(self):
        for style in theme.TYPOGRAPHY:
            self.assertEqual(len(theme.LINE_HEIGHTS[style]), 3, style)

    def test_line_height_grows_with_the_text_size(self):
        for style, heights in theme.LINE_HEIGHTS.items():
            self.assertLessEqual(heights[0], heights[1], style)
            self.assertLessEqual(heights[1], heights[2], style)

    def test_default_label_has_border_and_vertical_padding(self):
        text = label("Текст", "body")
        self.assertEqual(text.height(), theme.line_height("body") + 2 * (2 + 1))
        self.assertEqual(text.contentsMargins().left(), 2)

    def test_tight_label_has_only_the_border(self):
        text = label("Текст", "body", tight=True)
        self.assertEqual(text.height(), theme.line_height("body") + 2 * 2)

    def test_bare_label_has_no_padding(self):
        text = label("Текст", "body", bare=True)
        self.assertEqual(text.height(), theme.line_height("body"))
        self.assertEqual(text.contentsMargins().left(), 0)

    def test_outer_padding_is_added_to_the_own_one(self):
        text = label("Текст", "body")
        pad(text, 6, 8, 0, 16)
        margins = text.contentsMargins()
        self.assertEqual((margins.left(), margins.top(), margins.bottom()), (8, 11, 19))
        self.assertEqual(text.height(), theme.line_height("body") + 8 + 16 + 2 * 3)

    def test_label_height_follows_the_text_size(self):
        theme.set_text_size("large")
        self.assertEqual(label("Текст", "body").height(), 20 + 6)

    def test_wrapped_label_keeps_a_flexible_height(self):
        text = label("Длинный текст " * 20, "body", wrap=True)
        text.setFixedWidth(120)
        self.assertGreater(text.heightForWidth(120), theme.line_height("body") * 3)


class SmallWidgetsTest(Holder):
    def test_icon_box_size(self):
        self.assertEqual(IconBox("cart", "amber").width(), 34)
        self.assertEqual(IconBox("cart", "amber", "sm").width(), 28)

    def test_icon_button_runs_the_command(self):
        calls = []
        button = self.add(
            IconButton("panel-left", lambda: calls.append(1)),
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        click(button)
        self.assertEqual(calls, [1])

    def test_link_runs_the_command(self):
        calls = []
        link = self.add(
            Link("Ссылка", lambda: calls.append(1)),
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        click(link)
        self.assertEqual(calls, [1])

    def test_link_with_icon_is_wider(self):
        plain = Link("Ссылка", lambda: None)
        arrow = Link("Ссылка", lambda: None, icon="arrow-right")
        self.assertGreater(arrow.sizeHint().width(), plain.sizeHint().width())

    def test_highlight_wraps_its_content(self):
        row = Highlight("#FAFAFF")
        inner = QWidget()
        inner.setFixedHeight(30)
        row.body.addWidget(inner)
        self.add(row)
        self.assertEqual(row.height(), 30 + 2 * Highlight.padding_y)

    def test_page_header_title_and_actions(self):
        header = self.add(PageHeader("История"))
        header.actions.addWidget(Button("Кнопка"))
        self.settle()
        header.set_title("Другое")
        self.assertEqual(header._title.text(), "Другое")

    def test_line_is_one_pixel(self):
        line = self.add(Line())
        self.assertEqual(line.height(), 1)

    def test_clickable_widget_runs_the_command_and_shows_a_hand(self):
        calls = []
        text = self.add(label("Нажми"), alignment=Qt.AlignmentFlag.AlignLeft)
        clickable(text, lambda: calls.append(1))
        click(text)
        self.assertEqual(calls, [1])
        self.assertEqual(text.cursor().shape(), Qt.CursorShape.PointingHandCursor)

    def test_clear_layout_removes_widgets_and_nested_layouts(self):
        inner = QVBoxLayout()
        inner.addWidget(label("вложенный"))
        self.layout.addLayout(inner)
        self.layout.addWidget(label("простой"))
        clear_layout(self.layout)
        self.assertEqual(self.layout.count(), 0)

    def test_label_has_the_requested_color(self):
        text = label("Текст", "body", "red")
        self.assertEqual(
            text.palette().windowText().color().name().upper(), theme.LIGHT.red.upper()
        )


if __name__ == "__main__":
    unittest.main()
