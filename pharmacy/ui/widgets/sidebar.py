"""Боковое меню: разделы, счётчик уведомлений, пользователь и выход."""

import tkinter as tk
from typing import Callable, Dict, Sequence

from pharmacy.models import User
from pharmacy.ui import theme
from pharmacy.ui.drawing import Shadow, rounded_box
from pharmacy.ui.fonts import font_spec, line_height, text_width
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import mix, palette
from pharmacy.ui.widgets.common import parent_bg, photo

NAV_RADIUS = 10
NAV_PAD = 3  # поле под тень выбранного пункта
NAV_PADDING_X = 12
NAV_PADDING_Y = 9
COUNTER_PADDING_X = 7
COUNTER_PADDING_Y = 1
AVATAR_SIZE = 26


class NavItem(tk.Canvas):
    """Пункт меню: название, выделение выбранного и необязательный счётчик."""

    def __init__(self, master: tk.Misc, text: str, command: Callable[[], None]) -> None:
        super().__init__(
            master, bd=0, highlightthickness=0, bg=parent_bg(master), cursor="hand2"
        )
        self._text = text
        self._command = command
        self._active = False
        self._hover = False
        self._count = 0
        self._width = 0
        self._images: list = []
        self._height = line_height(self, "body") + 2 * NAV_PADDING_Y
        self.configure(height=self._height + 2 * NAV_PAD)
        self.bind("<Configure>", self._on_resize)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda _event: self._command())

    def set_active(self, active: bool) -> None:
        """Выделяет пункт как выбранный или снимает выделение."""
        self._active = active
        self._draw()

    def set_count(self, count: int) -> None:
        """Показывает счётчик справа (0 скрывает его)."""
        self._count = count
        self._draw()

    def _on_resize(self, event: tk.Event) -> None:
        if event.width != self._width:
            self._width = event.width
            self._draw()

    def _on_enter(self, _event: tk.Event) -> None:
        self._hover = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hover = False
        self._draw()

    def _draw(self) -> None:
        if self._width <= 2 * NAV_PAD:
            return
        pal = palette()
        self.delete("all")
        self._images = []
        body = self._width - 2 * NAV_PAD
        if self._active:
            fill, ink, style = pal.primary_soft, pal.primary_ink, "body_strong"
            shadows = (Shadow(2, 6, pal.primary, 0.18),)
        else:
            fill = mix(pal.side, pal.primary_soft, 0.5) if self._hover else None
            ink, style, shadows = pal.ink_2, "body", ()
        if fill is not None:
            box = rounded_box(
                body, self._height, NAV_RADIUS, fill, shadows=shadows, pad=NAV_PAD
            )
            self._images.append(photo(box, self))
            self.create_image(0, 0, image=self._images[-1], anchor="nw")
        middle = NAV_PAD + self._height / 2
        self.create_text(
            NAV_PAD + NAV_PADDING_X,
            middle,
            text=self._text,
            anchor="w",
            fill=ink,
            font=font_spec(style, self),
        )
        if self._count:
            self._draw_counter(middle)

    def _draw_counter(self, middle: float) -> None:
        pal = palette()
        label = str(self._count)
        width = text_width(self, label, "counter") + 2 * COUNTER_PADDING_X
        height = line_height(self, "counter") + 2 * COUNTER_PADDING_Y
        right = self._width - NAV_PAD - NAV_PADDING_X
        self._images.append(
            photo(rounded_box(width, height, theme.BADGE_RADIUS, pal.primary), self)
        )
        self.create_image(right, middle, image=self._images[-1], anchor="e")
        self.create_text(
            right - width / 2,
            middle,
            text=label,
            fill=pal.on_primary,
            font=font_spec("counter", self),
        )


class Sidebar(tk.Frame):
    """Левая панель: название, разделы, пользователь и кнопка выхода."""

    def __init__(
        self,
        master: tk.Misc,
        user: User,
        sections: Sequence[str],
        on_select: Callable[[str], None],
        on_logout: Callable[[], None],
        on_toggle_theme: Callable[[], None],
    ) -> None:
        """Создаёт меню.

        Args:
            master: Родительский виджет.
            user: Вошедший пользователь (имя и логин внизу).
            sections: Названия разделов сверху вниз.
            on_select: Вызывается с названием раздела при нажатии.
            on_logout: Вызывается при нажатии на «Выход».
            on_toggle_theme: Вызывается при нажатии на «Тёмная/Светлая тема».
        """
        pal = palette()
        self._footer_icons: list = []
        super().__init__(master, bg=pal.side, width=theme.SIDEBAR_WIDTH)
        self.pack_propagate(False)
        tk.Frame(self, bg=pal.line, width=1).pack(side="right", fill="y")
        inner = tk.Frame(self, bg=pal.side)
        inner.pack(fill="both", expand=True, padx=(14 - NAV_PAD, 14 - NAV_PAD))
        tk.Label(
            inner,
            text="Моя аптечка",
            bg=pal.side,
            fg=pal.brand_ink,
            font=font_spec("sidebar_title", self),
            padx=0,
        ).pack(anchor="w", padx=NAV_PAD + 4, pady=(22, 26))
        self._items: Dict[str, NavItem] = {}
        for name in sections:
            item = NavItem(inner, name, lambda value=name: on_select(value))
            item.pack(fill="x")
            self._items[name] = item
        self._build_footer(inner, user, on_logout, on_toggle_theme)

    def set_active(self, name: str) -> None:
        """Выделяет раздел в меню."""
        for key, item in self._items.items():
            item.set_active(key == name)

    def set_count(self, name: str, count: int) -> None:
        """Показывает счётчик у раздела."""
        self._items[name].set_count(count)

    def _build_footer(
        self,
        inner: tk.Frame,
        user: User,
        on_logout: Callable[[], None],
        on_toggle_theme: Callable[[], None],
    ) -> None:
        pal = palette()
        footer = tk.Frame(inner, bg=pal.side)
        footer.pack(side="bottom", fill="x", pady=(0, 14 - NAV_PAD))
        tk.Frame(footer, bg=pal.line, height=1).pack(fill="x", padx=NAV_PAD)
        person = tk.Frame(footer, bg=pal.side)
        person.pack(fill="x", padx=NAV_PAD + 8, pady=(14, 6))
        avatar = tk.Canvas(
            person,
            width=AVATAR_SIZE,
            height=AVATAR_SIZE,
            bd=0,
            highlightthickness=0,
            bg=pal.side,
        )
        avatar.pack(side="left")
        self._avatar = photo(
            rounded_box(AVATAR_SIZE, AVATAR_SIZE, AVATAR_SIZE // 2, pal.primary), avatar
        )
        avatar.create_image(0, 0, image=self._avatar, anchor="nw")
        avatar.create_text(
            AVATAR_SIZE / 2,
            AVATAR_SIZE / 2,
            text=user.username[:1].upper(),
            fill=pal.on_primary,
            font=font_spec("counter", self),
        )
        names = tk.Frame(person, bg=pal.side)
        names.pack(side="left", padx=(8, 0))
        tk.Label(
            names,
            text=user.username,
            bg=pal.side,
            fg=pal.ink,
            font=font_spec("user_name", self),
            padx=0,
            pady=0,
        ).pack(anchor="w")
        tk.Label(
            names,
            text=user.login,
            bg=pal.side,
            fg=pal.ink_3,
            font=font_spec("caption", self),
            padx=0,
            pady=0,
        ).pack(anchor="w")
        dark = theme.theme_name() == theme.DARK_THEME
        self._footer_link(
            footer,
            "Светлая тема" if dark else "Тёмная тема",
            "sun" if dark else "moon",
            pal.ink_2,
            on_toggle_theme,
        ).pack(fill="x", padx=NAV_PAD + 12, pady=(0, 4))
        self._footer_link(footer, "Выход", "logout", pal.red, on_logout).pack(
            fill="x", padx=NAV_PAD + 12
        )

    def _footer_link(
        self,
        footer: tk.Frame,
        text: str,
        icon: str,
        color: str,
        command: Callable[[], None],
    ) -> tk.Label:
        """Строка внизу меню: значок и подпись, нажатие вызывает команду."""
        pal = palette()
        glyph = photo(render_icon(icon, 14, color), footer)
        self._footer_icons.append(glyph)
        label = tk.Label(
            footer,
            text="  " + text,
            image=glyph,
            compound="left",
            bg=pal.side,
            fg=color,
            font=font_spec("body", self),
            cursor="hand2",
            anchor="w",
        )
        label.bind("<Button-1>", lambda _event: command())
        return label
