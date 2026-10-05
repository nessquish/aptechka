"""Экран «Уведомления» (макет Figma, экран 11)."""

import tkinter as tk
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from pharmacy.errors import NotFoundError, ValidationError
from pharmacy.models import Notification, NotificationKind
from pharmacy.services.notification_service import KIND_LABELS
from pharmacy.ui import labels, periods, theme
from pharmacy.ui.drawing import rounded_box
from pharmacy.ui.fonts import font_spec, line_height
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD, palette
from pharmacy.ui.widgets.badge import Badge, measure_badge
from pharmacy.ui.widgets.button import Button, measure_button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.common import photo
from pharmacy.ui.widgets.controls import Segmented
from pharmacy.ui.widgets.highlight import Highlight
from pharmacy.ui.widgets.iconbox import IconBox
from pharmacy.ui.widgets.page import PageHeader
from pharmacy.ui.widgets.select import Select
from pharmacy.utils.dates import format_user_date

if TYPE_CHECKING:
    from pharmacy.ui.screens.shell import MainShell

# Вкладки: (подпись, вид уведомления или None, только непрочитанные).
TABS = (
    ("Все", None, False),
    ("Непрочитанные", None, True),
    ("Срок годности", "expiry", False),
    ("Низкий остаток", NotificationKind.LOW_STOCK, False),
)
EXPIRY_KINDS = (NotificationKind.EXPIRED, NotificationKind.EXPIRING)
ROW_PADDING_X = 18
ROW_PADDING_Y = 9
WHEN_WIDTH = 100
ADD_TO_LIST_TEXT = "В список покупок"
IN_LIST_TEXT = "В списке покупок"
DOT = 6
EMPTY_TEXT = "Уведомлений нет"


def _when(created_at: str, today: Optional[date] = None) -> str:
    """Время уведомления: «сегодня, 09:00» или дата."""
    created = datetime.strptime(created_at[:19], "%Y-%m-%d %H:%M:%S")
    if created.date() == (today or date.today()):
        return f"сегодня, {created:%H:%M}"
    return format_user_date(created.date())


class NotificationsScreen(tk.Frame):
    """Список уведомлений с вкладками, периодом и действиями."""

    def __init__(self, master: tk.Misc, shell: "MainShell") -> None:
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self._shell = shell
        self._services = shell.services
        self._user = shell.user
        self._tab = 0
        self._measure_actions()
        self._period = periods.ALL_TIME
        header = PageHeader(self, "Уведомления")
        header.pack(fill="x")
        Select(
            header.actions,
            periods.PERIODS,
            self._period,
            compact=True,
            on_change=self._on_period,
        ).pack(side="left", padx=(0, 8 - 2 * SHADOW_PAD))
        Button(header.actions, "Прочитать все", command=self._read_all).pack(
            side="left"
        )
        self._build_tabs()
        self._card = Card(self)
        self._card.pack(fill="x", pady=(0, 0))
        self._reload()

    # --- вкладки ---

    def _build_tabs(self) -> None:
        pal = palette()
        row = tk.Frame(self, bg=pal.bg)
        row.pack(fill="x", pady=(12 - SHADOW_PAD, 12 - SHADOW_PAD))
        self._tabs = Segmented(row, self._tab_labels(), self._tab, self._on_tab)
        self._tabs.pack(side="left", padx=(CARD_SHADOW_PAD - SHADOW_PAD, 0))
        days = self._user.warning_days
        tk.Label(
            row,
            text=f"Предупреждение о сроке — за {days} дн. (меняется в Настройках)",
            bg=pal.bg,
            fg=pal.ink_3,
            font=font_spec("small", self),
            padx=0,
        ).pack(side="right", padx=CARD_SHADOW_PAD)

    def _tab_labels(self) -> List[str]:
        items = self._period_items()
        unread = sum(1 for item in items if not item.is_read)
        return [
            f"Все · {len(items)}",
            f"Непрочитанные · {unread}",
            TABS[2][0],
            TABS[3][0],
        ]

    # --- данные ---

    def _period_items(self) -> List[Notification]:
        return self._services.notifications.list_notifications(
            self._user.id, since=periods.since(self._period)
        )

    def _visible(self) -> List[Notification]:
        _label, kind, unread_only = TABS[self._tab]
        items = self._period_items()
        if unread_only:
            items = [item for item in items if not item.is_read]
        if kind == "expiry":
            items = [item for item in items if item.kind in EXPIRY_KINDS]
        elif kind is not None:
            items = [item for item in items if item.kind == kind]
        return items

    def _reload(self) -> None:
        """Перерисовывает вкладки и список и обновляет счётчик в меню."""
        self._tabs.set_items(self._tab_labels())
        for child in self._card.body.winfo_children():
            child.destroy()
        items = self._visible()
        if not items:
            tk.Label(
                self._card.body,
                text=EMPTY_TEXT,
                bg=palette().card,
                fg=palette().ink_3,
                font=font_spec("body", self),
            ).pack(pady=40)
        for index, item in enumerate(items):
            if index:
                tk.Frame(self._card.body, bg=palette().line, height=1).pack(fill="x")
            self._row(item)
        self._shell.refresh_counters()

    # --- строка ---

    def _row(self, item: Notification) -> None:
        pal = palette()
        background = pal.card if item.is_read else pal.unread_bg
        # Подсветка непрочитанного: скруглённая плашка, а не прямоугольник у края
        # карточки. У прочитанных строк плашка того же цвета, что карточка, поэтому
        # размеры строк одинаковые.
        row = Highlight(self._card.body, background)
        row.pack(fill="x")
        if not item.is_read:
            self._dot(row.body, background)
        inner = tk.Frame(row.body, bg=background)
        inner.pack(
            fill="x",
            padx=ROW_PADDING_X
            - self._card.inner_inset
            - SHADOW_PAD
            - row.padding_x
            + 4,
            pady=ROW_PADDING_Y - row.padding_y,
        )
        IconBox(
            inner,
            labels.NOTIFICATION_ICONS[item.kind],
            labels.NOTIFICATION_TONES[item.kind],
        ).pack(side="left", padx=(SHADOW_PAD, 14))
        self._build_close(inner, background, item)
        self._build_actions(inner, background, item)
        when = tk.Frame(
            inner,
            bg=background,
            width=WHEN_WIDTH,
            height=line_height(self, "caption"),
        )
        when.pack_propagate(False)
        when.pack(side="right", padx=(8, 8))
        tk.Label(
            when,
            text=_when(item.created_at),
            bg=background,
            fg=pal.ink_3,
            font=font_spec("caption", self),
            anchor="e",
            padx=0,
        ).pack(fill="both")
        texts = tk.Frame(inner, bg=background)
        texts.pack(side="left", fill="x", expand=True)
        tk.Label(
            texts,
            text=KIND_LABELS[item.kind],
            bg=background,
            fg=pal.ink,
            font=font_spec("strong", self),
            padx=0,
            pady=0,
        ).pack(anchor="w")
        tk.Label(
            texts,
            text=item.message,
            bg=background,
            fg=pal.ink_2,
            font=font_spec("small", self),
            padx=0,
            pady=0,
        ).pack(anchor="w", pady=(3, 0))

    def _dot(self, row: tk.Frame, background: str) -> None:
        """Точка слева у непрочитанного уведомления."""
        canvas = tk.Canvas(
            row, width=DOT, height=DOT, bd=0, highlightthickness=0, bg=background
        )
        canvas.image = photo(rounded_box(DOT, DOT, DOT // 2, palette().primary), canvas)
        canvas.create_image(0, 0, image=canvas.image, anchor="nw")
        canvas.place(x=0, rely=0.5, anchor="w")

    def _build_close(
        self, inner: tk.Frame, background: str, item: Notification
    ) -> None:
        close = tk.Label(inner, bg=background, cursor="hand2", padx=0)
        close.image = photo(render_icon("x", 15, palette().ink_3), close)
        close.configure(image=close.image)
        close.pack(side="right", padx=(8, 0))
        close.bind("<Button-1>", lambda _event, i=item.id: self._delete(i))

    def _build_actions(
        self, inner: tk.Frame, background: str, item: Notification
    ) -> None:
        # Два столбца фиксированной ширины: «Открыть товар» и «В список покупок»
        # (или плашка «В списке покупок»). У всех строк они стоят ровно друг под другом.
        height = theme.CONTROL_HEIGHT_SMALL + 2 * SHADOW_PAD
        box = tk.Frame(inner, bg=background, width=self._actions_width, height=height)
        box.pack_propagate(False)
        box.pack(side="right")
        Button(
            box,
            "Открыть товар",
            command=lambda: self._open_product(item),
            size="sm",
            width=self._open_width,
        ).pack(side="left")
        slot = tk.Frame(
            box, bg=background, width=self._list_width + 2 * SHADOW_PAD, height=height
        )
        slot.pack_propagate(False)
        slot.pack(side="left")
        if self._services.shopping.is_in_list(self._user.id, item.product_id):
            Badge(slot, IN_LIST_TEXT, "green", icon="check").pack(
                side="left", padx=SHADOW_PAD
            )
        else:
            Button(
                slot,
                ADD_TO_LIST_TEXT,
                command=lambda: self._add_to_list(item),
                variant="primary",
                size="sm",
                icon="plus",
                width=self._list_width,
            ).pack(side="left")

    def _measure_actions(self) -> None:
        """Считает ширину столбцов кнопок: по самому широкому содержимому."""
        self._open_width = measure_button(self, "Открыть товар", "sm")
        self._list_width = max(
            measure_button(self, ADD_TO_LIST_TEXT, "sm", "plus"),
            measure_badge(self, IN_LIST_TEXT, "check"),
        )
        self._actions_width = self._open_width + self._list_width + 4 * SHADOW_PAD

    # --- действия ---

    def _on_tab(self, index: int) -> None:
        self._tab = index
        self._reload()

    def _on_period(self, value: object) -> None:
        self._period = value
        self._reload()

    def _read_all(self) -> None:
        self._services.notifications.mark_all_read(self._user.id)
        self._reload()

    def _mark_read(self, item: Notification) -> None:
        try:
            self._services.notifications.mark_read(self._user.id, item.id)
        except NotFoundError:
            pass

    def _open_product(self, item: Notification) -> None:
        self._mark_read(item)
        self._shell.open_product(item.product_id)

    def _add_to_list(self, item: Notification) -> None:
        self._mark_read(item)
        try:
            self._services.shopping.add_from_product(self._user.id, item.product_id)
        except (NotFoundError, ValidationError):
            pass
        self._reload()

    def _delete(self, notification_id: int) -> None:
        try:
            self._services.notifications.delete(self._user.id, notification_id)
        except NotFoundError:
            pass
        self._reload()
