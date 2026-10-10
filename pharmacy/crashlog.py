"""Журнал аварий: если программа упала, ошибка записывается в файл и показывается.

У собранной программы (``.exe``) нет консоли, поэтому без журнала при ошибке
окно просто исчезало бы и причину нельзя было бы узнать.
"""

import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from pharmacy.config import get_db_path

LOG_NAME = "error.log"


def log_path() -> Path:
    """Возвращает путь к журналу ошибок (рядом с базой данных)."""
    return get_db_path().parent / LOG_NAME


def write_report(error: BaseException, path: Optional[Path] = None) -> Path:
    """Дописывает описание ошибки в журнал и возвращает путь к нему."""
    path = path or log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = "".join(traceback.format_exception(error))
    with path.open("a", encoding="utf-8") as file:
        file.write(f"--- {stamp} ---\n{text}\n")
    return path


def show_message(path: Path, error: BaseException) -> None:
    """Показывает окно с сообщением об ошибке (если удаётся создать окно)."""
    try:
        from PySide6.QtWidgets import QMessageBox

        from pharmacy.ui.runtime import application

        application()
        QMessageBox.critical(
            None,
            "Моя аптечка",
            f"Программа остановилась из-за ошибки:\n{error}\n\n"
            f"Подробности записаны в файл:\n{path}",
        )
    except Exception:  # noqa: BLE001 - окно показать не удалось, журнал уже записан
        pass


def run_with_report(function: Callable[[], None]) -> None:
    """Запускает программу и при ошибке пишет журнал и показывает сообщение."""
    try:
        function()
    except Exception as error:  # noqa: BLE001 - нужно поймать любую ошибку запуска
        path = write_report(error)
        show_message(path, error)
        raise SystemExit(1) from error
