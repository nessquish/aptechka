"""Тесты выпадающего списка, переключателей, таблицы и расширенных полей."""

import tkinter as tk
from typing import List

from pharmacy.ui.widgets.controls import Checkbox, Pagination, Segmented, Toggle
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.popup import PopupList
from pharmacy.ui.widgets.select import Select
from pharmacy.ui.widgets.table import Column, DataTable, TextCell
from tests.test_ui_widgets import WidgetTestCase


def click(widget: tk.Misc, x: int, y: int) -> None:
    widget.event_generate("<ButtonPress-1>", x=x, y=y)
    widget.event_generate("<ButtonRelease-1>", x=x, y=y)


class SelectTest(WidgetTestCase):
    OPTIONS = [(1, "Лекарства"), (2, "Бытовая химия"), (3, "Гигиена")]

    def make(self, **kwargs) -> Select:
        select = Select(self.root, self.OPTIONS, label="Категория", **kwargs)
        select.pack(fill="x")
        self.settle()
        return select

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
        select = Select(self.root, ["упак.", "шт."], value="шт.")
        self.assertEqual(select.get(), "шт.")

    def test_click_opens_the_list_and_pick_changes_value(self):
        picked: List[object] = []
        select = self.make(on_change=picked.append)
        click(select._canvas, 40, 16)
        self.settle()
        self.assertIsInstance(select._popup, PopupList)
        popup = select._popup
        popup.close()
        popup._on_pick(2)
        self.settle()
        self.assertEqual(select.get(), 2)
        self.assertEqual(picked, [2])
        self.assertIsNone(select._popup)

    def test_popup_closes_on_escape(self):
        select = self.make()
        click(select._canvas, 40, 16)
        self.settle()
        select._popup.event_generate("<Escape>")
        self.settle()
        self.assertIsNone(select._popup)

    def test_error_is_cleared_after_pick(self):
        select = self.make()
        select.set_error("Выберите категорию")
        select._pick(1)
        self.assertIsNone(select.error)

    def test_compact_width_follows_longest_option(self):
        select = Select(self.root, self.OPTIONS, compact=True, prefix="Сортировка: ")
        self.assertGreater(int(select._canvas.cget("width")), 120)

    def test_set_options(self):
        select = self.make(value=1)
        select.set_options([(9, "Новая")])
        self.assertEqual(select._label_of(9), "Новая")


class PopupListTest(WidgetTestCase):
    def test_scrolls_long_lists(self):
        anchor = tk.Canvas(self.root, width=200, height=30)
        anchor.pack()
        self.settle()
        options = [(i, f"Вариант {i}") for i in range(20)]
        popup = PopupList(anchor, options, 0, lambda value: None)
        self.settle()
        popup._canvas.event_generate("<MouseWheel>", delta=-120, x=20, y=40)
        self.assertEqual(popup._offset, 1)
        popup._offset = 100
        popup._on_wheel(type("E", (), {"delta": -120})())
        self.assertEqual(popup._offset, 12)
        popup.close()
        popup.close()


class TextFieldExtrasTest(WidgetTestCase):
    def make(self, **kwargs) -> TextField:
        field = TextField(self.root, **kwargs)
        field.pack(fill="x")
        self.settle()
        return field

    def test_without_label(self):
        field = self.make(placeholder="Поиск", leading_icon="search")
        field.set("бинт")
        self.assertEqual(field.get(), "бинт")

    def test_multiline_text(self):
        field = self.make(label="Примечание", multiline=True, placeholder="Введите")
        self.assertEqual(field.get(), "")
        field.set("первая\nвторая")
        self.assertEqual(field.get(), "первая\nвторая")
        field.set("")
        self.assertEqual(field.get(), "")

    def test_multiline_placeholder_cycle(self):
        field = self.make(label="Примечание", multiline=True, placeholder="Введите")
        field.entry.event_generate("<FocusIn>")
        self.assertEqual(field.entry.get("1.0", "end-1c"), "")
        field.entry.event_generate("<FocusOut>")
        self.assertEqual(field.entry.get("1.0", "end-1c"), "Введите")

    def test_readonly_keeps_value_but_can_be_set_from_code(self):
        field = self.make(label="Логин", readonly=True)
        field.set("nessquish")
        self.assertEqual(field.get(), "nessquish")
        field.entry.insert(0, "x")
        self.assertEqual(field.get(), "nessquish")

    def test_on_change_fires_for_typing_but_not_for_placeholder(self):
        calls: List[int] = []
        field = self.make(placeholder="Поиск", on_change=lambda: calls.append(1))
        field.entry.event_generate("<FocusIn>")
        field.entry.event_generate("<FocusOut>")
        self.assertEqual(calls, [])
        field.entry.focus_force()
        self.settle()
        field.entry.insert(0, "а")
        field.entry.event_generate("<KeyRelease>", keysym="BackSpace")
        self.assertEqual(calls, [1])


class SegmentedTest(WidgetTestCase):
    def make(self, variant="tabs") -> Segmented:
        changes: List[int] = []
        seg = Segmented(
            self.root,
            ["Все · 4", "Не куплено · 3", "Куплено · 1"],
            0,
            changes.append,
            variant,
        )
        seg.pack()
        seg.changes = changes
        self.settle()
        return seg

    def test_click_selects_item(self):
        for variant in ("tabs", "outline"):
            seg = self.make(variant)
            left, right = seg._spans[1]
            click(seg, (left + right) // 2, 15)
            self.assertEqual(seg.active, 1)
            self.assertEqual(seg.changes, [1])

    def test_clicking_active_item_does_nothing(self):
        seg = self.make()
        left, right = seg._spans[0]
        click(seg, (left + right) // 2, 15)
        self.assertEqual(seg.changes, [])

    def test_select_is_silent(self):
        seg = self.make()
        seg.select(2)
        self.assertEqual(seg.active, 2)
        self.assertEqual(seg.changes, [])

    def test_set_items_updates_labels(self):
        seg = self.make()
        before = int(seg.cget("width"))
        seg.set_items(["Все · 1000", "Не куплено · 3", "Куплено · 1"])
        self.assertGreater(int(seg.cget("width")), before)

    def test_unknown_variant(self):
        with self.assertRaises(ValueError):
            Segmented(self.root, ["a"], variant="x")


class SwitchTest(WidgetTestCase):
    def test_toggle(self):
        values: List[bool] = []
        toggle = Toggle(self.root, True, values.append)
        toggle.pack()
        self.settle()
        click(toggle, 5, 5)
        click(toggle, 5, 5)
        self.assertEqual(values, [False, True])
        self.assertTrue(toggle.value)

    def test_toggle_set_is_silent(self):
        values: List[bool] = []
        toggle = Toggle(self.root, False, values.append)
        toggle.set(True)
        self.assertTrue(toggle.value)
        self.assertEqual(values, [])

    def test_checkbox(self):
        values: List[bool] = []
        box = Checkbox(self.root, False, values.append)
        box.pack()
        self.settle()
        click(box, 5, 5)
        self.assertTrue(box.value)
        box.set(False)
        self.assertFalse(box.value)
        self.assertEqual(values, [True])


class PaginationTest(WidgetTestCase):
    def make(self, page=1, pages=3):
        picked: List[int] = []
        pager = Pagination(self.root, page, pages, picked.append)
        pager.pack()
        pager.picked = picked
        self.settle()
        return pager

    def cell_x(self, index: int) -> int:
        return index * (Pagination.CELL + Pagination.GAP) + 5

    def test_page_buttons(self):
        pager = self.make()
        click(pager, self.cell_x(2), 5)  # цифра 2
        self.assertEqual(pager.picked, [2])

    def test_arrows(self):
        pager = self.make(page=2)
        click(pager, self.cell_x(4), 5)  # стрелка вперёд
        click(pager, self.cell_x(0), 5)  # стрелка назад
        self.assertEqual(pager.picked, [3, 2])

    def test_disabled_arrow_and_current_page_do_nothing(self):
        pager = self.make(page=1)
        click(pager, self.cell_x(0), 5)
        click(pager, self.cell_x(1), 5)
        self.assertEqual(pager.picked, [])

    def test_single_page(self):
        pager = self.make(page=1, pages=1)
        click(pager, self.cell_x(2), 5)
        self.assertEqual(pager.picked, [])


class DataTableTest(WidgetTestCase):
    def make(self) -> DataTable:
        table = DataTable(
            self.root,
            [
                Column("Название", 3),
                Column("Срок", 2, sorted=True),
                Column("", fixed=40),
            ],
        )
        table.pack(fill="x")
        self.settle()
        return table

    def test_rows_are_added_and_cleared(self):
        table = self.make()
        table.add_row(["Бинт", "01.01.2027", "x"])
        table.add_row(["Вата", "02.01.2027", "y"])
        self.settle()
        rows = [
            w
            for w in table._body.winfo_children()
            if isinstance(w, tk.Frame) and w.winfo_height() > 1
        ]
        self.assertEqual(len(rows), 2)
        table.clear()
        self.assertEqual(table._body.winfo_children(), [])

    def test_link_cell_calls_command(self):
        calls: List[int] = []
        table = self.make()
        row = table.add_row(
            [
                TextCell("Бинт", "primary", True, on_click=lambda: calls.append(1)),
                "-",
                "-",
            ]
        )
        self.settle()
        row.grid_slaves(column=0)[0].event_generate("<Button-1>")
        self.assertEqual(calls, [1])

    def test_widget_cells(self):
        table = self.make()
        row = table.add_row(
            ["Бинт", lambda parent: tk.Label(parent, text="виджет"), ""]
        )
        self.assertEqual(row.grid_slaves(column=1)[0].cget("text"), "виджет")

    def test_strike_and_muted_cells(self):
        table = self.make()
        row = table.add_row([TextCell("Витамин C", "ink_3", strike=True), "", ""])
        self.assertIn("overstrike", str(row.grid_slaves(column=0)[0].cget("font")))

    def test_selected_row_has_highlight(self):
        table = self.make()
        plain = table.add_row(["a", "b", "c"])
        chosen = table.add_row(["a", "b", "c"], selected=True)
        self.assertNotEqual(plain.cget("bg"), chosen.cget("bg"))

    def test_message_row(self):
        table = self.make()
        table.add_message("Ничего не найдено")
        self.settle()
        texts = [
            w.cget("text")
            for w in table._body.winfo_children()
            if isinstance(w, tk.Label)
        ]
        self.assertEqual(texts, ["Ничего не найдено"])

    def test_header_columns_follow_weights(self):
        table = self.make()
        lefts = table._fractions()
        self.assertEqual(lefts[0], 0)
        self.assertGreater(lefts[1], 0)
        self.assertAlmostEqual(table._width - lefts[2], 40, delta=1)
