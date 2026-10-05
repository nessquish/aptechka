"""Поле ввода из макета: подпись, рамка, подсказка и сообщение об ошибке."""

import tkinter as tk
from typing import Callable, Optional

from pharmacy.ui import theme
from pharmacy.ui.drawing import Shadow, rounded_box
from pharmacy.ui.fonts import font_spec
from pharmacy.ui.icons import render_icon
from pharmacy.ui.theme import SHADOW_PAD, palette
from pharmacy.ui.widgets.common import parent_bg, photo

RING_PAD = SHADOW_PAD  # поле вокруг рамки: помещается кольцо ошибки и тень
RING_WIDTH = 3  # толщина красного кольца вокруг поля с ошибкой
TEXT_INSET = 10
ICON_SIZE = 16
ICON_INSET = 10
MASK_CHAR = "•"


class TextField(tk.Frame):
    """Однострочное поле с подписью.

    Умеет показывать подсказку в пустом поле, скрывать пароль с кнопкой
    «глаз», показывать значок справа и красную рамку с текстом ошибки.
    """

    def __init__(
        self,
        master: tk.Misc,
        label: str,
        placeholder: str = "",
        required: bool = False,
        password: bool = False,
        trailing_icon: Optional[str] = None,
    ) -> None:
        """Создаёт поле.

        Args:
            master: Родительский виджет.
            label: Подпись над полем.
            placeholder: Серая подсказка в пустом поле.
            required: Добавить красную звёздочку к подписи.
            password: Скрывать вводимые символы.
            trailing_icon: Значок справа (для паролей кнопка «глаз» ставится сама).
        """
        super().__init__(master, bg=parent_bg(master))
        pal = palette()
        self._placeholder = placeholder
        self._password = password
        self._revealed = False
        self._placeholder_on = False
        self._focused = False
        self._error: Optional[str] = None
        self._width = 0
        self._icon = "eye" if password else trailing_icon
        self._images: list = []

        self._build_label(label, required)
        self._canvas = tk.Canvas(
            self,
            bd=0,
            highlightthickness=0,
            bg=self.cget("bg"),
            height=theme.CONTROL_HEIGHT + 2 * RING_PAD,
        )
        self._canvas.pack(fill="x")
        self._entry = tk.Entry(
            self._canvas,
            bd=0,
            highlightthickness=0,
            relief="flat",
            bg=pal.input_bg,
            fg=pal.ink,
            insertbackground=pal.ink,
            selectbackground=pal.primary_soft,
            selectforeground=pal.ink,
            font=font_spec("body", self),
            show=self._mask(),
        )
        self._entry_window = self._canvas.create_window(
            0, 0, window=self._entry, anchor="w"
        )
        self._error_label = tk.Label(
            self,
            bg=self.cget("bg"),
            fg=pal.red,
            font=font_spec("caption", self),
            anchor="w",
            justify="left",
            padx=0,
        )

        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<ButtonPress-1>", self._on_canvas_click)
        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Key>", self._on_key, add="+")
        if placeholder:
            self._show_placeholder()

    def _build_label(self, text: str, required: bool) -> None:
        """Строит строку подписи над полем."""
        pal = palette()
        row = tk.Frame(self, bg=self.cget("bg"))
        row.pack(fill="x", padx=RING_PAD, pady=(0, 5 - RING_PAD))
        tk.Label(
            row,
            text=text,
            bg=row.cget("bg"),
            fg=pal.ink_2,
            font=font_spec("label", self),
            padx=0,
        ).pack(side="left")
        if required:
            tk.Label(
                row,
                text=" *",
                bg=row.cget("bg"),
                fg=pal.red,
                font=font_spec("label", self),
                padx=0,
            ).pack(side="left")

    # --- публичный интерфейс ---

    @property
    def entry(self) -> tk.Entry:
        """Внутренний виджет ввода (для привязки событий и порядка фокуса)."""
        return self._entry

    def get(self) -> str:
        """Возвращает введённый текст (без подсказки)."""
        return "" if self._placeholder_on else self._entry.get()

    def set(self, value: str) -> None:
        """Записывает текст в поле."""
        self._hide_placeholder()
        self._entry.delete(0, "end")
        self._entry.insert(0, value)
        if not value and not self._focused:
            self._show_placeholder()

    def focus_field(self) -> None:
        """Переводит фокус в поле."""
        self._entry.focus_set()

    def bind_submit(self, command: Callable[[], None]) -> None:
        """Вызывает команду по нажатию Enter в поле."""
        self._entry.bind("<Return>", lambda _event: command())

    def set_error(self, message: str = "") -> None:
        """Подсвечивает поле красным и показывает сообщение под ним.

        Args:
            message: Текст ошибки. Если пустой, поле только краснеет
                (сообщение показано в другом месте, например над формой).
        """
        self._error = message
        self._error_label.configure(text=message)
        if message:
            self._error_label.pack(fill="x", padx=RING_PAD, pady=(4 - RING_PAD, 0))
        else:
            self._error_label.pack_forget()
        self._draw()

    def clear_error(self) -> None:
        """Убирает подсветку ошибки."""
        if self._error is None:
            return
        self._error = None
        self._error_label.pack_forget()
        self._draw()

    @property
    def error(self) -> Optional[str]:
        """Текст ошибки или None."""
        return self._error

    # --- подсказка и пароль ---

    def _mask(self) -> str:
        """Символ, которым заменяются вводимые знаки."""
        return MASK_CHAR if self._password and not self._revealed else ""

    def _show_placeholder(self) -> None:
        self._entry.delete(0, "end")
        self._entry.insert(0, self._placeholder)
        self._entry.configure(fg=palette().ink_3, show="")
        self._placeholder_on = True

    def _hide_placeholder(self) -> None:
        if not self._placeholder_on:
            return
        self._entry.delete(0, "end")
        self._entry.configure(fg=palette().ink, show=self._mask())
        self._placeholder_on = False

    def _toggle_reveal(self) -> None:
        self._revealed = not self._revealed
        if not self._placeholder_on:
            self._entry.configure(show=self._mask())
        self._draw()

    # --- события ---

    def _on_focus_in(self, _event: tk.Event) -> None:
        self._focused = True
        self._hide_placeholder()
        self._draw()

    def _on_focus_out(self, _event: tk.Event) -> None:
        self._focused = False
        if self._placeholder and not self._entry.get():
            self._show_placeholder()
        self._draw()

    def _on_key(self, event: tk.Event) -> None:
        if event.keysym not in ("Tab", "Return", "Shift_L", "Shift_R"):
            self.clear_error()

    def _on_resize(self, event: tk.Event) -> None:
        if event.width != self._width:
            self._width = event.width
            self._draw()

    def _on_canvas_click(self, event: tk.Event) -> None:
        if self._icon_hit(event.x) and self._password:
            self._toggle_reveal()
        else:
            self._entry.focus_set()

    def _icon_hit(self, x: int) -> bool:
        return (
            self._icon is not None
            and x >= self._width - RING_PAD - ICON_SIZE - 2 * ICON_INSET
        )

    # --- рисование ---

    def _draw(self) -> None:
        """Рисует рамку, значок и подгоняет положение текста."""
        if self._width <= 0:
            return
        pal = palette()
        if self._error is not None:
            border, ring = pal.red, pal.red_ring
        elif self._focused:
            border, ring = pal.primary, None
        else:
            border, ring = pal.input_line, None
        box = rounded_box(
            self._width - 2 * RING_PAD,
            theme.CONTROL_HEIGHT,
            theme.CONTROL_RADIUS,
            pal.input_bg,
            border,
            shadows=(Shadow(1, 2, pal.shadow, 0.05),),
            pad=RING_PAD,
            ring=ring,
            ring_width=RING_WIDTH,
        )
        self._images = [photo(box, self)]
        self._canvas.delete("decor")
        self._canvas.create_image(
            0, 0, image=self._images[0], anchor="nw", tags="decor"
        )
        self._canvas.tag_lower("decor")

        middle = RING_PAD + theme.CONTROL_HEIGHT / 2
        right_edge = self._width - RING_PAD - TEXT_INSET
        if self._icon is not None:
            name = self._icon
            if self._password and self._revealed:
                name = "eye-off"
            self._images.append(photo(render_icon(name, ICON_SIZE, pal.ink_3), self))
            self._canvas.create_image(
                self._width - RING_PAD - ICON_INSET,
                middle,
                image=self._images[1],
                anchor="e",
                tags="decor",
            )
            right_edge -= ICON_SIZE + ICON_INSET - TEXT_INSET
        self._canvas.coords(self._entry_window, RING_PAD + TEXT_INSET, middle)
        self._canvas.itemconfigure(
            self._entry_window, width=max(right_edge - RING_PAD - TEXT_INSET, 1)
        )
