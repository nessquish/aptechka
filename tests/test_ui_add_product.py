"""Тесты кнопки «Добавить товар в аптечку» и окна добавления товара."""

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from pharmacy.models import HistoryAction
from pharmacy.ui import sections
from pharmacy.ui.screens.dashboard import DashboardScreen
from pharmacy.ui.screens.my_kit import MyKitScreen
from pharmacy.ui.screens.product_form import ADD_TITLE, ProductFormDialog
from pharmacy.utils.dates import format_user_date
from tests.qt_helpers import ShellTestCase, click, find_all, type_text

BUTTON = "Добавить товар в аптечку"


class AddProductTestCase(ShellTestCase):
    def open_dialog(self) -> ProductFormDialog:
        self.buttons(BUTTON)[0].invoke()
        self.settle()
        return find_all(self.app, ProductFormDialog)[0]

    def dialogs(self):
        return find_all(self.app, ProductFormDialog)

    def fill(self, dialog, **values):
        defaults = dict(name="Аспирин", quantity="3", min_quantity="1")
        defaults.update(values)
        for key, value in defaults.items():
            dialog.fields[key].set(value)

    def names(self):
        return [row[0] for row in self.page.table.row_texts]


class AddButtonTest(AddProductTestCase):
    def test_dashboard_button_has_the_new_name(self):
        self.assertEqual(self.page.add_button.text(), BUTTON)
        self.assertEqual(self.buttons("Добавить товар"), [])

    def test_kit_buttons_have_the_new_name(self):
        self.open(sections.MY_KIT)
        self.assertEqual(self.page.add_button.text(), BUTTON)
        self.assertEqual(self.buttons("Добавить товар"), [])

    def test_empty_kit_button_has_the_new_name(self):
        self.db.execute("DELETE FROM products")
        self.open(sections.MY_KIT)
        self.assertEqual(len(self.buttons(BUTTON)), 1)

    def test_dashboard_button_opens_the_dialog_at_once(self):
        self.assertIsInstance(self.page, DashboardScreen)
        dialog = self.open_dialog()
        self.assertTrue(dialog.isVisible())
        # Промежуточного перехода в «Мою аптечку» нет: экран остался прежним.
        self.assertIsInstance(self.page, DashboardScreen)
        self.assertEqual(self.shell.section, sections.HOME)

    def test_kit_button_opens_the_dialog_over_the_kit(self):
        self.open(sections.MY_KIT)
        self.open_dialog()
        self.assertIsInstance(self.page, MyKitScreen)

    def test_empty_kit_button_opens_the_dialog(self):
        self.db.execute("DELETE FROM products")
        self.open(sections.MY_KIT)
        self.buttons(BUTTON)[0].invoke()
        self.settle()
        self.assertEqual(len(self.dialogs()), 1)

    def test_click_on_the_button_opens_exactly_one_window(self):
        click(self.page.add_button)
        self.settle()
        self.assertEqual(len(self.dialogs()), 1)

    def test_dialog_is_part_of_the_window(self):
        dialog = self.open_dialog()
        self.assertIs(dialog.parentWidget(), self.app)
        self.assertFalse(dialog.isWindow())


class DialogContentTest(AddProductTestCase):
    def test_title(self):
        dialog = self.open_dialog()
        texts = [w.text() for w in dialog.findChildren(type(dialog.cancel_button))]
        self.assertIn("Отмена", texts)
        self.assertEqual(ADD_TITLE, "Добавить товар в аптечку")

    def test_all_fields_of_the_form_are_there(self):
        dialog = self.open_dialog()
        self.assertEqual(
            set(dialog.fields),
            {
                "name",
                "category_id",
                "quantity",
                "unit",
                "expiry_date",
                "storage_place",
                "min_quantity",
                "indications",
                "note",
            },
        )
        for widget in dialog.fields.values():
            self.assertTrue(widget.isVisible())

    def test_added_date_is_today_and_cannot_be_edited(self):
        dialog = self.open_dialog()
        self.assertEqual(dialog.added_field.get(), format_user_date(date.today()))
        type_text(dialog.added_field.entry, "x")
        self.assertEqual(dialog.added_field.get(), format_user_date(date.today()))

    def test_defaults(self):
        dialog = self.open_dialog()
        self.assertIsNotNone(dialog.fields["category_id"].get())
        self.assertEqual(dialog.fields["unit"].get(), "упак.")
        self.assertEqual(dialog.fields["name"].get(), "")

    def test_dialog_fits_into_the_window(self):
        dialog = self.open_dialog()
        card = dialog.card
        self.assertGreaterEqual(card.y(), 0)
        self.assertLessEqual(card.y() + card.height(), self.app.height())
        self.assertLessEqual(card.x() + card.width(), self.app.width())

    def test_dialog_fits_at_the_largest_text_size(self):
        self.shell.set_text_size("large")
        self.settle()
        dialog = self.open_dialog()
        card = dialog.card
        self.assertLessEqual(card.height(), self.app.height())

    def test_note_is_multiline(self):
        dialog = self.open_dialog()
        dialog.fields["note"].set("строка 1\nстрока 2")
        self.assertEqual(dialog.fields["note"].get(), "строка 1\nстрока 2")


class SaveTest(AddProductTestCase):
    def test_saving_adds_the_product_and_closes_the_window(self):
        dialog = self.open_dialog()
        self.fill(
            dialog, expiry_date="01.01.2030", storage_place="Шкаф", note="заметка"
        )
        dialog.save_button.invoke()
        self.settle()
        self.assertEqual(self.dialogs(), [])
        added = self.services.products.list_products(self.app.user.id, search="аспирин")
        self.assertEqual(added[0].product.note, "заметка")
        self.assertEqual(str(added[0].product.expiry_date), "2030-01-01")
        self.assertEqual(added[0].product.storage_place, "Шкаф")

    def test_after_saving_the_new_product_is_in_the_kit_table(self):
        dialog = self.open_dialog()
        self.fill(dialog, expiry_date="01.01.2030")
        dialog.save_button.invoke()
        self.settle()
        self.assertIsInstance(self.page, MyKitScreen)
        self.assertEqual(self.shell.section, sections.MY_KIT)
        self.assertIn("Аспирин", self.names())
        self.assertEqual(self.page.table.row_count, 8)  # первая страница из 9 товаров

    def test_saving_from_the_kit_refreshes_the_table(self):
        self.open(sections.MY_KIT)
        before = len(self.names())
        dialog = self.open_dialog()
        self.fill(dialog, name="Анальгин", expiry_date="01.01.2020")
        dialog.save_button.invoke()
        self.settle()
        self.assertIsInstance(self.page, MyKitScreen)
        self.assertEqual(len(self.names()), before)  # страница та же, но
        self.assertIn("Анальгин", self.names())  # новый товар в таблице

    def test_table_is_sorted_by_expiry_after_adding(self):
        dialog = self.open_dialog()
        self.fill(dialog, name="Самый срочный", expiry_date="01.01.2000")
        dialog.save_button.invoke()
        self.settle()
        self.assertEqual(self.names()[0], "Самый срочный")
        dialog = self.open_dialog()
        self.fill(dialog, name="Без срока")
        dialog.save_button.invoke()
        self.settle()
        self.assertNotEqual(self.names()[0], "Без срока")

    def test_adding_is_written_to_the_history(self):
        dialog = self.open_dialog()
        self.fill(dialog)
        dialog.save_button.invoke()
        actions = [
            r.action for r in self.services.history.list_history(self.app.user.id)
        ]
        self.assertIn(HistoryAction.PRODUCT_ADDED, actions)

    def test_enter_saves_the_form(self):
        dialog = self.open_dialog()
        self.fill(dialog)
        QTest.keyClick(dialog, Qt.Key.Key_Return)
        self.settle()
        self.assertEqual(self.dialogs(), [])
        self.assertIn("Аспирин", self.names())

    def test_category_picked_from_the_list_is_saved(self):
        dialog = self.open_dialog()
        self.fill(dialog)
        category = self.services.products.list_categories()[-1]
        dialog.fields["category_id"]._pick(category.id)
        dialog.save_button.invoke()
        added = self.services.products.list_products(self.app.user.id, search="аспирин")
        self.assertEqual(added[0].product.category_id, category.id)

    def test_category_list_opens_inside_the_dialog(self):
        dialog = self.open_dialog()
        select = dialog.fields["category_id"]
        select.frame_pressed(None)
        self.settle()
        self.assertTrue(select.popup.isVisible())
        select.popup.close_list()


class ValidationTest(AddProductTestCase):
    def test_empty_name_keeps_the_window_open_and_marks_the_field(self):
        dialog = self.open_dialog()
        self.fill(dialog, name="")
        dialog.save_button.invoke()
        self.settle()
        self.assertEqual(len(self.dialogs()), 1)
        self.assertEqual(dialog.fields["name"].error, "Введите название")
        self.assertFalse(dialog.save_button.enabled)
        self.assertIsInstance(self.page, DashboardScreen)

    def test_bad_values_are_marked_on_their_fields(self):
        for key, value in {
            "quantity": "abc",
            "min_quantity": "-1",
            "expiry_date": "31.31.2030",
        }.items():
            dialog = self.open_dialog()
            self.fill(dialog, **{key: value})
            dialog._submit()
            self.assertIsNotNone(dialog.fields[key].error, key)
            dialog.close_modal()
            self.settle()

    def test_typing_after_an_error_enables_the_button_again(self):
        dialog = self.open_dialog()
        self.fill(dialog, name="")
        dialog._submit()
        self.assertFalse(dialog.save_button.enabled)
        dialog.fields["name"].entry.textEdited.emit("А")
        self.assertTrue(dialog.save_button.enabled)

    def test_nothing_is_added_when_the_form_is_wrong(self):
        before = len(self.services.products.list_products(self.app.user.id))
        dialog = self.open_dialog()
        self.fill(dialog, name="")
        dialog._submit()
        after = len(self.services.products.list_products(self.app.user.id))
        self.assertEqual(before, after)


class CancelTest(AddProductTestCase):
    def test_cancel_closes_without_adding(self):
        before = len(self.services.products.list_products(self.app.user.id))
        dialog = self.open_dialog()
        self.fill(dialog)
        dialog.cancel_button.invoke()
        self.settle()
        self.assertEqual(self.dialogs(), [])
        self.assertIsInstance(self.page, DashboardScreen)
        self.assertEqual(
            len(self.services.products.list_products(self.app.user.id)), before
        )

    def test_escape_closes_the_window(self):
        dialog = self.open_dialog()
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        self.settle()
        self.assertEqual(self.dialogs(), [])

    def test_the_window_can_be_opened_again_after_closing(self):
        self.open_dialog().close_modal()
        self.settle()
        self.assertEqual(len(self.open_dialog().fields["name"].get()), 0)
