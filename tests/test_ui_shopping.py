"""Тесты экрана списка покупок и окна добавления."""

import tkinter as tk
from typing import List

from pharmacy.ui import sections
from pharmacy.ui.screens.product_card import ProductCardScreen
from pharmacy.ui.screens.shopping import AddItemDialog, ShoppingScreen
from pharmacy.ui.widgets.combo import ComboField
from pharmacy.ui.widgets.controls import Checkbox
from tests.test_ui_products import row_texts
from tests.test_ui_shell import ShellTestCase, find_all


class ShoppingTestCase(ShellTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.shell.navigate(sections.SHOPPING)
        self.settle()

    @property
    def page(self) -> ShoppingScreen:
        return self.shell._current

    def names(self) -> List[str]:
        return [row[0] for row in row_texts(self.page._table)]

    def boxes(self) -> List[Checkbox]:
        rows = [
            c for c in self.page._table._body.winfo_children() if c.winfo_children()
        ]
        return [
            next(w for w in row.winfo_children() if isinstance(w, Checkbox))
            for row in rows
        ]

    def items(self, bought=None):
        return self.services.shopping.list_items(self.app.user.id, bought)

    def pick(self, index: int) -> None:
        """Отмечает флажок в строке так, как это делает нажатие мышью."""
        self.boxes()[index]._on_click(None)
        self.settle()


class ShoppingScreenTest(ShoppingTestCase):
    def test_lists_all_items_open_first(self):
        self.assertEqual(len(self.names()), 4)
        self.assertEqual(self.names()[-1], "Витамин C")

    def test_tab_labels_show_counts(self):
        self.assertEqual(
            self.page._tab_labels(), ["Все · 4", "Не куплено · 3", "Куплено · 1"]
        )

    def test_tabs_filter_the_list(self):
        self.page._on_tab(1)
        self.assertEqual(len(self.names()), 3)
        self.assertNotIn("Витамин C", self.names())
        self.page._on_tab(2)
        self.assertEqual(self.names(), ["Витамин C"])

    def test_table_cells(self):
        rows = {row[0]: row for row in row_texts(self.page._table)}
        self.assertEqual(rows["Бинт"][1], "2 шт.")
        self.assertEqual(rows["Бинт"][2], "Уведомление")
        self.assertEqual(rows["Пластыри"][2], "Вручную")
        self.assertRegex(rows["Бинт"][3], r"\d\d\.\d\d\.\d{4}")

    def test_bar_is_hidden_without_selection(self):
        self.assertFalse(self.page._bar.winfo_ismapped())

    def test_selecting_rows_shows_bar_with_count(self):
        self.pick(0)
        self.pick(1)
        self.assertTrue(self.page._bar.winfo_ismapped())
        self.assertEqual(self.page._bar._text, "Выбрано: 2")

    def test_unselecting_hides_bar(self):
        self.pick(0)
        self.pick(0)
        self.assertFalse(self.page._bar.winfo_ismapped())

    def test_select_all(self):
        self.page._toggle_all(True)
        self.settle()
        self.assertEqual(self.page._bar._text, "Выбрано: 4")
        self.assertTrue(self.page._select_all.value)
        self.page._toggle_all(False)
        self.assertEqual(self.page._selected, set())

    def test_selection_is_cleared_when_tab_changes(self):
        self.pick(0)
        self.page._on_tab(2)
        self.assertEqual(self.page._selected, set())

    def test_mark_bought(self):
        self.pick(0)
        self.pick(1)
        self.buttons("Отметить как купленные")[0].invoke()
        self.settle()
        self.assertEqual(len(self.items(bought=True)), 3)
        self.assertEqual(self.page._selected, set())
        self.assertFalse(self.page._bar.winfo_ismapped())

    def test_remove_selected(self):
        self.pick(2)
        self.buttons("Удалить из списка")[0].invoke()
        self.settle()
        self.assertEqual(len(self.items()), 3)
        self.assertEqual(len(self.names()), 3)

    def test_linked_item_opens_the_product_card(self):
        row = next(
            c for c in self.page._table._body.winfo_children() if c.winfo_children()
        )
        row.grid_slaves(column=1)[0].event_generate("<Button-1>")
        self.settle()
        self.assertIsInstance(self.shell._current, ProductCardScreen)

    def test_empty_list_message(self):
        self.db.execute("DELETE FROM shopping_list")
        self.shell.navigate(sections.SHOPPING)
        self.settle()
        texts = [w.cget("text") for w in find_all(self.page, tk.Label)]
        self.assertTrue(any("Список покупок пуст" in t for t in texts))


class AddItemDialogTest(ShoppingTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.dialog = AddItemDialog(
            self.app, self.services, self.app.user.id, self.page._reload
        )
        self.settle()

    def test_button_opens_the_dialog(self):
        self.dialog.close()
        self.settle()
        self.assertEqual(find_all(self.app, ComboField), [])
        self.buttons("Добавить вручную")[0].invoke()
        self.settle()
        self.assertEqual(len(find_all(self.app, ComboField)), 1)

    def test_defaults(self):
        self.assertEqual(self.dialog.quantity.get(), "1")
        self.assertEqual(self.dialog.unit.get(), "шт.")
        self.assertEqual(self.dialog.name.get(), "")

    def test_adds_manual_item_and_refreshes_list(self):
        self.dialog.name.set("Перекись водорода")
        self.dialog.quantity.set("2")
        self.dialog._submit()
        self.settle()
        self.assertIn("Перекись водорода", self.names())
        item = next(i for i in self.items() if i.name == "Перекись водорода")
        self.assertEqual((item.quantity, item.unit), (2, "шт."))
        self.assertEqual(find_all(self.app, ComboField), [])

    def test_empty_name_is_marked(self):
        self.dialog._submit()
        self.assertEqual(self.dialog.name.error, "Введите название")
        self.assertEqual(len(self.items()), 4)

    def test_bad_quantity_is_marked(self):
        self.dialog.name.set("Вата")
        self.dialog.quantity.set("0")
        self.dialog._submit()
        self.assertIsNotNone(self.dialog.quantity.error)

    def test_cancel_closes_without_adding(self):
        self.buttons("Отмена")[0].invoke()
        self.settle()
        self.assertEqual(find_all(self.app, ComboField), [])
        self.assertEqual(len(self.items()), 4)

    def test_choice_from_list_fills_the_name(self):
        field = self.dialog.name
        field._pick("Ибупрофен")
        self.assertEqual(field.get(), "Ибупрофен")

    def test_choices_are_products_of_the_kit(self):
        self.assertIn("Ибупрофен", self.dialog.name._choices)
        self.assertEqual(len(self.dialog.name._choices), 8)

    def test_arrow_opens_the_list(self):
        field = self.dialog.name
        canvas = field.entry.master
        canvas.event_generate("<ButtonPress-1>", x=canvas.winfo_width() - 15, y=15)
        self.settle()
        self.assertIsNotNone(field._popup)
        field._popup.close()
        self.assertIsNone(field._popup)
