"""Тесты выпадающего списка, переключателей, таблицы и расширенных полей."""

from typing import List

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QVBoxLayout, QWidget

from pharmacy.ui import theme
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.common import label
from pharmacy.ui.widgets.controls import Checkbox, Pagination, Segmented, Toggle
from pharmacy.ui.widgets.field import ICON_INSET, ICON_SIZE, TextField
from pharmacy.ui.widgets.popup import MAX_VISIBLE, SHADOW_PAD, PopupList
from pharmacy.ui.widgets.select import Select
from pharmacy.ui.widgets.table import Column, DataTable, TextCell
from pharmacy.ui.fonts import text_width
from tests.qt_helpers import WidgetTestCase, click, type_text


class Holder(WidgetTestCase):
    """Окно с вертикальной раскладкой: виджеты прижаты к верху."""

    def setUp(self) -> None:
        super().setUp()
        self.layout = QVBoxLayout(self.root)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def add(self, widget: QWidget, alignment=Qt.AlignmentFlag(0)) -> QWidget:
        self.layout.addWidget(widget, 0, alignment | Qt.AlignmentFlag.AlignTop)
        self.settle()
        return widget


def open_list(select: Select) -> PopupList:
    click(select.frame, 40, 16)
    select.window()  # окно уже знает о новом виджете
    return select.popup


class SelectTest(Holder):
    OPTIONS = [(1, "Лекарства"), (2, "Бытовая химия"), (3, "Гигиена")]

    def make(self, **kwargs) -> Select:
        return self.add(Select(self.OPTIONS, label_text="Категория", **kwargs))

    def test_value_is_not_the_label(self):
        select = self.make(value=2)
        self.assertEqual(select.get(), 2)

    def test_empty_by_default(self):
        self.assertIsNone(self.make().get())

    def test_set_changes_value(self):
        select = self.make()
        select.set(3)
        self.assertEqual(select.value, 3)

    def test_plain_strings_work_as_options(self):
        select = Select(["упак.", "шт."], value="шт.")
        self.assertEqual(select.get(), "шт.")

    def test_shown_text_is_the_label_or_the_placeholder(self):
        select = self.make(value=2, placeholder="Выберите")
        self.assertEqual(select.shown_text(), "Бытовая химия")
        select.set(None)
        self.assertEqual(select.shown_text(), "Выберите")

    def test_click_opens_the_list_and_pick_changes_value(self):
        picked: List[object] = []
        select = self.make(on_change=picked.append)
        popup = open_list(select)
        self.assertIsInstance(popup, PopupList)
        self.assertTrue(popup.isVisible())
        popup._on_pick(2)
        popup.close_list()
        self.settle()
        self.assertEqual(select.get(), 2)
        self.assertEqual(picked, [2])
        self.assertIsNone(select.popup)

    def test_click_on_a_row_of_the_list_picks_it(self):
        picked: List[object] = []
        select = self.make(on_change=picked.append)
        popup = open_list(select)
        row = 1  # вторая строка списка
        y = 2 + 4 + row * 30 + 15
        click(popup, SHADOW_PAD + 20, y)
        self.settle()
        self.assertEqual(picked, [2])
        self.assertIsNone(select.popup)

    def test_one_click_on_another_select_switches_without_choosing(self):
        first = self.make(value=1)
        second = self.make(value=2)
        open_list(first)
        self.assertIsNotNone(first.popup)
        click(second.frame, 40, 16)
        self.settle()
        self.assertIsNone(first.popup)
        self.assertIsNotNone(second.popup)
        self.assertEqual(first.get(), 1)  # значение первого не изменилось
        second.popup.close_list()

    def test_click_elsewhere_closes_the_list_and_keeps_the_value(self):
        select = self.make(value=1)
        other = self.add(Button("другая кнопка"), Qt.AlignmentFlag.AlignLeft)
        open_list(select)
        self.assertIsNotNone(select.popup)
        click(other)
        self.settle()
        self.assertIsNone(select.popup)
        self.assertEqual(select.get(), 1)

    def test_clicking_the_same_select_twice_closes_the_list(self):
        select = self.make()
        open_list(select)
        click(select.frame, 40, 16)
        self.settle()
        self.assertIsNone(select.popup)

    def test_popup_closes_on_escape(self):
        select = self.make()
        popup = open_list(select)
        QTest.keyClick(popup, Qt.Key.Key_Escape)
        self.settle()
        self.assertIsNone(select.popup)

    def test_popup_is_a_widget_inside_the_window_not_a_separate_window(self):
        select = self.make()
        popup = open_list(select)
        self.assertFalse(popup.isWindow())
        self.assertIs(popup.parentWidget(), self.root)
        popup.close_list()

    def test_popup_closes_when_the_window_is_resized(self):
        select = self.make()
        open_list(select)
        self.root.resize(520, 420)
        self.settle()
        self.assertIsNone(select.popup)

    def test_clicking_inside_the_popup_does_not_close_it_as_outside(self):
        select = self.make()
        popup = open_list(select)
        # Нажатие внутри списка не считается нажатием «вне» (список закроется
        # сам, когда мышь отпустят на варианте).
        QTest.mousePress(
            popup, Qt.MouseButton.LeftButton, pos=QPoint(SHADOW_PAD + 20, 25)
        )
        self.settle()
        self.assertIsNotNone(select.popup)
        QTest.mouseRelease(
            popup, Qt.MouseButton.LeftButton, pos=QPoint(SHADOW_PAD + 20, 25)
        )
        self.settle()
        self.assertIsNone(select.popup)

    def test_popup_starts_below_the_field(self):
        select = self.make()
        popup = open_list(select)
        field_bottom = select.frame.mapTo(
            self.root, select.frame.rect().bottomLeft()
        ).y()
        self.assertGreaterEqual(popup.y(), field_bottom - 8)
        popup.close_list()

    def test_popup_opens_above_the_field_when_there_is_no_room_below(self):
        self.layout.addStretch(1)
        select = self.add(Select(self.OPTIONS, label_text="Категория"))
        popup = open_list(select)
        box_top = select.frame.mapTo(
            self.root, select.frame.box_rect().topLeft().toPoint()
        ).y()
        self.assertLess(popup.y(), box_top)
        # Низ списка (без поля под тень) упирается в верх поля, а не заходит на него.
        self.assertEqual(popup.y() + popup.height() - SHADOW_PAD, box_top)
        popup.close_list()

    def test_error_is_cleared_after_pick(self):
        select = self.make()
        select.set_error("Выберите категорию")
        select._pick(1)
        self.assertIsNone(select.error)

    def test_compact_width_follows_longest_option(self):
        select = Select(self.OPTIONS, 1, compact=True, prefix="Сортировка: ")
        self.assertGreater(select.minimumWidth(), 120)

    def test_set_options(self):
        select = self.make(value=1)
        select.set_options([(9, "Новая")])
        self.assertEqual(select._label_of(9), "Новая")

    def test_hand_cursor_over_the_field(self):
        select = self.make()
        self.assertEqual(
            select.frame.cursor().shape(), Qt.CursorShape.PointingHandCursor
        )


class PopupListTest(Holder):
    def test_scrolls_long_lists(self):
        anchor = self.add(QWidget())
        anchor.setFixedSize(200, 30)
        self.settle()
        options = [(i, f"Вариант {i}") for i in range(20)]
        popup = PopupList(anchor, options, 0, lambda value: None)
        self.settle()
        QTest.mouseMove(popup, popup.rect().center())
        popup.wheelEvent(_Wheel(-120))
        self.assertEqual(popup._offset, 1)
        popup._offset = 100
        popup.wheelEvent(_Wheel(-120))
        self.assertEqual(popup._offset, 20 - MAX_VISIBLE)
        popup.wheelEvent(_Wheel(120))
        self.assertEqual(popup._offset, 20 - MAX_VISIBLE - 1)
        popup.close_list()
        popup.close_list()

    def test_short_list_ignores_the_wheel(self):
        anchor = self.add(QWidget())
        anchor.setFixedSize(200, 30)
        popup = PopupList(anchor, [(1, "Один"), (2, "Два")], 1, lambda value: None)
        popup.wheelEvent(_Wheel(-120))
        self.assertEqual(popup._offset, 0)
        popup.close_list()

    def test_closing_calls_the_callback_once(self):
        anchor = self.add(QWidget())
        anchor.setFixedSize(200, 30)
        calls: List[int] = []
        popup = PopupList(
            anchor, [(1, "Один")], 1, lambda v: None, lambda: calls.append(1)
        )
        popup.close_list()
        popup.close_list()
        self.assertEqual(calls, [1])


class _Wheel:
    """Колесо мыши для вызова обработчика напрямую."""

    def __init__(self, delta: int) -> None:
        self._delta = delta

    def angleDelta(self):
        class Point:
            def __init__(self, y):
                self._y = y

            def y(self):
                return self._y

        return Point(self._delta)


class TextFieldExtrasTest(Holder):
    def make(self, **kwargs) -> TextField:
        return self.add(TextField(**kwargs))

    def clipboard(self) -> str:
        return QGuiApplication.clipboard().text()

    def set_clipboard(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)

    def shortcut(self, field: TextField, key: Qt.Key) -> None:
        field.entry.setFocus()
        QTest.keyClick(field.entry, key, Qt.KeyboardModifier.ControlModifier)
        self.settle()

    def test_without_label(self):
        field = self.make(placeholder="Поиск", leading_icon="search")
        field.set("бинт")
        self.assertEqual(field.get(), "бинт")

    def test_multiline_text(self):
        field = self.make(
            label_text="Примечание", multiline=True, placeholder="Введите"
        )
        self.assertEqual(field.get(), "")
        field.set("первая\nвторая")
        self.assertEqual(field.get(), "первая\nвторая")
        field.set("")
        self.assertEqual(field.get(), "")

    def test_multiline_is_taller(self):
        single = self.make(label_text="Один")
        multi = self.make(label_text="Много", multiline=True)
        self.assertGreater(multi.frame.height(), single.frame.height())

    def test_readonly_keeps_value_but_can_be_set_from_code(self):
        field = self.make(label_text="Логин", readonly=True)
        field.set("nessquish")
        self.assertEqual(field.get(), "nessquish")
        type_text(field.entry, "x")
        self.assertEqual(field.get(), "nessquish")

    def test_on_change_fires_for_typing_but_not_for_setting(self):
        calls: List[int] = []
        field = self.make(placeholder="Поиск", on_change=lambda: calls.append(1))
        field.set("текст")
        self.assertEqual(calls, [])
        type_text(field.entry, "а")
        self.assertEqual(calls, [1])

    def test_cyrillic_typing_works(self):
        field = self.make()
        type_text(field.entry, "Привет")
        self.assertEqual(field.get(), "Привет")

    def test_paste_works(self):
        calls: List[int] = []
        field = self.make(on_change=lambda: calls.append(1))
        self.set_clipboard("из буфера")
        self.shortcut(field, Qt.Key.Key_V)
        self.assertEqual(field.get(), "из буфера")
        self.assertEqual(calls, [1])

    def test_copy_and_cut(self):
        field = self.make()
        field.set("текст")
        field.entry.selectAll()
        self.shortcut(field, Qt.Key.Key_C)
        self.assertEqual(self.clipboard(), "текст")
        field.entry.selectAll()
        self.shortcut(field, Qt.Key.Key_X)
        self.assertEqual(field.get(), "")

    def password(self, value: str = "Секрет123") -> TextField:
        field = self.make(password=True, label_text="Пароль")
        field.set(value)
        field.entry.setFocus()
        return field

    def test_copy_from_a_hidden_field_gives_the_real_text(self):
        field = self.password()
        field.entry.selectAll()
        self.shortcut(field, Qt.Key.Key_C)
        self.assertEqual(self.clipboard(), "Секрет123")
        self.assertEqual(field.get(), "Секрет123")

    def test_copy_part_of_a_hidden_field(self):
        field = self.password()
        field.entry.setSelection(2, 3)
        self.shortcut(field, Qt.Key.Key_C)
        self.assertEqual(self.clipboard(), "кре")

    def test_cut_from_a_hidden_field(self):
        field = self.password()
        field.entry.selectAll()
        self.shortcut(field, Qt.Key.Key_X)
        self.assertEqual(self.clipboard(), "Секрет123")
        self.assertEqual(field.get(), "")

    def test_cut_part_of_a_hidden_field(self):
        field = self.password()
        field.entry.setSelection(0, 3)
        self.shortcut(field, Qt.Key.Key_X)
        self.assertEqual(self.clipboard(), "Сек")
        self.assertEqual(field.get(), "рет123")

    def test_revealed_password_copies_normally(self):
        field = self.password("abc123")
        field._toggle_reveal()
        field.entry.selectAll()
        self.shortcut(field, Qt.Key.Key_C)
        self.assertEqual(self.clipboard(), "abc123")

    def test_copy_with_nothing_selected_keeps_the_clipboard(self):
        field = self.password()
        self.set_clipboard("старое")
        field.entry.deselect()
        self.shortcut(field, Qt.Key.Key_C)
        self.assertEqual(self.clipboard(), "старое")

    def test_paste_into_a_hidden_field_still_works(self):
        field = self.make(password=True, label_text="Пароль")
        self.set_clipboard("Вставлено1")
        self.shortcut(field, Qt.Key.Key_V)
        self.assertEqual(field.get(), "Вставлено1")

    def test_readonly_hidden_field_copies_but_does_not_cut(self):
        field = self.make(password=True, readonly=True, label_text="Пароль")
        field.set("demo12345")
        field.entry.setFocus()
        field.entry.selectAll()
        self.shortcut(field, Qt.Key.Key_C)
        self.assertEqual(self.clipboard(), "demo12345")
        self.set_clipboard("")
        field.entry.selectAll()
        self.shortcut(field, Qt.Key.Key_X)
        self.assertEqual(field.get(), "demo12345")

    def test_readonly_field_cannot_be_pasted_into(self):
        field = self.make(label_text="Логин", readonly=True)
        field.set("nessquish")
        self.set_clipboard("чужое")
        self.shortcut(field, Qt.Key.Key_V)
        self.assertEqual(field.get(), "nessquish")

    def test_trailing_icon_does_not_change_the_text_area_rules(self):
        field = self.make(trailing_icon="calendar", label_text="Срок")
        self.assertIsNotNone(field._trailing)
        self.assertEqual(field._trailing.width(), ICON_SIZE)
        self.assertGreater(ICON_INSET, 0)


class SegmentedTest(Holder):
    def make(self, variant="tabs") -> Segmented:
        changes: List[int] = []
        seg = self.add(
            Segmented(
                ["Все · 4", "Не куплено · 3", "Куплено · 1"],
                0,
                changes.append,
                variant,
            ),
            Qt.AlignmentFlag.AlignLeft,
        )
        seg.changes = changes
        return seg

    def test_click_selects_item(self):
        for variant in ("tabs", "outline"):
            seg = self.make(variant)
            left, right = seg.spans[1]
            click(seg, (left + right) // 2, 15)
            self.assertEqual(seg.active, 1)
            self.assertEqual(seg.changes, [1])

    def test_clicking_active_item_does_nothing(self):
        seg = self.make()
        left, right = seg.spans[0]
        click(seg, (left + right) // 2, 15)
        self.assertEqual(seg.changes, [])

    def test_select_is_silent(self):
        seg = self.make()
        seg.select(2)
        self.assertEqual(seg.active, 2)
        self.assertEqual(seg.changes, [])

    def test_set_items_updates_labels(self):
        seg = self.make()
        before = seg.width()
        seg.set_items(["Все · 1000", "Не куплено · 3", "Куплено · 1"])
        self.assertGreater(seg.width(), before)

    def test_unknown_variant(self):
        with self.assertRaises(ValueError):
            Segmented(["a"], variant="x")


class SwitchTest(Holder):
    def test_toggle(self):
        values: List[bool] = []
        toggle = self.add(Toggle(True, values.append), Qt.AlignmentFlag.AlignLeft)
        click(toggle)
        click(toggle)
        self.assertEqual(values, [False, True])
        self.assertTrue(toggle.value)

    def test_toggle_set_is_silent(self):
        values: List[bool] = []
        toggle = Toggle(False, values.append)
        toggle.set(True)
        self.assertTrue(toggle.value)
        self.assertEqual(values, [])

    def test_checkbox(self):
        values: List[bool] = []
        box = self.add(Checkbox(False, values.append), Qt.AlignmentFlag.AlignLeft)
        click(box)
        self.assertTrue(box.value)
        box.set(False)
        self.assertFalse(box.value)
        self.assertEqual(values, [True])

    def test_toggle_and_checkbox_are_painted_in_the_accent_when_on(self):
        box = self.add(Checkbox(True), Qt.AlignmentFlag.AlignLeft)
        color = box.grab().toImage().pixelColor(1, 7).name().upper()
        self.assertEqual(color, theme.LIGHT.primary.upper())


class PaginationTest(Holder):
    def make(self, page=1, pages=3):
        picked: List[int] = []
        pager = self.add(
            Pagination(page, pages, picked.append), Qt.AlignmentFlag.AlignLeft
        )
        pager.picked = picked
        return pager

    def cell_x(self, pager: Pagination, index: int) -> int:
        return pager.cell_left(index) + 5

    def test_page_buttons(self):
        pager = self.make()
        click(pager, self.cell_x(pager, 2), 5)  # цифра 2
        self.assertEqual(pager.picked, [2])
        self.assertEqual(pager.page, 2)

    def test_arrows(self):
        pager = self.make(page=2)
        click(pager, self.cell_x(pager, 4), 5)  # стрелка вперёд
        click(pager, self.cell_x(pager, 0), 5)  # стрелка назад
        self.assertEqual(pager.picked, [3, 2])

    def test_disabled_arrow_and_current_page_do_nothing(self):
        pager = self.make(page=1)
        click(pager, self.cell_x(pager, 0), 5)
        click(pager, self.cell_x(pager, 1), 5)
        self.assertEqual(pager.picked, [])

    def test_single_page(self):
        pager = self.make(page=1, pages=1)
        click(pager, self.cell_x(pager, 2), 5)
        self.assertEqual(pager.picked, [])


class DataTableTest(Holder):
    def make(self) -> DataTable:
        table = DataTable(
            [
                Column("Название", 3),
                Column("Срок", 2),
                Column("", fixed=40),
            ],
        )
        return self.add(table)

    def test_rows_are_added_and_cleared(self):
        table = self.make()
        table.add_row(["Бинт", "01.01.2027", "x"])
        table.add_row(["Вата", "02.01.2027", "y"])
        self.settle()
        self.assertEqual(table.row_count, 2)
        self.assertEqual(table.row_texts[0], ["Бинт", "01.01.2027", "x"])
        table.clear()
        self.settle()
        self.assertEqual(table.row_count, 0)
        self.assertEqual(table.row_texts, [])

    def test_link_cell_calls_command(self):
        calls: List[int] = []
        table = self.make()
        table.add_row(
            [
                TextCell("Бинт", "primary", True, on_click=lambda: calls.append(1)),
                "-",
                "-",
            ]
        )
        self.settle()
        click(table.cell_widgets(0)[0])
        self.assertEqual(calls, [1])

    def test_widget_cells(self):
        table = self.make()
        table.add_row(["Бинт", lambda: label("виджет"), ""])
        self.settle()
        self.assertEqual(table.cell_widgets(1)[0].text(), "виджет")

    def test_strike_cell(self):
        table = self.make()
        table.add_row([TextCell("Витамин C", "ink_3", strike=True), "", ""])
        self.assertTrue(table.cell_widgets(0)[0].font().strikeOut())

    def test_selected_row_has_highlight(self):
        table = self.make()
        table.add_row(["a", "b", "c"])
        plain = len(table._rows)
        table.add_row(["a", "b", "c"], selected=True)
        # У выбранной строки добавляется ещё и подложка.
        self.assertEqual(len(table._rows) - plain, plain + 1)

    def test_message_row(self):
        table = self.make()
        table.add_message("Ничего не найдено")
        self.settle()
        self.assertEqual(table.row_count, 0)
        self.assertIn(
            "Ничего не найдено", [w.text() for w in table.findChildren(type(label("")))]
        )

    def test_sort_arrow_is_shown_for_one_column(self):
        table = self.make()
        table.set_sorted(1)
        self.assertEqual(table.sorted_column, 1)
        table.set_sorted(None)
        self.assertIsNone(table.sorted_column)

    def test_columns_follow_weights(self):
        table = self.make()
        table.add_row(["Бинт", "01.01.2027", ""])
        self.settle()
        first = table._cells[0][0].width()
        second = table._cells[0][1].width()
        fixed = table._cells[0][2].width()
        self.assertEqual(fixed, 40)
        self.assertAlmostEqual(first / second, 3 / 2, delta=0.05)

    def test_header_widget_replaces_the_title(self):
        table = self.make()
        box = table.set_header_widget(2, lambda: Checkbox(False))
        self.settle()
        self.assertTrue(box.isVisible())

    def test_without_a_card_the_header_paints_itself(self):
        table = self.make()
        self.assertTrue(table._grid_host.paint_header)


class CompactSelectWidthTest(Holder):
    def test_text_never_runs_under_the_arrow(self):
        options = [("a", "срок годности"), ("b", "дата добавления"), ("c", "имя")]
        for value in ("a", "b", "c"):
            select = self.add(
                Select(options, value, compact=True, prefix="Сортировка: "),
                Qt.AlignmentFlag.AlignLeft,
            )
            needed = (
                select._inset
                + text_width(select.shown_text(), "body")
                + ICON_SIZE
                + ICON_INSET
            )
            self.assertGreaterEqual(select.width() - 8, needed)
            select.setParent(None)
            select.deleteLater()

    def test_width_follows_the_chosen_value(self):
        select = self.add(
            Select([("a", "имя"), ("b", "очень длинное название")], "a", compact=True),
            Qt.AlignmentFlag.AlignLeft,
        )
        short = select.width()
        select.set("b")
        self.settle()
        self.assertGreater(select.width(), short)


class SelectBorderTest(Holder):
    OPTIONS = [(1, "Все категории"), (2, "Лекарства")]

    def make(self) -> Select:
        return self.add(
            Select(self.OPTIONS, 1, compact=True), Qt.AlignmentFlag.AlignLeft
        )

    def test_blue_border_only_while_the_list_is_open(self):
        select = self.make()
        self.assertEqual(select.frame_colors()[0], theme.LIGHT.line)
        select.frame_pressed(None)
        self.settle()
        self.assertEqual(select.frame_colors()[0], theme.LIGHT.primary)
        select.popup.close_list()
        self.settle()
        self.assertEqual(select.frame_colors()[0], theme.LIGHT.line)

    def test_border_is_normal_after_picking(self):
        select = self.make()
        select.frame_pressed(None)
        popup = select.popup
        popup._on_pick(2)
        popup.close_list()
        self.settle()
        self.assertEqual(select.frame_colors()[0], theme.LIGHT.line)

    def test_error_color_wins_over_open_state(self):
        select = self.make()
        select.set_error("Выберите")
        select.frame_pressed(None)
        self.settle()
        self.assertEqual(select.frame_colors()[0], theme.LIGHT.red)
        select.popup.close_list()
