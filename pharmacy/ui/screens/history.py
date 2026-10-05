"""Экран «История» (макет Figma, экран 12): действия, сгруппированные по дням."""

import tkinter as tk
from datetime import date, datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from pharmacy.models import HistoryRecord
from pharmacy.services.history_service import ACTION_LABELS
from pharmacy.ui import labels, periods
from pharmacy.ui.fonts import font_spec, line_height
from pharmacy.ui.theme import SHADOW_PAD, palette
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.iconbox import IconBox
from pharmacy.ui.widgets.page import PageHeader
from pharmacy.ui.widgets.select import Select
from pharmacy.utils.dates import format_user_date

if TYPE_CHECKING:
    from pharmacy.ui.screens.shell import MainShell

SEARCH_WIDTH = 200
SEARCH_DELAY_MS = 250
RECORD_LIMIT = 300
PADDING_X = 22
TIME_WIDTH = 42
EMPTY_TEXT = "Записей нет"


def day_title(day: date, today: Optional[date] = None) -> str:
    """Заголовок дня: «Сегодня, 01.10.2026» или просто дата."""
    text = format_user_date(day)
    if day == (today or date.today()):
        return f"Сегодня, {text}"
    return text


def group_by_day(records: List[HistoryRecord]) -> Dict[date, List[HistoryRecord]]:
    """Раскладывает записи по дням, сохраняя порядок (новые дни и записи первыми)."""
    groups: Dict[date, List[HistoryRecord]] = {}
    for record in records:
        day = datetime.strptime(record.created_at[:10], "%Y-%m-%d").date()
        groups.setdefault(day, []).append(record)
    return groups


class HistoryScreen(tk.Frame):
    """Лента действий с поиском по товару и фильтрами по действию и периоду."""

    def __init__(self, master: tk.Misc, shell: "MainShell") -> None:
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self._shell = shell
        self._services = shell.services
        self._user = shell.user
        self._query = ""
        self._action: Optional[str] = None
        self._period = periods.WEEK
        self._job: Optional[str] = None
        self.bind("<Destroy>", self._on_destroy)
        header = PageHeader(self, "История")
        header.pack(fill="x")
        gap = 8 - 2 * SHADOW_PAD
        self._search = TextField(
            header.actions,
            placeholder="Поиск по товару…",
            leading_icon="search",
            compact=True,
            width=SEARCH_WIDTH,
            on_change=self._on_search,
        )
        self._search.pack(side="left", padx=(0, gap))
        actions = [(None, "Все действия")] + list(ACTION_LABELS.items())
        Select(
            header.actions, actions, None, compact=True, on_change=self._on_action
        ).pack(side="left", padx=(0, gap))
        Select(
            header.actions,
            periods.PERIODS,
            self._period,
            compact=True,
            on_change=self._on_period,
        ).pack(side="left")
        self._card = Card(self)
        self._card.pack(fill="x")
        self._reload()

    # --- данные ---

    def _records(self) -> List[HistoryRecord]:
        records = self._services.history.list_history(
            self._user.id,
            action=self._action,
            since=periods.since(self._period),
            limit=RECORD_LIMIT,
        )
        if self._query:
            needle = self._query.casefold()
            records = [r for r in records if needle in r.description.casefold()]
        return records

    def _reload(self) -> None:
        pal = palette()
        for child in self._card.body.winfo_children():
            child.destroy()
        groups = group_by_day(self._records())
        if not groups:
            tk.Label(
                self._card.body,
                text=EMPTY_TEXT,
                bg=pal.card,
                fg=pal.ink_3,
                font=font_spec("body", self),
            ).pack(pady=40)
            return
        for day, records in groups.items():
            self._day(day)
            for index, record in enumerate(records):
                if index:
                    tk.Frame(self._card.body, bg=pal.line_soft, height=1).pack(
                        fill="x", padx=PADDING_X - self._card.inner_inset
                    )
                self._event(record)

    def _day(self, day: date) -> None:
        pal = palette()
        tk.Label(
            self._card.body,
            text=day_title(day),
            bg=pal.card,
            fg=pal.ink_3,
            font=font_spec("small_medium", self),
            anchor="w",
            padx=0,
        ).pack(fill="x", padx=PADDING_X - self._card.inner_inset, pady=(12, 4))

    def _event(self, record: HistoryRecord) -> None:
        pal = palette()
        row = tk.Frame(self._card.body, bg=pal.card)
        row.pack(fill="x", padx=PADDING_X - self._card.inner_inset, pady=7)
        clock = tk.Frame(
            row, bg=pal.card, width=TIME_WIDTH, height=line_height(self, "small")
        )
        clock.pack_propagate(False)
        clock.pack(side="left", padx=(0, 14 - SHADOW_PAD))
        tk.Label(
            clock,
            text=record.created_at[11:16],
            bg=pal.card,
            fg=pal.ink_3,
            font=font_spec("small", self),
            anchor="w",
            padx=0,
        ).pack(fill="both")
        IconBox(
            row,
            labels.HISTORY_ICONS[record.action],
            labels.HISTORY_TONES[record.action],
            "sm",
        ).pack(side="left", padx=(0, 14))
        texts = tk.Frame(row, bg=pal.card)
        texts.pack(side="left", fill="x", expand=True)
        tk.Label(
            texts,
            text=ACTION_LABELS[record.action],
            bg=pal.card,
            fg=pal.ink,
            font=font_spec("strong", self),
            padx=0,
            pady=0,
        ).pack(anchor="w")
        tk.Label(
            texts,
            text=record.description,
            bg=pal.card,
            fg=pal.ink_2,
            font=font_spec("small", self),
            padx=0,
            pady=0,
        ).pack(anchor="w", pady=(2, 0))

    # --- события ---

    def _on_search(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(SEARCH_DELAY_MS, self._apply_search)

    def _apply_search(self) -> None:
        self._job = None
        self._query = self._search.get().strip()
        self._reload()

    def _on_action(self, value: object) -> None:
        self._action = value
        self._reload()

    def _on_period(self, value: object) -> None:
        self._period = value
        self._reload()

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self and self._job is not None:
            self.after_cancel(self._job)
            self._job = None
