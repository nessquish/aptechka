"""Точка входа для сборки .exe (PyInstaller запускает этот файл)."""

from pharmacy.crashlog import run_with_report
from pharmacy.ui.app import run

if __name__ == "__main__":
    run_with_report(run)
