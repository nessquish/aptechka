"""Тесты экранов товаров: список, форма, карточка."""

from typing import List

from PySide6.QtWidgets import QLabel

from pharmacy.db.seed import seed_bulk
from pharmacy.models import HistoryAction
from pharmacy.services.status import ProductStatus
from pharmacy.ui import sections
from pharmacy.ui.screens.my_kit import PAGE_SIZE, MyKitScreen
from pharmacy.ui.screens.product_card import ProductCardScreen, _days_phrase
from pharmacy.ui.screens.product_form import ProductFormScreen
from pharmacy.ui.widgets.link import Link
from tests.qt_helpers import ShellTestCase, click, find_all


class KitTestCase(ShellTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.open(sections.MY_KIT)

    @property
    def kit(self) -> MyKitScreen:
        return self.page

    def names(self) -> List[str]:
        return [row[0] for row in self.kit.table.row_texts]

    def product_id(self, name: str) -> int:
        views = self.services.products.list_products(self.app.user.id)
        return next(v.product.id for v in views if v.product.name == name)


class MyKitTest(KitTestCase):
    def test_shows_all_products_sorted_by_expiry(self):
        names = self.names()
        self.assertEqual(len(names), 8)
        self.assertEqual(names[0], "Активированный уголь")
        self.assertEqual(names[-1], "Бинт")  # товар без срока уходит вниз

    def test_row_has_a_cell_for_every_column(self):
        for row in self.kit.table.row_texts:
            self.assertEqual(len(row), 7)

    def test_search_ignores_case(self):
        self.kit._search_field.set("ИБУ")
        self.kit._apply_search()
        self.assertEqual(self.names(), ["Ибупрофен"])

    def test_typing_in_search_filters_after_a_pause(self):
        self.kit._search_field.entry.setText("ибу")
        self.kit._search_field.entry.textEdited.emit("ибу")
        self.assertTrue(self.kit._search_timer.isActive())
        self.kit._search_timer.timeout.emit()
        self.assertEqual(self.names(), ["Ибупрофен"])

    def test_nothing_found_message(self):
        self.kit._search_field.set("zzz")
        self.kit._apply_search()
        self.settle()
        self.assertEqual(self.names(), [])
        texts = [w.text() for w in find_all(self.kit, QLabel)]
        self.assertIn("Ничего не найдено", texts)
        self.assertIn("Показано 0 из 0", texts)

    def test_category_filter(self):
        category = self.services.products.list_categories()[0].id
        self.kit._on_category(category)
        shown = self.kit.table.row_texts
        self.assertTrue(shown)
        for row in shown:
            self.assertEqual(row[1], "Лекарства")

    def test_status_filter(self):
        self.kit._on_status(ProductStatus.EXPIRED)
        self.assertEqual(self.names(), ["Активированный уголь"])

    def test_filters_are_in_the_toolbar_and_apply(self):
        self.kit.status_select._pick(ProductStatus.EXPIRED)
        self.assertEqual(self.names(), ["Активированный уголь"])
        self.assertEqual(self.kit.status_select.get(), ProductStatus.EXPIRED)

    def test_sorting_by_name(self):
        self.kit._on_sort("name")
        names = self.names()
        self.assertEqual(names, sorted(names, key=str.casefold))
        self.assertEqual(self.kit.table.sorted_column, 0)

    def test_sorting_by_date_added_has_no_arrow(self):
        self.kit._on_sort("added")
        self.assertIsNone(self.kit.table.sorted_column)

    def test_pagination(self):
        seed_bulk(self.db, self.app.user.id, count=20)
        self.open(sections.MY_KIT)
        self.assertEqual(len(self.names()), PAGE_SIZE)
        first = self.names()
        self.kit._on_page(2)
        self.assertEqual(len(self.names()), PAGE_SIZE)
        self.assertNotEqual(self.names(), first)
        self.kit._on_page(4)
        self.assertEqual(len(self.names()), 28 - 3 * PAGE_SIZE)

    def test_pagination_buttons_change_the_page(self):
        seed_bulk(self.db, self.app.user.id, count=20)
        self.open(sections.MY_KIT)
        pagination = self.kit.pagination
        click(pagination, pagination.cell_left(2) + 5, 10)  # кнопка «2»
        self.settle()
        self.assertEqual(self.kit._page, 2)

    def test_page_resets_after_filter(self):
        seed_bulk(self.db, self.app.user.id, count=20)
        self.open(sections.MY_KIT)
        self.kit._on_page(3)
        self.kit._search_field.set("ибу")
        self.kit._apply_search()
        self.assertEqual(self.kit._page, 1)

    def test_summary_counts_shown_rows(self):
        self.assertEqual(self.kit.summary.text(), "Показано 1–8 из 8")

    def test_product_name_opens_card(self):
        first = self.kit.table.cell_widgets(0)[0]
        click(first)
        self.settle()
        self.assertIsInstance(self.page, ProductCardScreen)

    def test_add_button_opens_form(self):
        self.buttons("Добавить товар")[0].invoke()
        self.settle()
        self.assertIsInstance(self.page, ProductFormScreen)
        self.assertFalse(self.page.editing)

    def test_empty_state_for_new_account(self):
        self.db.execute("DELETE FROM products")
        self.open(sections.MY_KIT)
        texts = [w.text() for w in find_all(self.kit, QLabel)]
        self.assertIn("В аптечке пока пусто", texts)
        self.assertFalse(hasattr(self.kit, "_table"))
        self.buttons("Добавить товар")[0].invoke()
        self.settle()
        self.assertIsInstance(self.page, ProductFormScreen)

    def test_pending_search_is_harmless_when_the_screen_closes(self):
        self.kit._on_search()
        self.assertTrue(self.kit._search_timer.isActive())
        self.open(sections.HOME)

    def test_table_columns_line_up(self):
        lefts = {
            tuple(
                cell.mapTo(self.kit, cell.rect().topLeft()).x()
                for cell in self.kit.table.cell_widgets(0)
            )
        }
        self.assertEqual(len(next(iter(lefts))), 8)
        self.assertEqual(len(set(next(iter(lefts)))), 1)


class ProductFormTest(KitTestCase):
    def open_form(self, product=None):
        self.shell.open_product_form(self.product_id(product) if product else None)
        self.settle()
        return self.page

    def fill(self, form, **values):
        defaults = dict(name="Аспирин", quantity="3", min_quantity="1")
        defaults.update(values)
        for key, value in defaults.items():
            form.fields[key].set(value)

    def test_add_product(self):
        form = self.open_form()
        self.fill(form, expiry_date="01.01.2030", storage_place="Шкаф", note="заметка")
        form._submit()
        self.settle()
        self.assertIsInstance(self.page, MyKitScreen)
        self.assertIn("Аспирин", self.names())
        added = self.services.products.list_products(self.app.user.id, search="аспирин")
        self.assertEqual(added[0].product.note, "заметка")
        self.assertEqual(str(added[0].product.expiry_date), "2030-01-01")

    def test_default_category_and_unit_are_chosen(self):
        form = self.open_form()
        self.assertIsNotNone(form.fields["category_id"].get())
        self.assertEqual(form.fields["unit"].get(), "упак.")

    def test_empty_name_shows_error_and_disables_save(self):
        form = self.open_form()
        self.fill(form, name="")
        form._submit()
        self.assertEqual(form.fields["name"].error, "Введите название")
        self.assertFalse(form.save_button.enabled)
        self.assertIsInstance(self.page, ProductFormScreen)

    def test_bad_values_are_marked_on_their_fields(self):
        cases = {
            "quantity": "abc",
            "min_quantity": "-1",
            "expiry_date": "31.31.2030",
        }
        for key, value in cases.items():
            form = self.open_form()
            self.fill(form, **{key: value})
            form._submit()
            self.assertIsNotNone(form.fields[key].error, key)

    def test_save_is_enabled_again_after_fixing_the_field(self):
        form = self.open_form()
        self.fill(form, name="")
        form._submit()
        self.assertFalse(form.save_button.enabled)
        form.fields["name"].set("Аспирин")
        form.fields["name"].clear_error()
        form._refresh_save()
        self.assertTrue(form.save_button.enabled)

    def test_typing_after_error_reenables_save(self):
        form = self.open_form()
        self.fill(form, name="")
        form._submit()
        field = form.fields["name"]
        field.entry.textEdited.emit("А")  # так Qt сообщает о правке пользователем
        self.settle()
        self.assertTrue(form.save_button.enabled)

    def test_edit_prefills_all_fields(self):
        form = self.open_form("Ибупрофен")
        self.assertTrue(form.editing)
        data = form.read_form()
        self.assertEqual(data.name, "Ибупрофен")
        self.assertEqual(data.quantity, "2")
        self.assertEqual(data.min_quantity, "3")
        self.assertEqual(data.storage_place, "Шкаф")
        self.assertRegex(data.expiry_date, r"^\d\d\.\d\d\.\d{4}$")
        self.assertTrue(data.category_id)

    def test_edit_saves_and_opens_card(self):
        form = self.open_form("Ибупрофен")
        form.fields["quantity"].set("10")
        form._submit()
        self.settle()
        self.assertIsInstance(self.page, ProductCardScreen)
        view = self.services.products.get_product(
            self.app.user.id, self.product_id("Ибупрофен")
        )
        self.assertEqual(view.product.quantity, 10)
        actions = [
            r.action for r in self.services.history.list_history(self.app.user.id)
        ]
        self.assertIn(HistoryAction.PRODUCT_UPDATED, actions)

    def test_cancel_goes_back(self):
        self.open_form()
        self.buttons("Отмена")[0].invoke()
        self.settle()
        self.assertIsInstance(self.page, MyKitScreen)
        self.open_form("Ибупрофен")
        self.buttons("Отмена")[0].invoke()
        self.settle()
        self.assertIsInstance(self.page, ProductCardScreen)

    def test_editing_deleted_product_returns_to_list(self):
        form = self.open_form("Ибупрофен")
        self.services.products.delete_product(
            self.app.user.id, self.product_id("Ибупрофен")
        )
        form._submit()
        self.settle()
        self.assertIsInstance(self.page, MyKitScreen)

    def test_multiline_note_is_saved(self):
        form = self.open_form()
        self.fill(form, note="первая строка\nвторая строка")
        form._submit()
        self.settle()
        added = self.services.products.list_products(self.app.user.id, search="аспирин")
        self.assertEqual(added[0].product.note, "первая строка\nвторая строка")


class ProductCardTest(KitTestCase):
    def open_card(self, name="Ибупрофен"):
        self.shell.open_product(self.product_id(name))
        self.settle()
        return self.page

    def texts(self, screen):
        return [w.text() for w in find_all(screen, QLabel)]

    def test_shows_product_data(self):
        card = self.open_card()
        texts = self.texts(card)
        self.assertIn("Ибупрофен", texts)
        self.assertIn("2 упак.", texts)
        self.assertIn("3 упак.", texts)
        self.assertIn("Шкаф", texts)
        self.assertIn("Жаропонижающее, обезболивающее", texts)

    def test_empty_fields_show_no_data(self):
        card = self.open_card("Бинт")
        texts = self.texts(card)
        self.assertGreaterEqual(texts.count("Нет данных"), 2)

    def test_days_left_is_shown_for_expiring_product(self):
        card = self.open_card()
        self.assertTrue(any("через" in t for t in self.texts(card)))

    def test_add_to_shopping_list(self):
        self.open_card("Витамин D")
        self.buttons("В список покупок")[0].invoke()
        self.settle()
        self.assertTrue(
            self.services.shopping.is_in_list(
                self.app.user.id, self.product_id("Витамин D")
            )
        )
        disabled = self.buttons("В списке покупок")
        self.assertEqual(len(disabled), 1)
        self.assertFalse(disabled[0].enabled)

    def test_edit_button_opens_form(self):
        self.open_card()
        self.buttons("Редактировать")[0].invoke()
        self.settle()
        form = self.page
        self.assertIsInstance(form, ProductFormScreen)
        self.assertTrue(form.editing)

    def test_back_link_returns_to_the_list(self):
        card = self.open_card()
        back = next(w for w in find_all(card, Link) if w.text() == "Назад к списку")
        click(back)
        self.settle()
        self.assertIsInstance(self.page, MyKitScreen)

    def test_delete_asks_confirmation(self):
        self.open_card()
        self.buttons("Удалить")[0].invoke()
        self.settle()
        cancel = self.buttons("Отмена")[0]
        cancel.invoke()
        self.settle()
        self.assertEqual(len(self.names_in_db()), 8)

    def test_confirmed_delete_removes_product_and_returns_to_list(self):
        self.open_card()
        self.buttons("Удалить")[0].invoke()
        self.settle()
        confirm = [b for b in self.buttons("Удалить") if b._variant == "danger_solid"][
            0
        ]
        confirm.invoke()
        self.settle()
        self.assertIsInstance(self.page, MyKitScreen)
        self.assertEqual(len(self.names_in_db()), 7)
        self.assertNotIn("Ибупрофен", self.names())

    def names_in_db(self):
        return self.services.products.list_products(self.app.user.id)

    def test_days_phrase(self):
        self.assertEqual(_days_phrase(19), "через 19 дней")
        self.assertEqual(_days_phrase(1), "через 1 день")
        self.assertEqual(_days_phrase(0), "истекает сегодня")
        self.assertEqual(_days_phrase(-3), "просрочено на 3 дня")
