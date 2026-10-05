"""Поля из макета: подпись, рамка, подсказка и сообщение об ошибке.

``LabeledBox`` рисует рамку с подписью и ошибкой, а ``TextField`` добавляет
к ней ввод текста. Выпадающий список (``select.Select``) строится на той же
основе, поэтому выглядит так же.
"""

import tkinter as tk
from typing import Callable, Optional, Tuple

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
# Коды клавиш Windows для Ctrl+сочетаний: не зависят от раскладки.
_SHORTCUT_KEYCODES = {67: "Copy", 86: "Paste", 88: "Cut", 65: "select_all"}
AREA_HEIGHT = 54  # высота многострочного поля
AREA_PADDING_TOP = 9


class LabeledBox(tk.Frame):
    """Рамка поля с подписью сверху и сообщением об ошибке снизу.

    Рисует рамку (обычную, в фокусе или с ошибкой). Что лежит внутри рамки,
    решают наследники: они переопределяют ``_place_content``.
    """

    def __init__(
        self,
        master: tk.Misc,
        label: Optional[str] = None,
        required: bool = False,
        height: int = theme.CONTROL_HEIGHT,
        compact: bool = False,
        width: Optional[int] = None,
    ) -> None:
        """Создаёт рамку.

        Args:
            master: Родительский виджет.
            label: Подпись над полем (None, если подписи нет).
            required: Добавить красную звёздочку к подписи.
            height: Высота рамки без полей под тень.
            compact: Вид фильтра на панели: граница цвета карточек.
            width: Ширина рамки. Если не задана, поле занимает всю ширину,
                которую даёт родитель.
        """
        super().__init__(master, bg=parent_bg(master))
        pal = palette()
        self._box_height = height
        self._border = pal.line if compact else pal.input_line
        self._focused = False
        self._error: Optional[str] = None
        self._width = 0
        self._images: list = []
        if label is not None:
            self._build_label(label, required)
        self._canvas = tk.Canvas(
            self,
            bd=0,
            highlightthickness=0,
            bg=self.cget("bg"),
            width=1,  # реальную ширину даёт родитель (по умолчанию у Canvas 378 px)
            height=height + 2 * RING_PAD,
        )
        self._canvas.pack(fill="x")
        if width is not None:
            self.set_width(width)
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

    def set_width(self, width: int) -> None:
        """Фиксирует ширину рамки (без полей под тень)."""
        self._canvas.configure(width=width + 2 * RING_PAD)
        self._canvas.pack_configure(fill="none", anchor="w")

    # --- ошибка ---

    @property
    def error(self) -> Optional[str]:
        """Текст ошибки или None."""
        return self._error

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

    # --- рисование ---

    def _colors(self) -> Tuple[str, Optional[str]]:
        """Цвет границы и кольца для текущего состояния."""
        pal = palette()
        if self._error is not None:
            return pal.red, pal.red_ring
        if self._focused:
            return pal.primary, None
        return self._border, None

    def _on_resize(self, event: tk.Event) -> None:
        if event.width != self._width:
            self._width = event.width
            self._draw()

    def _draw(self) -> None:
        """Рисует рамку и просит наследника разместить содержимое."""
        if self._width <= 2 * RING_PAD:
            return
        pal = palette()
        border, ring = self._colors()
        box = rounded_box(
            self._width - 2 * RING_PAD,
            self._box_height,
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
        self._place_content()

    def _draw_icon(self, name: str, x: float, anchor: str) -> None:
        """Рисует значок внутри рамки на уровне середины."""
        glyph = photo(render_icon(name, ICON_SIZE, palette().ink_3), self)
        self._images.append(glyph)
        self._canvas.create_image(
            x,
            RING_PAD + self._box_height / 2,
            image=glyph,
            anchor=anchor,
            tags="decor",
        )

    def _place_content(self) -> None:
        """Размещает содержимое рамки (переопределяется)."""


class TextField(LabeledBox):
    """Поле ввода текста.

    Умеет показывать подсказку в пустом поле, скрывать пароль с кнопкой
    «глаз», показывать значки слева и справа, быть многострочным и
    только для чтения.
    """

    def __init__(
        self,
        master: tk.Misc,
        label: Optional[str] = None,
        placeholder: str = "",
        required: bool = False,
        password: bool = False,
        trailing_icon: Optional[str] = None,
        leading_icon: Optional[str] = None,
        multiline: bool = False,
        readonly: bool = False,
        compact: bool = False,
        on_change: Optional[Callable[[], None]] = None,
        width: Optional[int] = None,
        justify: str = "left",
    ) -> None:
        """Создаёт поле.

        Args:
            master: Родительский виджет.
            label: Подпись над полем.
            placeholder: Серая подсказка в пустом поле.
            required: Добавить красную звёздочку к подписи.
            password: Скрывать вводимые символы.
            trailing_icon: Значок справа (для паролей кнопка «глаз» ставится сама).
            leading_icon: Значок слева (например, лупа в поиске).
            multiline: Многострочное поле высотой в несколько строк.
            readonly: Только чтение: текст нельзя изменить.
            compact: Вид поля на панели фильтров.
            on_change: Вызывается после каждого изменения текста пользователем.
            width: Ширина поля (по умолчанию на всю ширину родителя).
            justify: Выравнивание текста в однострочном поле: ``left`` или ``center``.
        """
        super().__init__(
            master,
            label,
            required,
            height=AREA_HEIGHT if multiline else theme.CONTROL_HEIGHT,
            compact=compact,
            width=width,
        )
        pal = palette()
        self._placeholder = placeholder
        self._password = password
        self._multiline = multiline
        self._readonly = readonly
        self._on_change = on_change
        self._revealed = False
        self._placeholder_on = False
        self._leading = leading_icon
        self._trailing = "eye" if password else trailing_icon
        options = dict(
            bd=0,
            highlightthickness=0,
            relief="flat",
            bg=pal.input_bg,
            fg=pal.ink_3 if readonly else pal.ink,
            insertbackground=pal.ink,
            selectbackground=pal.primary_soft,
            selectforeground=pal.ink,
            font=font_spec("body", self),
        )
        if multiline:
            self._entry = tk.Text(self._canvas, wrap="word", **options)
        else:
            self._entry = tk.Entry(
                self._canvas, show=self._mask(), justify=justify, **options
            )
        self._entry_window = self._canvas.create_window(
            0, 0, window=self._entry, anchor="nw" if multiline else "w"
        )
        if readonly:
            self._entry.configure(state="disabled" if multiline else "readonly")
            if not multiline:
                self._entry.configure(readonlybackground=pal.input_bg)

        self._canvas.bind("<ButtonPress-1>", self._on_canvas_click)
        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Key>", self._on_key, add="+")
        self._entry.bind("<KeyRelease>", self._notify, add="+")
        self._entry.bind("<<Paste>>", self._notify, add="+")
        self._entry.bind("<<Cut>>", self._notify, add="+")
        self._entry.bind("<<Copy>>", self._on_copy, add="+")
        self._entry.bind("<<Cut>>", self._on_cut, add="+")
        self._entry.bind("<Control-KeyPress>", self._on_shortcut)
        self._entry.bind("<Button-3>", self._show_menu)
        if placeholder:
            self._show_placeholder()

    # --- текст ---

    @property
    def entry(self) -> tk.Misc:
        """Внутренний виджет ввода (для привязки событий и порядка фокуса)."""
        return self._entry

    def _read(self) -> str:
        if self._multiline:
            return self._entry.get("1.0", "end-1c")
        return self._entry.get()

    def _write(self, text: str) -> None:
        """Заменяет текст виджета (даже у поля только для чтения)."""
        locked = self._readonly
        if locked:
            self._entry.configure(state="normal")
        if self._multiline:
            self._entry.delete("1.0", "end")
            self._entry.insert("1.0", text)
        else:
            self._entry.delete(0, "end")
            self._entry.insert(0, text)
        if locked:
            self._entry.configure(state="disabled" if self._multiline else "readonly")

    def get(self) -> str:
        """Возвращает введённый текст (без подсказки)."""
        return "" if self._placeholder_on else self._read()

    def set(self, value: str) -> None:
        """Записывает текст в поле."""
        self._placeholder_on = False
        self._entry.configure(fg=self._text_color(), **self._show_option())
        self._write(value)
        if not value and not self._focused and self._placeholder:
            self._show_placeholder()

    def focus_field(self) -> None:
        """Переводит фокус в поле."""
        self._entry.focus_set()

    def bind_submit(self, command: Callable[[], None]) -> None:
        """Вызывает команду по нажатию Enter в однострочном поле."""
        if not self._multiline:
            self._entry.bind("<Return>", lambda _event: command())

    # --- подсказка и пароль ---

    def _text_color(self) -> str:
        pal = palette()
        return pal.ink_3 if self._readonly else pal.ink

    def _mask(self) -> str:
        """Символ, которым заменяются вводимые знаки."""
        return MASK_CHAR if self._password and not self._revealed else ""

    def _show_option(self) -> dict:
        """Параметр показа символов (есть только у однострочного поля)."""
        return {} if self._multiline else {"show": self._mask()}

    def _show_placeholder(self) -> None:
        self._write(self._placeholder)
        options = {} if self._multiline else {"show": ""}
        self._entry.configure(fg=palette().ink_3, **options)
        self._placeholder_on = True

    def _hide_placeholder(self) -> None:
        if not self._placeholder_on:
            return
        self._write("")
        self._entry.configure(fg=self._text_color(), **self._show_option())
        self._placeholder_on = False

    def _toggle_reveal(self) -> None:
        self._revealed = not self._revealed
        if not self._placeholder_on:
            self._entry.configure(show=self._mask())
        self._draw()

    # --- события ---

    def _notify(self, _event: Optional[tk.Event] = None) -> None:
        """Сообщает об изменении текста после того, как Tk закончил вставку."""
        if self._on_change is not None:
            self.after_idle(self._fire_change)

    def _fire_change(self) -> None:
        if self.winfo_exists() and not self._placeholder_on:
            self._on_change()

    def _on_shortcut(self, event: tk.Event) -> Optional[str]:
        """Работают ли Ctrl+C, V, X и A на любой раскладке клавиатуры.

        Tk определяет сочетание по букве, а на русской раскладке вместо «v»
        приходит «м», и вставка не срабатывает. Поэтому для не латинских букв
        сочетание определяется по коду клавиши.
        """
        if event.keysym.lower() in ("c", "v", "x", "a"):
            return None  # латинская раскладка: Tk справится сам
        action = _SHORTCUT_KEYCODES.get(event.keycode)
        if action is None:
            return None
        if action == "select_all":
            self._select_all()
        else:
            self._entry.event_generate(f"<<{action}>>")
        return "break"

    def _is_masked(self) -> bool:
        """Скрыт ли сейчас введённый текст точками."""
        return self._password and not self._revealed and not self._placeholder_on

    def _selected_text(self) -> str:
        """Настоящий выделенный текст (а не точки, которые видны на экране)."""
        if not self._entry.selection_present():
            return ""
        first = self._entry.index("sel.first")
        last = self._entry.index("sel.last")
        return self._entry.get()[first:last]

    def _on_copy(self, _event: tk.Event) -> Optional[str]:
        """Копирует настоящий текст скрытого поля, а не точки.

        Tk копирует то, что видно на экране, поэтому из поля пароля в буфер
        попадали бы точки. Для остальных полей остаётся обычное копирование.
        """
        if not self._is_masked():
            return None
        text = self._selected_text()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
        return "break"

    def _on_cut(self, event: tk.Event) -> Optional[str]:
        """Вырезает настоящий текст скрытого поля."""
        if not self._is_masked():
            return None
        text = self._selected_text()
        if text and not self._readonly:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._entry.delete("sel.first", "sel.last")
            self._notify()
        return "break"

    def _show_menu(self, event: tk.Event) -> None:
        """Контекстное меню по правой кнопке мыши."""
        self._entry.focus_set()
        menu = tk.Menu(self._entry, tearoff=0)
        editable = not self._readonly
        menu.add_command(
            label="Вырезать",
            command=lambda: self._entry.event_generate("<<Cut>>"),
            state="normal" if editable else "disabled",
        )
        menu.add_command(
            label="Копировать", command=lambda: self._entry.event_generate("<<Copy>>")
        )
        menu.add_command(
            label="Вставить",
            command=lambda: self._entry.event_generate("<<Paste>>"),
            state="normal" if editable else "disabled",
        )
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=self._select_all)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _select_all(self) -> None:
        if self._multiline:
            self._entry.tag_add("sel", "1.0", "end-1c")
        else:
            self._entry.selection_range(0, "end")

    def _on_focus_in(self, _event: tk.Event) -> None:
        self._focused = True
        self._hide_placeholder()
        self._draw()

    def _on_focus_out(self, _event: tk.Event) -> None:
        self._focused = False
        if self._placeholder and not self._read():
            self._show_placeholder()
        self._draw()

    def _on_key(self, event: tk.Event) -> None:
        if event.keysym not in ("Tab", "Return", "Shift_L", "Shift_R"):
            self.clear_error()

    def _on_canvas_click(self, event: tk.Event) -> None:
        if self._trailing and self._password and self._icon_hit(event.x):
            self._toggle_reveal()
        else:
            self._entry.focus_set()

    def _icon_hit(self, x: int) -> bool:
        return x >= self._width - RING_PAD - ICON_SIZE - 2 * ICON_INSET

    # --- размещение ---

    def _place_content(self) -> None:
        """Размещает текст и значки внутри рамки."""
        left = RING_PAD + TEXT_INSET
        right = self._width - RING_PAD - TEXT_INSET
        middle = RING_PAD + self._box_height / 2
        if self._leading:
            self._draw_icon(self._leading, left, "w")
            left += ICON_SIZE + 8
        if self._trailing:
            name = "eye-off" if self._password and self._revealed else self._trailing
            self._draw_icon(name, self._width - RING_PAD - ICON_INSET, "e")
            right -= ICON_SIZE + ICON_INSET - TEXT_INSET
        width = max(right - left, 1)
        if self._multiline:
            self._canvas.coords(self._entry_window, left, RING_PAD + AREA_PADDING_TOP)
            self._canvas.itemconfigure(
                self._entry_window,
                width=width,
                height=self._box_height - 2 * AREA_PADDING_TOP,
            )
        else:
            self._canvas.coords(self._entry_window, left, middle)
            self._canvas.itemconfigure(self._entry_window, width=width)
