"""Кнопка из макета: обычная, главная и опасная, с иконкой и без."""

import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from pharmacy.ui import theme
from pharmacy.ui.drawing import Shadow, rounded_box
from pharmacy.ui.fonts import font_spec, text_width
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import SHADOW_PAD, mix, palette
from pharmacy.ui.widgets.common import parent_bg, photo

ICON_GAP = 6
DISABLED_SHARE = 0.55  # насколько цвета неактивной кнопки уходят в фон
HOVER_SHARE = 0.07
PRESSED_SHARE = 0.14


@dataclass(frozen=True)
class _Size:
    height: int
    padding: int
    font: str
    icon: int


SIZES = {
    "md": _Size(theme.CONTROL_HEIGHT, 16, "body_medium", 14),
    "sm": _Size(theme.CONTROL_HEIGHT_SMALL, 10, "small_medium", 13),
    "lg": _Size(theme.CONTROL_HEIGHT_LARGE, 16, "body_strong", 14),
}

VARIANTS = ("default", "primary", "danger", "danger_solid")


def _colors(variant: str) -> Tuple[str, str, str]:
    """Возвращает (заливка, граница, текст) кнопки в спокойном состоянии."""
    pal = palette()
    return {
        "default": (pal.input_bg, pal.line, pal.ink_2),
        "primary": (pal.primary, pal.primary, pal.on_primary),
        "danger": (pal.input_bg, pal.red_line, pal.red),
        "danger_solid": (pal.red, pal.red, pal.on_primary),
    }[variant]


def _shadows(variant: str) -> Tuple[Shadow, ...]:
    """Тени кнопки: у цветных кнопок тень того же цвета."""
    pal = palette()
    if variant == "primary":
        return (Shadow(3, 8, pal.primary, 0.28), Shadow(1, 2, pal.primary, 0.12))
    if variant == "danger_solid":
        return (Shadow(3, 8, pal.red, 0.28), Shadow(1, 2, pal.red, 0.12))
    return (Shadow(1, 3, pal.shadow, 0.08), Shadow(2, 6, pal.shadow, 0.05))


class Button(tk.Canvas):
    """Кнопка, нарисованная на Canvas.

    Меняет вид при наведении и нажатии, умеет быть неактивной и растягиваться
    на всю ширину (``fill="x"`` при размещении).
    """

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Optional[Callable[[], None]] = None,
        variant: str = "default",
        size: str = "md",
        icon: Optional[str] = None,
        width: Optional[int] = None,
    ) -> None:
        """Создаёт кнопку.

        Args:
            master: Родительский виджет.
            text: Подпись.
            command: Что вызвать при нажатии.
            variant: ``default``, ``primary``, ``danger`` или ``danger_solid``.
            size: ``md`` (32 px), ``sm`` (26 px) или ``lg`` (36 px).
            icon: Название иконки из ``icons.ICONS`` слева от подписи.
            width: Ширина кнопки в пикселях (по умолчанию по тексту).
        """
        super().__init__(
            master, bd=0, highlightthickness=0, bg=parent_bg(master), cursor="hand2"
        )
        if variant not in VARIANTS:
            raise ValueError(f"Неизвестный вид кнопки: {variant}")
        self._text = text
        self._command = command
        self._variant = variant
        self._size = SIZES[size]
        self._icon = icon
        self._enabled = True
        self._hover = False
        self._pressed = False
        self._images: list = []
        self._body_width = width or self._natural_width()
        self.configure(
            width=self._body_width + 2 * SHADOW_PAD,
            height=self._size.height + 2 * SHADOW_PAD,
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", self._on_resize)
        self._draw()

    @property
    def text(self) -> str:
        """Подпись кнопки."""
        return self._text

    @property
    def enabled(self) -> bool:
        """Нажимается ли кнопка."""
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Включает или выключает кнопку."""
        self._enabled = enabled
        self._hover = self._pressed = False
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def set_text(self, text: str) -> None:
        """Меняет подпись."""
        self._text = text
        self._draw()

    def invoke(self) -> None:
        """Нажимает кнопку программно."""
        if self._enabled and self._command is not None:
            self._command()

    def _natural_width(self) -> int:
        """Ширина по тексту и иконке."""
        width = text_width(self, self._text, self._size.font)
        if self._icon:
            width += self._size.icon + ICON_GAP
        return width + 2 * self._size.padding

    def _state_colors(self) -> Tuple[str, str, str]:
        """Цвета с учётом наведения, нажатия и недоступности."""
        fill, border, ink = _colors(self._variant)
        if not self._enabled:
            bg = parent_bg(self)
            return tuple(mix(c, bg, DISABLED_SHARE) for c in (fill, border, ink))
        if self._pressed or self._hover:
            share = PRESSED_SHARE if self._pressed else HOVER_SHARE
            tint = (
                "#000000"
                if self._variant in ("primary", "danger_solid")
                else palette().primary
            )
            fill = mix(fill, tint, share)
        return fill, border, ink

    def _draw(self) -> None:
        """Перерисовывает кнопку целиком."""
        self.delete("all")
        self._images.clear()
        fill, border, ink = self._state_colors()
        shadows = _shadows(self._variant) if self._enabled else ()
        box = rounded_box(
            self._body_width,
            self._size.height,
            theme.CONTROL_RADIUS,
            fill,
            border,
            shadows=shadows,
            pad=SHADOW_PAD,
        )
        self._images.append(photo(box, self))
        self.create_image(0, 0, image=self._images[-1], anchor="nw")

        center_y = SHADOW_PAD + self._size.height / 2
        content = text_width(self, self._text, self._size.font)
        left = SHADOW_PAD + (self._body_width - content) / 2
        if self._icon:
            content += self._size.icon + ICON_GAP
            left = SHADOW_PAD + (self._body_width - content) / 2
            glyph = render_icon(self._icon, self._size.icon, ink)
            self._images.append(photo(glyph, self))
            self.create_image(left, center_y, image=self._images[-1], anchor="w")
            left += self._size.icon + ICON_GAP
        self.create_text(
            left,
            center_y,
            text=self._text,
            anchor="w",
            fill=ink,
            font=font_spec(self._size.font, self),
        )

    def _on_resize(self, event: tk.Event) -> None:
        """Подгоняет кнопку под ширину, выданную менеджером размещения."""
        width = event.width - 2 * SHADOW_PAD
        if width != self._body_width and width > 0:
            self._body_width = width
            self._draw()

    def _on_enter(self, _event: tk.Event) -> None:
        if self._enabled:
            self._hover = True
            self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hover = self._pressed = False
        if self._enabled:
            self._draw()

    def _on_press(self, _event: tk.Event) -> None:
        if self._enabled:
            self._pressed = True
            self._draw()

    def _on_release(self, event: tk.Event) -> None:
        if not (self._enabled and self._pressed):
            return
        self._pressed = False
        self._draw()
        inside = (
            0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        )
        if inside and self._command is not None:
            self._command()
