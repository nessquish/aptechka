"""Экран «Настройки» (макет Figma, экран 13): профиль, пароль, уведомления, тема."""

import tkinter as tk
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from pharmacy.errors import NotFoundError, ValidationError
from pharmacy.ui import sections, theme
from pharmacy.ui.fonts import font_spec
from pharmacy.ui.theme import CARD_SHADOW_PAD, SHADOW_PAD, palette
from pharmacy.ui.widgets.badge import Badge
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.controls import Segmented, Toggle
from pharmacy.ui.widgets.field import TextField
from pharmacy.ui.widgets.page import PageHeader

if TYPE_CHECKING:
    from pharmacy.ui.screens.shell import MainShell

SECTION_PADDING_X = 20
SECTION_PADDING_Y = 18
CARD_GAP = 16 - 2 * CARD_SHADOW_PAD
FIELD_GAP = 2  # 10 px по макету минус поля под тень у соседних полей
THEMES = ((theme.LIGHT_THEME, "Светлая"), (theme.DARK_THEME, "Тёмная"))
DAYS_FIELD_WIDTH = 56
NOTICE_MS = 3000
SAVED = "Изменения сохранены"
DAYS_HINT = "Предупреждать заранее"


class SettingsScreen(tk.Frame):
    """Четыре карточки настроек и сохранение одной кнопкой."""

    def __init__(self, master: tk.Misc, shell: "MainShell") -> None:
        pal = palette()
        super().__init__(master, bg=pal.bg)
        self._shell = shell
        self._services = shell.services
        self._user = self._services.settings.get_user(shell.user.id)
        self._fields: Dict[str, TextField] = {}
        self._notice_job: Optional[str] = None
        self.bind("<Destroy>", self._on_destroy)
        self._header = PageHeader(self, "Настройки")
        self._header.pack(fill="x")
        Button(self._header.actions, "Отмена", command=self._cancel).pack(side="left")
        Button(
            self._header.actions,
            "Сохранить изменения",
            command=self._save,
            variant="primary",
        ).pack(side="left")
        grid = tk.Frame(self, bg=pal.bg)
        grid.pack(fill="x", pady=(18 - CARD_SHADOW_PAD - SHADOW_PAD, 0))
        grid.columnconfigure(0, weight=1, uniform="column")
        grid.columnconfigure(1, weight=1, uniform="column")
        self._build_profile(grid).grid(row=0, column=0, sticky="new")
        self._build_password(grid).grid(
            row=0, column=1, sticky="new", padx=(CARD_GAP, 0)
        )
        self._build_notifications(grid).grid(
            row=1, column=0, sticky="new", pady=(CARD_GAP, 0)
        )
        self._build_appearance(grid).grid(
            row=1, column=1, sticky="new", padx=(CARD_GAP, 0), pady=(CARD_GAP, 0)
        )
        notice = shell.take_notice()
        if notice:
            self._show_notice(notice)

    # --- общие части карточек ---

    def _section(self, master: tk.Misc, title: str, hint: str) -> Tuple[Card, tk.Frame]:
        """Карточка с заголовком и пояснением. Возвращает её и рамку для содержимого."""
        pal = palette()
        card = Card(master)
        inner = tk.Frame(card.body, bg=pal.card)
        inner.pack(
            fill="x",
            padx=SECTION_PADDING_X - card.inner_inset,
            pady=SECTION_PADDING_Y - card.inner_inset,
        )
        tk.Label(
            inner,
            text=title,
            bg=pal.card,
            fg=pal.ink,
            font=font_spec("section", self),
            padx=0,
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            inner,
            text=hint,
            bg=pal.card,
            fg=pal.ink_3,
            font=font_spec("small", self),
            padx=0,
        ).pack(anchor="w", pady=(0, 14))
        return card, inner

    def _field(self, inner: tk.Frame, key: str, label: str, **options) -> TextField:
        field = TextField(inner, label, **options)
        field.pack(fill="x", pady=(0, FIELD_GAP))
        self._fields[key] = field
        return field

    def _row(
        self, inner: tk.Frame, label: str, hint: str = "", first: bool = False
    ) -> Tuple[tk.Frame, Optional[tk.Label]]:
        """Строка настройки: слева название и пояснение, справа элемент управления.

        Returns:
            Рамка строки (в неё кладётся элемент управления) и подпись-пояснение.
        """
        pal = palette()
        if not first:
            tk.Frame(inner, bg=pal.line_soft, height=1).pack(fill="x")
        row = tk.Frame(inner, bg=pal.card)
        row.pack(fill="x", pady=9)
        texts = tk.Frame(row, bg=pal.card)
        texts.pack(side="left")
        tk.Label(
            texts,
            text=label,
            bg=pal.card,
            fg=pal.ink,
            font=font_spec("body", self),
            padx=0,
            pady=0,
        ).pack(anchor="w")
        note = None
        if hint:
            note = tk.Label(
                texts,
                text=hint,
                bg=pal.card,
                fg=pal.ink_3,
                font=font_spec("caption", self),
                padx=0,
                pady=0,
            )
            note.pack(anchor="w", pady=(2, 0))
        return row, note

    def _caption(self, row: tk.Frame, text: str) -> None:
        """Слово рядом с полем числа («за» и «дней»)."""
        pal = palette()
        tk.Label(
            row,
            text=text,
            bg=pal.card,
            fg=pal.ink_2,
            font=font_spec("body", self),
            padx=0,
        ).pack(side="right")

    # --- карточки ---

    def _build_profile(self, master: tk.Misc) -> Card:
        card, inner = self._section(master, "Профиль", "Данные вашей учётной записи")
        self._field(inner, "username", "Имя пользователя").set(self._user.username)
        self._field(inner, "login", "Логин", readonly=True).set(self._user.login)
        self._field(inner, "email", "Электронная почта").set(self._user.email)
        return card

    def _build_password(self, master: tk.Misc) -> Card:
        card, inner = self._section(master, "Смена пароля", "Не менее 8 символов")
        # Текущий пароль только показывается (значок «глаз»), изменить его здесь
        # нельзя. Он известен лишь из входа в этом сеансе: в базе только хэш.
        current = self._field(
            inner,
            "old_password",
            "Текущий пароль",
            placeholder="••••••••",
            password=True,
            readonly=True,
        )
        current.set(self._shell.app.session_password)
        self._field(
            inner,
            "new_password",
            "Новый пароль",
            placeholder="Введите новый пароль",
            password=True,
        )
        self._field(
            inner,
            "new_password_repeat",
            "Повторите новый пароль",
            placeholder="Повторите пароль",
            password=True,
        )
        return card

    def _build_notifications(self, master: tk.Misc) -> Card:
        card, inner = self._section(
            master, "Уведомления", "Когда приложение должно предупреждать"
        )
        row, _ = self._row(inner, "Срок годности истёк", first=True)
        self._expired = Toggle(row, self._user.notify_expired)
        self._expired.pack(side="right")

        row, self._days_hint = self._row(inner, "Скоро истекает срок", DAYS_HINT)
        self._caption(row, "дней")
        self._days = TextField(
            row,
            width=DAYS_FIELD_WIDTH,
            justify="center",
            on_change=self._days_edited,
        )
        self._days.set(str(self._user.warning_days))
        self._days.pack(side="right", padx=4)
        self._caption(row, "за")

        row, _ = self._row(inner, "Низкий остаток", "Когда количество ≤ минимального")
        self._low = Toggle(row, self._user.notify_low_stock)
        self._low.pack(side="right")
        return card

    def _build_appearance(self, master: tk.Misc) -> Card:
        card, inner = self._section(master, "Оформление", "Внешний вид приложения")
        row, _ = self._row(inner, "Тема", first=True)
        names = [name for _key, name in THEMES]
        current = [key for key, _name in THEMES].index(self._user.theme)
        self._theme = Segmented(
            row,
            names,
            current,
            # Тема применяется сразу, без кнопки «Сохранить изменения».
            lambda index: self._shell.set_theme(THEMES[index][0]),
            variant="outline",
        )
        self._theme.pack(side="right")

        row, _ = self._row(inner, "Размер текста")
        sizes = list(theme.TEXT_SIZES)
        self._text_size = Segmented(
            row,
            [theme.TEXT_SIZES[key][0] for key in sizes],
            sizes.index(theme.text_size_name()),
            # Как и тема, размер текста применяется сразу.
            lambda index: self._shell.set_text_size(sizes[index]),
            variant="outline",
        )
        self._text_size.pack(side="right")
        return card

    # --- сохранение ---

    def _days_edited(self) -> None:
        self._days.clear_error()
        self._days_hint.configure(text=DAYS_HINT, fg=palette().ink_3)

    def _clear_errors(self) -> None:
        for field in self._fields.values():
            field.clear_error()
        self._days_edited()

    def _save(self) -> None:
        """Сохраняет профиль, настройки и (если введён) новый пароль."""
        self._clear_errors()
        settings = self._services.settings
        user_id = self._user.id
        try:
            settings.update_profile(
                user_id,
                self._fields["username"].get(),
                self._fields["email"].get(),
            )
            settings.update_settings(
                user_id,
                self._days.get(),
                THEMES[self._theme.active][0],
                self._expired.value,
                self._low.value,
            )
            self._change_password_if_filled()
        except ValidationError as error:
            self._show_error(error)
            return
        except NotFoundError:
            self._shell.app.sign_out()
            return
        self._shell.app.apply_user_changes(settings.get_user(user_id), SAVED)

    def _change_password_if_filled(self) -> None:
        """Меняет пароль, если заполнено «Новый пароль» или его повтор.

        Текущий пароль для проверки берётся из сеанса, пользователь его не
        вводит: поле «Текущий пароль» только показывает его.
        """
        new = self._fields["new_password"].get()
        repeat = self._fields["new_password_repeat"].get()
        if not (new or repeat):
            return
        app = self._shell.app
        self._services.auth.change_password(
            self._user.id, app.session_password, new, repeat
        )
        app.session_password = new

    def _show_error(self, error: ValidationError) -> None:
        if error.field == "warning_days":
            self._days.set_error()
            self._days_hint.configure(text=error.message, fg=palette().red)
            return
        field = self._fields.get(error.field or "")
        if field is not None:
            field.set_error(error.message)
            field.focus_field()

    def _cancel(self) -> None:
        self._shell.navigate(sections.SETTINGS)

    # --- уведомление «сохранено» ---

    def _show_notice(self, text: str) -> None:
        actions = self._header.actions
        badge = Badge(actions, text, "green", icon="check")
        badge.pack(side="left", before=actions.winfo_children()[0], padx=(0, 10))
        self._notice_job = self.after(NOTICE_MS, badge.destroy)

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self and self._notice_job is not None:
            self.after_cancel(self._notice_job)
            self._notice_job = None
