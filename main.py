#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代書 (Daisho) - High-Precision Japanese OCR Desktop Application

A PyQt6-based application for capturing and recognizing Japanese text
from screen regions using manga-ocr or PaddleOCR engines.

Features:
- Transparent, resizable capture overlay
- Multiple OCR engines (manga-ocr, PaddleOCR)
- Advanced image preprocessing options
- Global hotkey support
- Macro recording for workflow automation
- GPU acceleration support

Usage:
    python main_new.py

Requirements:
    - Python 3.10+
    - PyQt6
    - manga-ocr or paddleocr
    - opencv-python-headless (optional, for advanced preprocessing)
    - keyboard (for global hotkeys)
    - mouse (for macro recording)
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# IMPORTANT: Set High DPI policy BEFORE importing/creating QApplication
# This must happen before any Qt imports
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"


def check_dependencies() -> list[str]:
    """Check for missing required dependencies."""
    missing = []

    # Required packages
    required = [
        ("PyQt6", "PyQt6"),
        ("PIL", "Pillow"),
        ("manga_ocr", "manga-ocr"),
    ]

    for import_name, package_name in required:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)

    return missing


def show_dependency_error(missing: list[str]) -> None:
    """Show error dialog for missing dependencies."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Missing Dependencies",
            f"The following packages are required but not installed:\n\n"
            f"{chr(10).join('- ' + p for p in missing)}\n\n"
            f"Please install them with:\n"
            f"pip install {' '.join(missing)}"
        )
        sys.exit(1)
    except ImportError:
        # PyQt6 itself is missing, print to console
        print("ERROR: Missing required dependencies:")
        for package in missing:
            print(f"  - {package}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        sys.exit(1)


def main() -> int:
    """Main entry point."""
    # Set up logging first
    from src.utils.logger import setup_logger, log_info, log_error, log_exception, log_system_info

    logger = setup_logger()
    log_info("Application starting...")

    # Log system diagnostics for debugging
    log_system_info()

    # Check dependencies
    missing = check_dependencies()
    if missing:
        log_error(f"Missing dependencies: {missing}")
        show_dependency_error(missing)
        return 1

    log_info("All dependencies found")

    try:
        # Import Qt modules
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt

        # Set high DPI policy BEFORE creating QApplication
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("代書")
        app.setOrganizationName("Daisho")

        log_info("QApplication created")

        # Import and create main window
        from src.gui.main_window import MainWindow

        window = MainWindow()
        log_info("MainWindow created")

        # Show or minimize based on settings
        if window._settings.get("start_minimized", True):
            log_info("Starting minimized to system tray")
            print("Starting minimized to system tray")
            print("Double-click tray icon or use menu to show overlay")
        else:
            window.show()
            log_info("Main window shown")

        # Run event loop
        log_info("Entering main event loop")
        result = app.exec()
        log_info(f"Application exiting with code {result}")
        return result

    except Exception as e:
        log_exception(e, "main()")
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
