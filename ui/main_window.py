"""Uygulamanın temel ana penceresi."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from app.constants import APPLICATION_DISPLAY_NAME
from ui.excel_import_widget import ExcelImportWidget


class MainWindow(QMainWindow):
    """Sonraki modüllerin yerleştirileceği temel uygulama penceresi."""

    def __init__(self, database_path: Path) -> None:
        super().__init__()
        self.database_path = database_path
        self._configure_window()
        self._build_content()

    def _configure_window(self) -> None:
        self.setWindowTitle(APPLICATION_DISPLAY_NAME)
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

    def _build_content(self) -> None:
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)

        title = QLabel(APPLICATION_DISPLAY_NAME)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 600;")

        layout.addWidget(title)
        layout.addWidget(ExcelImportWidget(central_widget), 1)

        self.setCentralWidget(central_widget)
        self.statusBar().showMessage("Hazır")
