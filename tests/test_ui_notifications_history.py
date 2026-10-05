"""Тесты экранов «Уведомления» и «История», периодов и прокрутки."""

import tkinter as tk
import unittest
from datetime import date, datetime, timedelta
from typing import List

from pharmacy.models import HistoryAction, NotificationKind
from pharmacy.ui import periods, sections
from pharmacy.ui.screens.history import (
    HistoryScreen,
    day_title,
    group_by_day,
)
from pharmacy.ui.screens.notifications import NotificationsScreen, _when
from pharmacy.ui.screens.product_card import ProductCardScreen
from pharmacy.ui.widgets.scroll import ScrollArea
from tests.test_ui_shell import ShellTestCase, find_all
from tests.test_ui_widgets import WidgetTestCase


class PeriodsTest(unittest.TestCase):
    TODAY = date(2026, 10, 5)

    def test_all_time_has_no_start(self):
        self.assertIsNone(periods.since(periods.ALL_TIME, self.TODAY))

    def test_today_week_month(self):
        self.assertEqual(periods.since(periods.TODAY, self.TODAY), self.TODAY)
        self.assertEqual(periods.since(periods.WEEK, self.TODAY), date(2026, 9, 29))
        self.assertEqual(periods.since(periods.MONTH, self.TODAY), date(2026, 9, 6))

    def test_unknown_period(self):
        with self.assertRaises(KeyError):
            periods.since("year", self.TODAY)

    def test_every_period_has_a_label(self):
        keys = {key for key, _ in periods.PERIODS}
        self.assertEqual(keys, {"all", "today", "week", "month"})


class HelpersTest(unittest.TestCase):
    def test_when_today_and_other_day(self):
        today = date(2026, 10, 5)
        self.assertEqual(_when("2026-10-05 09:00:12", today), "сегодня, 09:00")
        self.assertEqual(_when("2026-09-30 18:30:00", today), "30.09.2026")

    def test_day_title(self):
        today = date(2026, 10, 1)
        self.assertEqual(day_title(today, today), "Сегодня, 01.10.2026")
        self.assertEqual(day_title(date(2026, 9, 30), today), "30.09.2026")

    def test_group_by_day_keeps_order(self):
        class Record:
            def __init__(self, stamp):
                self.created_at = stamp

        records = [
            Record("2026-10-03 10:00:00"),
            Record("2026-10-03 09:00:00"),
            Record("2026-10-01 12:00:00"),
        ]
        groups = group_by_day(records)
        self.assertEqual(list(groups), [date(2026, 10, 3), date(2026, 10, 1)])
        self.assertEqual(len(groups[date(2026, 10, 3)]), 2)


class NotificationsTest(ShellTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.shell.navigate(sections.NOTIFICATIONS)
        self.settle()

    @property
    def page(self) -> NotificationsScreen:
        return self.shell._current

    def notifications(self):
        return self.services.notifications.list_notifications(self.app.user.id)

    def titles(self) -> List[str]:
        names = {
            "Срок годности истёк",
            "Скоро истекает срок годности",
            "Низкий остаток",
        }
        return [
            w.cget("text")
            for w in find_all(self.page._card, tk.Label)
            if w.cget("text") in names
        ]

    def test_lists_all_notifications(self):
        self.assertEqual(len(self.titles()), len(self.notifications()))

    def test_tab_labels_have_counts(self):
        total = len(self.notifications())
        labels = self.page._tab_labels()
        self.assertEqual(labels[0], f"Все · {total}")
        self.assertEqual(labels[1], f"Непрочитанные · {total}")

    def test_expiry_tab_shows_only_expiry_kinds(self):
        self.page._on_tab(2)
        kinds = {n.kind for n in self.page._visible()}
        self.assertTrue(kinds <= {NotificationKind.EXPIRED, NotificationKind.EXPIRING})
        self.assertTrue(kinds)

    def test_low_stock_tab(self):
        self.page._on_tab(3)
        kinds = {n.kind for n in self.page._visible()}
        self.assertEqual(kinds, {NotificationKind.LOW_STOCK})

    def test_read_all_updates_everything(self):
        self.buttons("Прочитать все")[0].invoke()
        self.settle()
        self.assertEqual(self.services.notifications.count_unread(self.app.user.id), 0)
        self.assertTrue(self.page._tab_labels()[1].endswith("· 0"))
        self.page._on_tab(1)
        self.assertEqual(self.titles(), [])
        self.assertIn(
            "Уведомлений нет", [w.cget("text") for w in find_all(self.page, tk.Label)]
        )

    def test_unread_tab_hides_read_items(self):
        first = self.notifications()[0]
        self.services.notifications.mark_read(self.app.user.id, first.id)
        self.page._on_tab(1)
        self.assertNotIn(first.id, [n.id for n in self.page._visible()])

    def test_period_filter(self):
        first = self.notifications()[0]
        self.db.execute(
            "UPDATE notifications SET created_at = '2020-01-01 10:00:00' WHERE id = ?",
            (first.id,),
        )
        self.page._on_period(periods.WEEK)
        self.assertNotIn(first.id, [n.id for n in self.page._visible()])
        self.page._on_period(periods.ALL_TIME)
        self.assertIn(first.id, [n.id for n in self.page._visible()])

    def test_delete_removes_one_notification(self):
        before = len(self.notifications())
        self.page._delete(self.notifications()[0].id)
        self.assertEqual(len(self.notifications()), before - 1)

    def test_delete_of_missing_notification_is_ignored(self):
        self.page._delete(99999)

    def test_open_product_marks_read_and_opens_card(self):
        target = self.notifications()[0]
        self.buttons("Открыть товар")[0].invoke()
        self.settle()
        self.assertIsInstance(self.shell._current, ProductCardScreen)
        refreshed = self.services.notifications.list_notifications(self.app.user.id)
        self.assertTrue(next(n for n in refreshed if n.id == target.id).is_read)

    def test_add_to_list_replaces_button_with_badge(self):
        add = self.buttons("В список покупок")
        self.assertTrue(add)
        before = len(self.services.shopping.list_items(self.app.user.id, False))
        add[0].invoke()
        self.settle()
        after = len(self.services.shopping.list_items(self.app.user.id, False))
        self.assertEqual(after, before + 1)
        self.assertEqual(len(self.buttons("В список покупок")), len(add) - 1)

    def test_sidebar_counter_follows_reading(self):
        self.buttons("Прочитать все")[0].invoke()
        self.settle()
        self.assertEqual(self.shell._sidebar._items[sections.NOTIFICATIONS]._count, 0)


class HistoryTest(ShellTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.db.execute("UPDATE history SET created_at = datetime('now','localtime')")
        self.db.execute(
            "UPDATE history SET created_at = ? WHERE action = ?",
            (
                (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S"),
                HistoryAction.PRODUCT_ADDED,
            ),
        )
        self.shell.navigate(sections.HISTORY)
        self.settle()

    @property
    def page(self) -> HistoryScreen:
        return self.shell._current

    def descriptions(self) -> List[str]:
        return [r.description for r in self.page._records()]

    def test_default_period_is_week(self):
        for description in self.descriptions():
            self.assertNotIn("добавлен в аптечку", description)

    def test_all_time_shows_old_records(self):
        self.page._on_period(periods.ALL_TIME)
        self.assertTrue(any("добавлен в аптечку" in d for d in self.descriptions()))

    def test_action_filter(self):
        self.page._on_period(periods.ALL_TIME)
        self.page._on_action(HistoryAction.PRODUCT_ADDED)
        records = self.page._records()
        self.assertTrue(records)
        self.assertEqual({r.action for r in records}, {HistoryAction.PRODUCT_ADDED})

    def test_search_by_product_name(self):
        self.page._on_period(periods.ALL_TIME)
        self.page._search.set("ПАРАЦЕТАМОЛ")
        self.page._apply_search()
        self.assertTrue(self.descriptions())
        for description in self.descriptions():
            self.assertIn("парацетамол", description.casefold())

    def test_nothing_found_message(self):
        self.page._search.set("zzzz")
        self.page._apply_search()
        texts = [w.cget("text") for w in find_all(self.page, tk.Label)]
        self.assertIn("Записей нет", texts)

    def test_groups_are_titled_by_day(self):
        texts = [w.cget("text") for w in find_all(self.page, tk.Label)]
        self.assertIn(day_title(date.today()), texts)

    def test_event_shows_time_and_title(self):
        texts = [w.cget("text") for w in find_all(self.page, tk.Label)]
        self.assertTrue(
            any(t in texts for t in ("Изменение товара", "Удаление товара"))
        )
        self.assertTrue(any(len(t) == 5 and t[2] == ":" for t in texts))

    def test_search_job_is_cancelled_on_close(self):
        self.page._on_search()
        self.assertIsNotNone(self.page._job)
        self.shell.navigate(sections.HOME)
        self.settle()


class ScrollAreaTest(WidgetTestCase):
    def make(self, content_height: int) -> ScrollArea:
        self.root.geometry("300x200+0+0")
        area = ScrollArea(self.root)
        area.pack(fill="both", expand=True)
        tk.Frame(area.body, height=content_height, bg="white").pack(fill="x")
        self.settle()
        return area

    def test_short_content_does_not_scroll(self):
        area = self.make(50)
        self.assertEqual(area._overflow(), 0)
        area._on_wheel(type("E", (), {"delta": -120})())
        self.assertEqual(area._canvas.canvasy(0), 0)
        self.assertEqual(area._bar.find_all(), ())

    def test_long_content_scrolls_with_wheel(self):
        area = self.make(600)
        self.assertGreater(area._overflow(), 0)
        self.assertTrue(area._bar.find_all())
        area._on_wheel(type("E", (), {"delta": -120})())
        self.assertGreater(area._canvas.canvasy(0), 0)
        area._on_wheel(type("E", (), {"delta": 120})())
        self.assertEqual(area._canvas.canvasy(0), 0)

    def test_cannot_scroll_past_the_end(self):
        area = self.make(300)
        for _ in range(50):
            area._on_wheel(type("E", (), {"delta": -120})())
        self.assertAlmostEqual(area._canvas.canvasy(0), area._overflow(), delta=1)

    def test_dragging_the_thumb(self):
        area = self.make(600)
        top, bottom = area._thumb_span()
        press = type("E", (), {"y": (top + bottom) / 2})()
        area._on_bar_press(press)
        area._on_bar_drag(type("E", (), {"y": (top + bottom) / 2 + 40})())
        self.assertGreater(area._canvas.canvasy(0), 0)

    def test_scroll_to_top(self):
        area = self.make(600)
        area._on_wheel(type("E", (), {"delta": -120})())
        area.scroll_to_top()
        self.assertEqual(area._canvas.canvasy(0), 0)
