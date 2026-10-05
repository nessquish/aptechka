"""Модальное окно поверх затемнённого окна приложения."""

import tkinter as tk
from typing import Callable, Optional

from PIL import Image, ImageGrab

from pharmacy.ui import theme
from pharmacy.ui.drawing import rgba, rounded_box
from pharmacy.ui.fonts import font_spec
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import mix, palette
from pharmacy.ui.widgets.button import Button
from pharmacy.ui.widgets.card import Card
from pharmacy.ui.widgets.common import photo

SCRIM_OPACITY = 0.42
PADDING = 24
WARN_SIZE = 42


def _scrim_image(host: tk.Misc, width: int, height: int) -> Optional[Image.Image]:
    """Снимок окна, затемнённый цветом подложки (None, если снять нельзя)."""
    try:
        shot = ImageGrab.grab(
            bbox=(
                host.winfo_rootx(),
                host.winfo_rooty(),
                host.winfo_rootx() + width,
                host.winfo_rooty() + height,
            )
        ).convert("RGBA")
    except OSError:
        return None
    shade = Image.new("RGBA", shot.size, rgba(palette().overlay, SCRIM_OPACITY))
    return Image.alpha_composite(shot, shade)


class Dialog:
    """Окно с заголовком, текстом и кнопками «Отмена» и подтверждения.

    Закрывается по «Отмена», по подтверждению и по клавише Esc. Enter
    подтверждает действие. Пока окно открыто, остальной интерфейс закрыт
    затемнением и не реагирует на нажатия.
    """

    def __init__(
        self,
        host: tk.Misc,
        title: str,
        message: str,
        confirm_text: str,
        on_confirm: Callable[[], None],
        confirm_variant: str = "primary",
        cancel_text: str = "Отмена",
        warning: bool = False,
        width: int = 400,
    ) -> None:
        """Показывает окно.

        Args:
            host: Окно или экран, поверх которого открывается диалог.
            title: Заголовок.
            message: Пояснение.
            confirm_text: Подпись кнопки подтверждения.
            on_confirm: Что сделать после подтверждения (окно закроется само).
            confirm_variant: Вид кнопки подтверждения (``primary``, ``danger_solid``).
            cancel_text: Подпись кнопки отмены.
            warning: Показать красный значок восклицания над заголовком.
            width: Ширина окна.
        """
        host.update_idletasks()
        pal = palette()
        self._host = host
        self._on_confirm = on_confirm
        self._images: list = []
        shot = _scrim_image(host, host.winfo_width(), host.winfo_height())
        self._scrim = tk.Canvas(
            host,
            bd=0,
            highlightthickness=0,
            bg=mix(pal.bg, pal.overlay, SCRIM_OPACITY),
        )
        if shot is not None:
            self._images.append(photo(shot, self._scrim))
            self._scrim.create_image(0, 0, image=self._images[-1], anchor="nw")
        self._scrim.place(x=0, y=0, relwidth=1, relheight=1)
        self._scrim.bind("<Button-1>", lambda _event: "break")

        self._card = Card(host, radius=theme.MODAL_RADIUS, elevated=True, backdrop=shot)
        self._card.place(relx=0.5, rely=0.5, anchor="center")
        body = tk.Frame(self._card.body, bg=pal.card, padx=PADDING, pady=PADDING)
        body.pack()
        tk.Frame(body, bg=pal.card, width=width - 2 * PADDING, height=1).pack()
        if warning:
            self._build_warning(body)
        tk.Label(
            body,
            text=title,
            bg=pal.card,
            fg=pal.ink,
            font=font_spec("modal_title", host),
            padx=0,
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            body,
            text=message,
            bg=pal.card,
            fg=pal.ink_2,
            font=font_spec("body", host),
            justify="left",
            anchor="w",
            wraplength=width - 2 * PADDING,
            padx=0,
        ).pack(anchor="w", fill="x")
        buttons = tk.Frame(body, bg=pal.card)
        buttons.pack(anchor="e", pady=(16, 0))
        Button(buttons, cancel_text, command=self.close).pack(side="left", padx=(0, 4))
        Button(
            buttons, confirm_text, command=self._confirm, variant=confirm_variant
        ).pack(side="left")

        self._card.focus_set()
        toplevel = host.winfo_toplevel()
        self._bindings = [
            (sequence, toplevel.bind(sequence, lambda _event, c=call: c(), add="+"))
            for sequence, call in (
                ("<Escape>", self.close),
                ("<Return>", self._confirm),
            )
        ]

    def _build_warning(self, body: tk.Frame) -> None:
        """Рисует красный круг с восклицательным знаком над заголовком."""
        pal = palette()
        canvas = tk.Canvas(
            body,
            width=WARN_SIZE,
            height=WARN_SIZE,
            bd=0,
            highlightthickness=0,
            bg=pal.card,
        )
        canvas.pack(anchor="w", pady=(0, 14))
        self._images.append(
            photo(rounded_box(WARN_SIZE, WARN_SIZE, WARN_SIZE // 2, pal.red_bg), canvas)
        )
        self._images.append(photo(render_icon("alert", 20, pal.red), canvas))
        canvas.create_image(0, 0, image=self._images[-2], anchor="nw")
        canvas.create_image(
            WARN_SIZE / 2, WARN_SIZE / 2, image=self._images[-1], anchor="center"
        )

    def _confirm(self) -> None:
        self.close()
        self._on_confirm()

    def close(self) -> None:
        """Закрывает окно и снимает затемнение."""
        if not self._card.winfo_exists():
            return
        toplevel = self._host.winfo_toplevel()
        for sequence, binding_id in self._bindings:
            toplevel.unbind(sequence, binding_id)
        self._card.destroy()
        self._scrim.destroy()
