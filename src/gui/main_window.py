"""
Main Window - Primary application window with results display.

Provides the main interface for viewing OCR results, accessing
settings, and controlling the overlay.
"""

from __future__ import annotations
import json
import os
import threading
from typing import Optional
from PIL import Image
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QStatusBar,
    QSystemTrayIcon, QMenu, QGroupBox, QComboBox,
    QMessageBox, QToolTip, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QMetaObject, Q_ARG, Qt as QtCore
from PyQt6.QtGui import QIcon, QAction, QPixmap, QCursor, QFont, QColor

from .overlay import CaptureWindow
from ..core.ocr_manager import get_ocr_manager, OCREngine, get_engine_name, get_engine_description
from ..core.macro_system import get_macro_manager, MacroState
from ..utils.image_ops import PreprocessingMode, preprocess_image, mode_description
from ..utils.clipboard import copy_text
from ..utils.logger import get_logger, log_info, log_error, log_warning, log_debug, log_exception


class MainWindow(QMainWindow):
    """
    Main application window.

    Displays OCR results, controls the capture overlay,
    and provides access to settings.
    """

    # Signals for thread-safe GUI updates
    ocrCompleted = pyqtSignal(str)
    ocrError = pyqtSignal(str)
    triggerCapture = pyqtSignal()  # Signal to trigger capture from hotkey thread

    def __init__(self) -> None:
        super().__init__()
        log_debug("MainWindow.__init__ starting")

        # State
        self._settings = self._get_default_settings()
        self._overlay: Optional[CaptureWindow] = None
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._hotkey_registered = False
        self._statusbar: Optional[QStatusBar] = None  # Initialize early to avoid AttributeError

        # Components
        self._ocr_manager = get_ocr_manager()
        self._macro_manager = get_macro_manager()

        # Load settings first
        self._load_settings()
        log_debug("Settings loaded")

        # Set up UI
        self._setup_window()
        log_debug("Window configured")
        self._setup_ui()
        log_debug("UI setup complete")
        self._setup_tray()
        log_debug("Tray setup complete")
        self._connect_signals()
        log_debug("Signals connected")

        # Set up hotkey after signals are connected
        self._setup_hotkey()
        log_debug("Hotkey setup complete")

        # Start loading OCR model
        self._start_ocr_loading()

        # Auto-launch japReader if enabled
        self._auto_launch_japreader()

        log_info("MainWindow initialization complete")

    def _get_default_settings(self) -> dict:
        """Get default settings."""
        return {
            "capture_hotkey": "ctrl+shift",
            "ocr_engine": OCREngine.MANGA_OCR.value,
            "preprocessing_mode": "none",
            "auto_copy": True,
            "show_notification": True,
            "start_minimized": True,
            "macro_enabled": False,
            "macro_events": [],
            "kill_key": "f12",
            "overlay_geometry": None,
            "japreader_autolaunch": False,
            "japreader_path": "",
        }

    def _load_settings(self) -> None:
        """Load settings from file."""
        settings_file = "ocr_settings.json"
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r") as f:
                    loaded = json.load(f)
                    self._settings.update(loaded)
                    log_info(f"Settings loaded from {settings_file}: hotkey={self._settings.get('capture_hotkey')}")
            except Exception as e:
                log_error(f"Failed to load settings: {e}")
        else:
            log_info(f"No settings file found at {settings_file}, using defaults")

        # Set the OCR engine from settings
        engine_value = self._settings.get("ocr_engine", OCREngine.MANGA_OCR.value)
        try:
            engine = OCREngine(engine_value)
            self._ocr_manager.set_engine(engine)
            log_info(f"OCR engine set to: {get_engine_name(engine)}")
        except ValueError:
            log_warning(f"Unknown OCR engine: {engine_value}, using default manga-ocr")
            self._ocr_manager.set_engine(OCREngine.MANGA_OCR)

    def _setup_window(self) -> None:
        """Configure the main window."""
        self.setWindowTitle("代書 - Japanese OCR")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)

        # Dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: #e0e0e0;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
            QPushButton#primary {
                background-color: #ff6b6b;
                color: #1a1a1a;
            }
            QPushButton#primary:hover {
                background-color: #ff5252;
            }
            QTextEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Yu Gothic UI', 'Meiryo', sans-serif;
                font-size: 14px;
            }
            QGroupBox {
                border: 2px solid #ff6b6b;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #ff6b6b;
            }
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QStatusBar {
                background-color: #2d2d2d;
                color: #a0a0a0;
            }
        """)

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("代書")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #ff6b6b;")
        layout.addWidget(header)

        subtitle = QLabel("High-precision Japanese OCR")
        subtitle.setStyleSheet("color: #808080; font-size: 12px;")
        layout.addWidget(subtitle)

        # Status section
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)

        self._status_label = QLabel("Loading OCR model...")
        self._status_label.setStyleSheet("font-size: 14px;")
        status_layout.addWidget(self._status_label)

        self._gpu_label = QLabel("")
        self._gpu_label.setStyleSheet("color: #808080; font-size: 11px;")
        status_layout.addWidget(self._gpu_label)

        # Show current hotkey
        hotkey = self._settings.get("capture_hotkey", "ctrl+shift")
        self._hotkey_label = QLabel(f"Capture hotkey: {hotkey}")
        self._hotkey_label.setStyleSheet("color: #808080; font-size: 11px;")
        status_layout.addWidget(self._hotkey_label)

        layout.addWidget(status_group)

        # Controls section
        controls_group = QGroupBox("Controls")
        controls_layout = QHBoxLayout(controls_group)

        self._show_overlay_btn = QPushButton("Show Overlay")
        self._show_overlay_btn.setObjectName("primary")
        self._show_overlay_btn.clicked.connect(self._show_overlay)
        controls_layout.addWidget(self._show_overlay_btn)

        self._hide_overlay_btn = QPushButton("Hide Overlay")
        self._hide_overlay_btn.clicked.connect(self._hide_overlay)
        self._hide_overlay_btn.setEnabled(False)
        controls_layout.addWidget(self._hide_overlay_btn)

        self._capture_btn = QPushButton("Capture Now")
        self._capture_btn.clicked.connect(self._manual_capture)
        controls_layout.addWidget(self._capture_btn)

        self._settings_btn = QPushButton("Settings")
        self._settings_btn.clicked.connect(self._show_settings)
        controls_layout.addWidget(self._settings_btn)

        controls_layout.addStretch()

        layout.addWidget(controls_group)

        # Preprocessing mode
        preprocess_group = QGroupBox("Preprocessing Mode")
        preprocess_layout = QHBoxLayout(preprocess_group)

        self._preprocess_combo = QComboBox()
        for mode in PreprocessingMode:
            self._preprocess_combo.addItem(mode_description(mode), mode.value)
        self._preprocess_combo.currentIndexChanged.connect(self._on_preprocess_change)

        # Set to saved mode
        saved_mode = self._settings.get("preprocessing_mode", "none")
        index = self._preprocess_combo.findData(saved_mode)
        if index >= 0:
            self._preprocess_combo.setCurrentIndex(index)

        preprocess_layout.addWidget(self._preprocess_combo)
        preprocess_layout.addStretch()

        layout.addWidget(preprocess_group)

        # Results section
        results_group = QGroupBox("OCR Results")
        results_layout = QVBoxLayout(results_group)

        self._results_text = QTextEdit()
        hotkey = self._settings.get("capture_hotkey", "ctrl+shift")
        self._results_text.setPlaceholderText(
            "OCR results will appear here...\n\n"
            "1. Click 'Show Overlay' to display the capture region\n"
            "2. Position and resize the overlay over Japanese text\n"
            f"3. Press the capture hotkey ({hotkey})"
        )
        results_layout.addWidget(self._results_text)

        # Result buttons
        result_buttons = QHBoxLayout()

        copy_btn = QPushButton("Copy All")
        copy_btn.clicked.connect(self._copy_results)
        result_buttons.addWidget(copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_results)
        result_buttons.addWidget(clear_btn)

        result_buttons.addStretch()
        results_layout.addLayout(result_buttons)

        layout.addWidget(results_group)

        # Status bar
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Ready")

    def _load_and_recolor_icon(self) -> QIcon:
        """Load icon from file and shift color to purple."""
        import os
        from PyQt6.QtGui import QPainter, QBrush, QImage

        # Try to load the icon from the specified path
        appdata = os.environ.get('APPDATA', '')
        icon_path = os.path.join(
            appdata,
            'Mozilla', 'Firefox', 'Profiles',
            'wwhjpx9k.default-release', 'taskbartabs', 'icons',
            'c6f48e66-845c-4ef6-967c-6130bdc54f4a.ico'
        )

        if os.path.exists(icon_path):
            try:
                # Load with PIL to manipulate colors
                from PIL import Image as PILImage
                import numpy as np

                pil_img = PILImage.open(icon_path)
                # Get the largest size or use 64x64
                if hasattr(pil_img, 'n_frames'):
                    # ICO files can have multiple sizes
                    pil_img.seek(0)
                pil_img = pil_img.convert('RGBA')
                pil_img = pil_img.resize((64, 64), PILImage.Resampling.LANCZOS)

                # Convert to numpy for color manipulation
                img_array = np.array(pil_img)

                # Shift colors to purple (swap red and blue, boost both)
                # Original RGB -> Purple shift: increase R and B, reduce G
                r = img_array[:, :, 0].astype(float)
                g = img_array[:, :, 1].astype(float)
                b = img_array[:, :, 2].astype(float)
                a = img_array[:, :, 3]

                # Purple shift: R stays, G reduces, B increases
                # Create a purple tint effect
                new_r = np.clip(r * 0.8 + b * 0.4, 0, 255).astype(np.uint8)
                new_g = np.clip(g * 0.3, 0, 255).astype(np.uint8)
                new_b = np.clip(b * 0.6 + r * 0.6, 0, 255).astype(np.uint8)

                img_array[:, :, 0] = new_r
                img_array[:, :, 1] = new_g
                img_array[:, :, 2] = new_b

                # Convert back to PIL then to QPixmap
                purple_img = PILImage.fromarray(img_array, 'RGBA')
                data = purple_img.tobytes('raw', 'RGBA')

                qimage = QImage(data, 64, 64, QImage.Format.Format_RGBA8888)
                pixmap = QPixmap.fromImage(qimage)

                log_info(f"Loaded and recolored icon from: {icon_path}")
                return QIcon(pixmap)

            except Exception as e:
                log_warning(f"Failed to load/recolor icon: {e}")

        # Fallback: create a simple purple circle icon
        log_info("Using fallback purple icon")
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor(128, 0, 128)))  # Purple
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(8, 8, 48, 48)
        painter.end()

        return QIcon(pixmap)

    def _setup_tray(self) -> None:
        """Set up system tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("System tray not available")
            return

        # Load icon (purple-shifted from Firefox taskbar icon)
        icon = self._load_and_recolor_icon()

        # Also set as window icon
        self.setWindowIcon(icon)

        # Create tray icon
        self._tray_icon = QSystemTrayIcon(icon, self)
        self._tray_icon.setToolTip("代書 - Japanese OCR")

        # Create menu
        menu = QMenu()

        show_action = menu.addAction("Show Window")
        show_action.triggered.connect(self.show)

        show_overlay_action = menu.addAction("Show Overlay")
        show_overlay_action.triggered.connect(self._show_overlay)

        hide_overlay_action = menu.addAction("Hide Overlay")
        hide_overlay_action.triggered.connect(self._hide_overlay)

        menu.addSeparator()

        # OCR Engine submenu
        self._engine_menu = menu.addMenu("OCR Engine")
        self._engine_actions = {}
        self._setup_engine_menu()

        menu.addSeparator()

        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self._show_settings)

        menu.addSeparator()

        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._quit)

        self._tray_icon.setContextMenu(menu)

        # Double-click to show/hide overlay
        self._tray_icon.activated.connect(self._on_tray_activated)

        self._tray_icon.show()

    def _setup_engine_menu(self) -> None:
        """Set up the OCR engine submenu with available engines."""
        self._engine_menu.clear()
        self._engine_actions.clear()

        current_engine = self._ocr_manager.current_engine

        for engine in OCREngine:
            name = get_engine_name(engine)
            action = self._engine_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(engine == current_engine)

            # Store reference and connect
            self._engine_actions[engine] = action
            # Use lambda with default arg to capture engine value
            action.triggered.connect(lambda checked, e=engine: self._on_engine_selected(e))

    def _on_engine_selected(self, engine: OCREngine) -> None:
        """Handle OCR engine selection from tray menu."""
        if engine == self._ocr_manager.current_engine:
            return  # Already selected

        log_info(f"Switching OCR engine to: {get_engine_name(engine)}")

        # Update checkmarks
        for eng, action in self._engine_actions.items():
            action.setChecked(eng == engine)

        # Update settings
        self._settings["ocr_engine"] = engine.value

        # Switch engine
        self._ocr_manager.set_engine(engine)

        # Reload model
        self._start_ocr_loading()

        # Save settings
        self._save_settings()

        # Show notification
        if self._tray_icon:
            self._tray_icon.showMessage(
                "OCR Engine Changed",
                f"Switching to {get_engine_name(engine)}...",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

    def _setup_hotkey(self) -> None:
        """Set up global hotkey (keyboard or mouse button)."""
        hotkey = self._settings.get("capture_hotkey", "ctrl+shift")

        # Check if this is a mouse button hotkey
        is_mouse = any(mb in hotkey.lower() for mb in ["mouse4", "mouse5", "middle"])

        # Unregister previous hotkeys
        self._unregister_hotkeys()

        if is_mouse:
            self._setup_mouse_hotkey(hotkey)
        else:
            self._setup_keyboard_hotkey(hotkey)

    def _unregister_hotkeys(self) -> None:
        """Unregister all hotkeys (keyboard and mouse)."""
        # Unregister keyboard hotkeys
        if self._hotkey_registered:
            try:
                import keyboard
                keyboard.unhook_all_hotkeys()
                log_debug("Unhooked keyboard hotkeys")
            except Exception as e:
                log_warning(f"Failed to unhook keyboard hotkeys: {e}")
            self._hotkey_registered = False

        # Unregister mouse hotkeys
        if getattr(self, '_mouse_hotkey_registered', False):
            try:
                import mouse
                mouse.unhook_all()
                log_debug("Unhooked mouse hotkeys")
            except Exception as e:
                log_warning(f"Failed to unhook mouse hotkeys: {e}")
            self._mouse_hotkey_registered = False

    def _setup_keyboard_hotkey(self, hotkey: str) -> None:
        """Set up a keyboard-based hotkey."""
        try:
            import keyboard

            keyboard.add_hotkey(hotkey, self._on_hotkey_pressed, suppress=False)
            self._hotkey_registered = True
            log_info(f"Global keyboard hotkey registered: {hotkey}")

        except ImportError:
            log_warning("keyboard module not installed. Global hotkeys disabled.")
        except Exception as e:
            log_error(f"Could not set up keyboard hotkey: {e}")
            log_exception(e, "_setup_keyboard_hotkey")

    def _setup_mouse_hotkey(self, hotkey: str) -> None:
        """Set up a mouse button-based hotkey."""
        try:
            import mouse

            # Parse the hotkey to get the mouse button
            parts = hotkey.lower().split("+")
            mouse_button = None
            modifiers = []

            for part in parts:
                if part in ["mouse4", "mouse5", "middle"]:
                    # Map to mouse library button names
                    if part == "mouse4":
                        mouse_button = "x"  # XButton1 (back)
                    elif part == "mouse5":
                        mouse_button = "x2"  # XButton2 (forward)
                    elif part == "middle":
                        mouse_button = "middle"
                elif part in ["ctrl", "alt", "shift", "win"]:
                    modifiers.append(part)

            if mouse_button is None:
                log_error(f"Could not parse mouse button from hotkey: {hotkey}")
                return

            # Store modifiers for checking during callback
            self._mouse_hotkey_modifiers = modifiers

            def mouse_callback(event):
                """Handle mouse button events."""
                if not isinstance(event, mouse.ButtonEvent):
                    return
                if event.event_type != 'down':
                    return
                if event.button != mouse_button:
                    return

                # Check keyboard modifiers if required
                if self._mouse_hotkey_modifiers:
                    try:
                        import keyboard
                        for mod in self._mouse_hotkey_modifiers:
                            if not keyboard.is_pressed(mod):
                                return
                    except Exception:
                        pass

                log_debug(f"Mouse hotkey triggered: {hotkey}")
                self.triggerCapture.emit()

            mouse.hook(mouse_callback)
            self._mouse_hotkey_registered = True
            log_info(f"Global mouse hotkey registered: {hotkey}")

        except ImportError:
            log_warning("mouse module not installed. Mouse hotkeys disabled.")
        except Exception as e:
            log_error(f"Could not set up mouse hotkey: {e}")
            log_exception(e, "_setup_mouse_hotkey")

    def _on_hotkey_pressed(self) -> None:
        """
        Called when hotkey is pressed (runs in keyboard thread).
        Emits signal to trigger capture in main Qt thread.
        """
        log_debug("Hotkey pressed, emitting triggerCapture signal")
        # Emit signal to main thread
        self.triggerCapture.emit()

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.ocrCompleted.connect(self._on_ocr_complete)
        self.ocrError.connect(self._on_ocr_error)
        # Connect capture trigger signal for thread-safe hotkey handling
        self.triggerCapture.connect(self._do_capture_from_hotkey)

    def _do_capture_from_hotkey(self) -> None:
        """Handle capture trigger from hotkey (runs in main Qt thread)."""
        log_debug("_do_capture_from_hotkey called")
        if self._overlay is not None and self._overlay.isVisible():
            if self._overlay.hotkey_enabled:
                log_info("Triggering capture from hotkey")
                self._overlay.capture_region()
            else:
                log_debug("Hotkey paused - toggle button is yellow")
        else:
            log_debug("Overlay not visible, ignoring hotkey")

    def _manual_capture(self) -> None:
        """Manually trigger capture from button."""
        if self._overlay is not None and self._overlay.isVisible():
            self._overlay.capture_region()
        else:
            if self._statusbar:
                self._statusbar.showMessage("Show overlay first, then capture")

    def _start_ocr_loading(self) -> None:
        """Start loading the OCR model asynchronously."""
        engine_name = get_engine_name(self._ocr_manager.current_engine)
        self._status_label.setText(f"Loading {engine_name}...")
        self._ocr_manager.load_model_async(self._on_model_loaded)

    def _is_process_running(self, process_name: str) -> bool:
        """Check if a process with the given name is already running."""
        import subprocess
        try:
            # Use tasklist on Windows to check for running processes
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {process_name}', '/NH'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # If the process is found, tasklist returns it; otherwise "INFO: No tasks..."
            return process_name.lower() in result.stdout.lower()
        except Exception as e:
            log_debug(f"Failed to check if {process_name} is running: {e}")
            return False

    def _auto_launch_japreader(self) -> None:
        """Auto-launch japReader if enabled in settings and not already running."""
        if not self._settings.get("japreader_autolaunch", False):
            return

        japreader_path = self._settings.get("japreader_path", "")
        if not japreader_path or not os.path.isfile(japreader_path):
            log_debug("japReader auto-launch enabled but path not found")
            return

        # Check if japReader is already running
        exe_name = os.path.basename(japreader_path)
        if self._is_process_running(exe_name):
            log_info(f"japReader ({exe_name}) is already running, skipping auto-launch")
            return

        try:
            import subprocess
            subprocess.Popen(
                [japreader_path],
                cwd=os.path.dirname(japreader_path),
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
            log_info(f"Auto-launched japReader from: {japreader_path}")
        except Exception as e:
            log_error(f"Failed to auto-launch japReader: {e}")

    def _on_model_loaded(self, success: bool, error: Optional[str]) -> None:
        """Handle OCR model load completion (may be called from background thread)."""
        # Use QTimer to ensure we're in the main thread
        QTimer.singleShot(0, lambda: self._update_model_status(success, error))

    def _update_model_status(self, success: bool, error: Optional[str]) -> None:
        """Update UI after model load (runs in main thread)."""
        engine_name = get_engine_name(self._ocr_manager.current_engine)
        if success:
            self._status_label.setText(f"Ready - {engine_name} loaded")
            self._status_label.setStyleSheet("color: #4caf50; font-size: 14px;")

            if self._ocr_manager.uses_gpu:
                self._gpu_label.setText("GPU acceleration enabled")
            else:
                self._gpu_label.setText("Running on CPU")
        else:
            self._status_label.setText(f"Error: {error}")
            self._status_label.setStyleSheet("color: #f44336; font-size: 14px;")

    def _show_overlay(self) -> None:
        """Show the capture overlay."""
        if self._overlay is None:
            self._overlay = CaptureWindow()
            self._overlay.captureCompleted.connect(self._on_capture)
            self._overlay.geometryChanged.connect(self._on_overlay_geometry_changed)

            # Restore saved geometry
            if self._settings.get("overlay_geometry"):
                self._overlay.restore_geometry_string(self._settings["overlay_geometry"])

        self._overlay.show()
        self._overlay.raise_()
        self._overlay.activateWindow()
        self._show_overlay_btn.setEnabled(False)
        self._hide_overlay_btn.setEnabled(True)

    def _hide_overlay(self) -> None:
        """Hide the capture overlay."""
        if self._overlay is not None:
            self._overlay.hide()
        self._show_overlay_btn.setEnabled(True)
        self._hide_overlay_btn.setEnabled(False)

    def _on_overlay_geometry_changed(self, geometry) -> None:
        """Save overlay geometry when it changes."""
        if self._overlay:
            self._settings["overlay_geometry"] = self._overlay.save_geometry_string()

    def _on_capture(self, pil_image: Image.Image) -> None:
        """Handle captured screen region (PIL Image from overlay)."""
        log_info(f"Capture received, image size: {pil_image.size}")

        if not self._ocr_manager.is_loaded:
            log_warning("OCR engine not loaded yet")
            QMessageBox.warning(self, "OCR Not Ready", "OCR model is still loading...")
            return

        if self._statusbar:
            self._statusbar.showMessage("Processing...")
        self._append_result("--- Processing capture... ---")

        # Process in background thread
        def process():
            try:
                # Get preprocessing mode
                mode_str = self._settings.get("preprocessing_mode", "none")
                mode = PreprocessingMode(mode_str)
                log_debug(f"Using preprocessing mode: {mode_str}")

                # Preprocess
                processed = preprocess_image(pil_image, mode)
                log_debug(f"Preprocessed image size: {processed.size}")

                # Run OCR using the manager
                engine_name = get_engine_name(self._ocr_manager.current_engine)
                log_debug(f"Running OCR inference with {engine_name}...")
                result = self._ocr_manager.perform_ocr(processed)
                log_info(f"OCR result: {result[:50]}..." if len(result) > 50 else f"OCR result: {result}")

                # Emit result (thread-safe via signal)
                self.ocrCompleted.emit(result)

            except Exception as e:
                log_exception(e, "_on_capture.process")
                self.ocrError.emit(str(e))

        thread = threading.Thread(target=process, daemon=True)
        thread.start()

    def _on_ocr_complete(self, text: str) -> None:
        """Handle OCR completion."""
        if text:
            self._append_result(f"Result:\n{text}\n")

            # Auto-copy to clipboard
            if self._settings.get("auto_copy", True):
                if copy_text(text):
                    self._statusbar.showMessage("Result copied to clipboard")

                    # Show notification
                    if self._settings.get("show_notification", True) and self._tray_icon:
                        self._tray_icon.showMessage(
                            "OCR Complete",
                            f"Copied: {text[:50]}..." if len(text) > 50 else f"Copied: {text}",
                            QSystemTrayIcon.MessageIcon.Information,
                            2000
                        )
                else:
                    self._statusbar.showMessage("OCR complete (clipboard copy failed)")
            else:
                self._statusbar.showMessage("OCR complete")

            # Run post-capture macro
            if self._settings.get("macro_enabled", False):
                events = self._settings.get("macro_events", [])
                if events:
                    self._macro_manager.load_events(events)
                    self._macro_manager.play()
        else:
            self._append_result("--- No text found ---")
            self._statusbar.showMessage("No text detected")

    def _on_ocr_error(self, error: str) -> None:
        """Handle OCR error."""
        self._append_result(f"Error: {error}")
        self._statusbar.showMessage("OCR error")
        QMessageBox.warning(self, "OCR Error", f"An error occurred:\n{error}")

    def _append_result(self, text: str) -> None:
        """Append text to results area."""
        self._results_text.append(text)

    def _copy_results(self) -> None:
        """Copy all results to clipboard."""
        text = self._results_text.toPlainText()
        if text:
            if copy_text(text):
                self._statusbar.showMessage("Results copied to clipboard")
            else:
                self._statusbar.showMessage("Failed to copy to clipboard")
        else:
            self._statusbar.showMessage("No results to copy")

    def _clear_results(self) -> None:
        """Clear the results area."""
        self._results_text.clear()

    def _on_preprocess_change(self, index: int) -> None:
        """Handle preprocessing mode change."""
        mode = self._preprocess_combo.currentData()
        self._settings["preprocessing_mode"] = mode
        log_debug(f"Preprocessing mode changed to: {mode}")
        # Check if statusbar exists (may not during initial setup)
        if self._statusbar is not None:
            self._statusbar.showMessage(f"Preprocessing mode: {mode}")

    def _show_settings(self) -> None:
        """Show the settings dialog."""
        from .settings import SettingsDialog

        dialog = SettingsDialog(self._settings, self)
        dialog.settingsChanged.connect(self._apply_settings)

        if dialog.exec():
            self._settings = dialog.get_settings()
            self._save_settings()

    def _apply_settings(self, settings: dict) -> None:
        """Apply new settings."""
        old_hotkey = self._settings.get("capture_hotkey")
        new_hotkey = settings.get("capture_hotkey")
        old_engine = self._settings.get("ocr_engine")
        new_engine = settings.get("ocr_engine")

        self._settings.update(settings)

        # Re-register hotkey if changed
        if old_hotkey != new_hotkey:
            self._setup_hotkey()
            self._hotkey_label.setText(f"Capture hotkey: {new_hotkey}")

        # Switch OCR engine if changed
        if old_engine != new_engine:
            try:
                engine = OCREngine(new_engine)
                self._ocr_manager.set_engine(engine)
                log_info(f"Switching OCR engine to: {get_engine_name(engine)}")
                # Update tray menu checkmarks
                if hasattr(self, '_engine_actions'):
                    for eng, action in self._engine_actions.items():
                        action.setChecked(eng == engine)
                # Reload the new engine
                self._start_ocr_loading()
            except ValueError:
                log_warning(f"Unknown OCR engine: {new_engine}")

        # Update preprocessing combo
        mode = settings.get("preprocessing_mode", "none")
        index = self._preprocess_combo.findData(mode)
        if index >= 0:
            self._preprocess_combo.setCurrentIndex(index)

        # Update macro kill key
        self._macro_manager.set_kill_key(settings.get("kill_key", "f12"))

    def _save_settings(self) -> None:
        """Save settings to file."""
        try:
            with open("ocr_settings.json", "w") as f:
                json.dump(self._settings, f, indent=2)
            log_info("Settings saved to ocr_settings.json")
        except Exception as e:
            log_error(f"Failed to save settings: {e}")

    def _on_tray_activated(self, reason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self._overlay and self._overlay.isVisible():
                self._hide_overlay()
            else:
                self._show_overlay()

    def _quit(self) -> None:
        """Quit the application."""
        # Save settings
        if self._overlay:
            self._settings["overlay_geometry"] = self._overlay.save_geometry_string()
        self._save_settings()

        # Unregister all hotkeys (keyboard and mouse)
        self._unregister_hotkeys()

        # Hide tray icon
        if self._tray_icon:
            self._tray_icon.hide()

        # Close overlay
        if self._overlay:
            self._overlay.close()

        # Quit application
        QApplication.quit()

    def closeEvent(self, event) -> None:
        """Handle window close - minimize to tray instead."""
        if self._tray_icon and self._tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            self._quit()
