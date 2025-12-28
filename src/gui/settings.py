"""
Settings Dialog - Configuration UI for the OCR tool.

Provides controls for hotkey configuration, preprocessing mode,
and macro management.
"""

from __future__ import annotations
import os
import subprocess
from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QLineEdit, QComboBox,
    QCheckBox, QSlider, QSpinBox, QTabWidget,
    QWidget, QFormLayout, QMessageBox, QTextEdit,
    QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence

from ..utils.logger import log_info, log_error, log_debug
from ..utils.image_ops import PreprocessingMode, get_available_modes, mode_description
from ..core.ocr_manager import OCREngine, get_engine_name, get_engine_description


class HotkeyEdit(QLineEdit):
    """
    Custom line edit for recording keyboard shortcuts and mouse buttons.

    Records key combinations or mouse buttons when focused and displays them
    in a human-readable format. Supports mouse4, mouse5 (side buttons), etc.
    """

    hotkeyChanged = pyqtSignal(str)

    # Mouse button names for the `mouse` library
    MOUSE_BUTTON_NAMES = {
        Qt.MouseButton.MiddleButton: "middle",
        Qt.MouseButton.BackButton: "mouse4",  # Back/XButton1
        Qt.MouseButton.ForwardButton: "mouse5",  # Forward/XButton2
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._recording = False
        self._modifiers = set()
        self._key = ""
        self._is_mouse_button = False
        self.setReadOnly(True)
        self.setPlaceholderText("Click to record hotkey or mouse button...")

    def mousePressEvent(self, event) -> None:
        """Handle mouse press - start recording or capture mouse button."""
        if not self._recording:
            # First click starts recording
            self._start_recording()
        else:
            # If already recording, check for special mouse buttons
            button = event.button()
            if button in self.MOUSE_BUTTON_NAMES:
                # Capture this mouse button as the hotkey
                self._key = self.MOUSE_BUTTON_NAMES[button]
                self._is_mouse_button = True
                self._update_display()
                self._stop_recording()
                return
        super().mousePressEvent(event)

    def _start_recording(self) -> None:
        """Begin recording a hotkey or mouse button."""
        self._recording = True
        self._modifiers.clear()
        self._key = ""
        self._is_mouse_button = False
        self.setText("Press key or mouse button...")
        self.setStyleSheet("background-color: #ffe0e0;")

    def keyPressEvent(self, event) -> None:
        """Record key presses."""
        if not self._recording:
            return

        key = event.key()
        modifiers = event.modifiers()

        # Build modifier set
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            self._modifiers.add("ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            self._modifiers.add("alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            self._modifiers.add("shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            self._modifiers.add("win")

        # Get key name
        key_name = self._key_to_string(key)
        if key_name:
            self._key = key_name

        # Update display
        self._update_display()

    def keyReleaseEvent(self, event) -> None:
        """Finish recording on key release."""
        if self._recording and self._key:
            self._stop_recording()

    def _stop_recording(self) -> None:
        """Finish recording and emit the hotkey."""
        self._recording = False
        self.setStyleSheet("")

        if self._modifiers or self._key:
            hotkey = self._build_hotkey_string()
            self.setText(hotkey)
            self.hotkeyChanged.emit(hotkey)

    def _update_display(self) -> None:
        """Update the displayed hotkey string."""
        self.setText(self._build_hotkey_string())

    def _build_hotkey_string(self) -> str:
        """Build a hotkey string from recorded keys or mouse button."""
        parts = []

        # For mouse buttons, modifiers are optional but supported
        # Add modifiers in standard order
        for mod in ["ctrl", "alt", "shift", "win"]:
            if mod in self._modifiers:
                parts.append(mod)

        # Add the key or mouse button
        if self._key:
            parts.append(self._key)

        return "+".join(parts) if parts else ""

    def is_mouse_hotkey(self) -> bool:
        """Check if the current hotkey is a mouse button."""
        hotkey = self.text().lower()
        return any(mb in hotkey for mb in ["mouse4", "mouse5", "middle"])

    def _key_to_string(self, key: int) -> str:
        """Convert Qt key code to string."""
        # Skip modifier-only keys
        modifier_keys = {
            Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift,
            Qt.Key.Key_Meta, Qt.Key.Key_AltGr
        }
        if key in modifier_keys:
            return ""

        # Special keys
        special_keys = {
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Escape: "esc",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "pageup",
            Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_Insert: "insert",
        }

        if key in special_keys:
            return special_keys[key]

        # Function keys
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            return f"f{key - Qt.Key.Key_F1 + 1}"

        # Regular keys
        seq = QKeySequence(key)
        text = seq.toString().lower()
        return text if len(text) == 1 else ""

    def set_hotkey(self, hotkey: str) -> None:
        """Set the displayed hotkey."""
        self.setText(hotkey)
        parts = hotkey.lower().split("+")
        self._modifiers = {p for p in parts if p in ("ctrl", "alt", "shift", "win")}
        self._key = next((p for p in parts if p not in self._modifiers), "")
        # Check if it's a mouse button
        self._is_mouse_button = any(mb in hotkey.lower() for mb in ["mouse4", "mouse5", "middle"])

    def get_hotkey(self) -> str:
        """Get the current hotkey string."""
        return self.text()


class SettingsDialog(QDialog):
    """
    Settings dialog for OCR tool configuration.

    Contains tabs for:
    - General settings (hotkey, preprocessing)
    - Macro configuration
    - About information
    """

    settingsChanged = pyqtSignal(dict)

    def __init__(
        self,
        current_settings: dict,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._settings = current_settings.copy()
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(450, 400)

        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_macro_tab(), "Macros")
        tabs.addTab(self._create_integrations_tab(), "Integrations")
        tabs.addTab(self._create_about_tab(), "About")
        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.clicked.connect(self._apply_settings)
        button_layout.addWidget(self._apply_btn)

        self._ok_btn = QPushButton("OK")
        self._ok_btn.clicked.connect(self._ok_clicked)
        button_layout.addWidget(self._ok_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self._cancel_btn)

        layout.addLayout(button_layout)

    def _create_general_tab(self) -> QWidget:
        """Create the general settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Hotkey settings
        hotkey_group = QGroupBox("Capture Hotkey")
        hotkey_layout = QFormLayout(hotkey_group)

        self._hotkey_edit = HotkeyEdit()
        hotkey_layout.addRow("Hotkey:", self._hotkey_edit)

        help_label = QLabel(
            "Click the field, then press a key combination or mouse button.\n"
            "Supports: keyboard keys, mouse4 (back), mouse5 (forward), middle click"
        )
        help_label.setStyleSheet("color: gray; font-size: 10px;")
        hotkey_layout.addRow(help_label)

        layout.addWidget(hotkey_group)

        # OCR Engine selection
        engine_group = QGroupBox("OCR Engine")
        engine_layout = QFormLayout(engine_group)

        self._engine_combo = QComboBox()
        for engine in OCREngine:
            self._engine_combo.addItem(get_engine_name(engine), engine.value)
        self._engine_combo.currentIndexChanged.connect(self._on_engine_change)
        engine_layout.addRow("Engine:", self._engine_combo)

        self._engine_desc_label = QLabel("")
        self._engine_desc_label.setStyleSheet("color: gray; font-size: 10px;")
        self._engine_desc_label.setWordWrap(True)
        engine_layout.addRow(self._engine_desc_label)

        engine_note = QLabel(
            "Note: Changing engines requires reloading the model.\n"
            "manga-ocr is best for manga/games. PaddleOCR is faster but less specialized."
        )
        engine_note.setStyleSheet("color: #ff9800; font-size: 10px;")
        engine_note.setWordWrap(True)
        engine_layout.addRow(engine_note)

        layout.addWidget(engine_group)

        # Preprocessing settings
        preprocess_group = QGroupBox("Image Preprocessing")
        preprocess_layout = QFormLayout(preprocess_group)

        self._preprocess_combo = QComboBox()
        for mode in get_available_modes():
            self._preprocess_combo.addItem(mode_description(mode), mode.value)
        preprocess_layout.addRow("Mode:", self._preprocess_combo)

        preprocess_help = QLabel(
            "None: Best for manga-ocr (recommended)\n"
            "Advanced: Full OpenCV pipeline for difficult images"
        )
        preprocess_help.setStyleSheet("color: gray; font-size: 10px;")
        preprocess_layout.addRow(preprocess_help)

        layout.addWidget(preprocess_group)

        # Behavior settings
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(behavior_group)

        self._auto_copy_cb = QCheckBox("Automatically copy OCR result to clipboard")
        self._auto_copy_cb.setChecked(True)
        behavior_layout.addWidget(self._auto_copy_cb)

        self._show_notification_cb = QCheckBox("Show notification after capture")
        self._show_notification_cb.setChecked(True)
        behavior_layout.addWidget(self._show_notification_cb)

        self._start_minimized_cb = QCheckBox("Start minimized to system tray")
        self._start_minimized_cb.setChecked(True)
        behavior_layout.addWidget(self._start_minimized_cb)

        layout.addWidget(behavior_group)

        layout.addStretch()
        return widget

    def _create_macro_tab(self) -> QWidget:
        """Create the macro settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Post-capture macro
        macro_group = QGroupBox("Post-Capture Macro")
        macro_layout = QVBoxLayout(macro_group)

        macro_help = QLabel(
            "Record a sequence of keyboard/mouse actions to play after each capture.\n"
            "Useful for automatically turning pages in manga readers."
        )
        macro_help.setWordWrap(True)
        macro_layout.addWidget(macro_help)

        self._macro_enabled_cb = QCheckBox("Enable post-capture macro")
        macro_layout.addWidget(self._macro_enabled_cb)

        button_layout = QHBoxLayout()
        self._record_macro_btn = QPushButton("Record Macro")
        self._record_macro_btn.clicked.connect(self._record_macro)
        button_layout.addWidget(self._record_macro_btn)

        self._clear_macro_btn = QPushButton("Clear Macro")
        self._clear_macro_btn.clicked.connect(self._clear_macro)
        button_layout.addWidget(self._clear_macro_btn)

        button_layout.addStretch()
        macro_layout.addLayout(button_layout)

        self._macro_display = QTextEdit()
        self._macro_display.setReadOnly(True)
        self._macro_display.setMaximumHeight(100)
        self._macro_display.setPlaceholderText("No macro recorded")
        macro_layout.addWidget(self._macro_display)

        layout.addWidget(macro_group)

        # Kill key setting
        safety_group = QGroupBox("Safety")
        safety_layout = QFormLayout(safety_group)

        self._kill_key_edit = HotkeyEdit()
        self._kill_key_edit.set_hotkey("f12")
        safety_layout.addRow("Kill key:", self._kill_key_edit)

        kill_help = QLabel("Press this key to immediately stop macro playback")
        kill_help.setStyleSheet("color: gray; font-size: 10px;")
        safety_layout.addRow(kill_help)

        layout.addWidget(safety_group)

        layout.addStretch()
        return widget

    def _create_integrations_tab(self) -> QWidget:
        """Create the integrations tab for external app connections."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # japReader integration
        japreader_group = QGroupBox("japReader Integration")
        japreader_layout = QVBoxLayout(japreader_group)

        japreader_help = QLabel(
            "japReader is a Japanese text reader app that works well with OCR output.\n"
            "Enable this to automatically launch japReader when starting 代書."
        )
        japreader_help.setWordWrap(True)
        japreader_layout.addWidget(japreader_help)

        # Auto-launch checkbox
        self._japreader_autolaunch_cb = QCheckBox("Auto-launch japReader on startup")
        japreader_layout.addWidget(self._japreader_autolaunch_cb)

        # Path configuration
        path_layout = QHBoxLayout()
        path_label = QLabel("Path:")
        self._japreader_path_edit = QLineEdit()
        self._japreader_path_edit.setPlaceholderText("Auto-detect or browse...")
        self._japreader_browse_btn = QPushButton("Browse...")
        self._japreader_browse_btn.clicked.connect(self._browse_japreader_path)

        path_layout.addWidget(path_label)
        path_layout.addWidget(self._japreader_path_edit, 1)
        path_layout.addWidget(self._japreader_browse_btn)
        japreader_layout.addLayout(path_layout)

        # Status and launch button
        status_layout = QHBoxLayout()
        self._japreader_status_label = QLabel("")
        self._japreader_status_label.setStyleSheet("color: gray; font-size: 10px;")
        status_layout.addWidget(self._japreader_status_label, 1)

        self._japreader_launch_btn = QPushButton("Launch japReader")
        self._japreader_launch_btn.clicked.connect(self._launch_japreader)
        status_layout.addWidget(self._japreader_launch_btn)

        japreader_layout.addLayout(status_layout)

        layout.addWidget(japreader_group)

        # Detect japReader on tab creation
        self._detect_japreader()

        layout.addStretch()
        return widget

    def _get_japreader_paths(self) -> list:
        """Get list of common japReader installation paths to check."""
        paths = []

        # Common installation locations
        program_files = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
        program_files_x86 = os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')
        local_appdata = os.environ.get('LOCALAPPDATA', '')
        appdata = os.environ.get('APPDATA', '')
        user_home = os.path.expanduser('~')

        # japReader possible locations
        possible_paths = [
            os.path.join(program_files, 'japReader', 'japReader.exe'),
            os.path.join(program_files_x86, 'japReader', 'japReader.exe'),
            os.path.join(local_appdata, 'japReader', 'japReader.exe'),
            os.path.join(appdata, 'japReader', 'japReader.exe'),
            os.path.join(user_home, 'japReader', 'japReader.exe'),
            os.path.join(local_appdata, 'Programs', 'japReader', 'japReader.exe'),
            # GitHub releases often extract to Downloads or Desktop
            os.path.join(user_home, 'Downloads', 'japReader', 'japReader.exe'),
            os.path.join(user_home, 'Desktop', 'japReader', 'japReader.exe'),
            # Portable installation in same directory as this app
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'japReader', 'japReader.exe'),
        ]

        return possible_paths

    def _detect_japreader(self) -> Optional[str]:
        """Detect japReader installation and update UI."""
        # First check if user has a saved path
        saved_path = self._settings.get("japreader_path", "")
        if saved_path and os.path.isfile(saved_path):
            self._japreader_path_edit.setText(saved_path)
            self._japreader_status_label.setText("✓ japReader found (saved path)")
            self._japreader_status_label.setStyleSheet("color: green; font-size: 10px;")
            self._japreader_launch_btn.setEnabled(True)
            log_debug(f"japReader found at saved path: {saved_path}")
            return saved_path

        # Try auto-detection
        for path in self._get_japreader_paths():
            if os.path.isfile(path):
                self._japreader_path_edit.setText(path)
                self._japreader_status_label.setText("✓ japReader auto-detected")
                self._japreader_status_label.setStyleSheet("color: green; font-size: 10px;")
                self._japreader_launch_btn.setEnabled(True)
                log_info(f"japReader auto-detected at: {path}")
                return path

        # Not found
        self._japreader_status_label.setText("japReader not found - please browse to locate")
        self._japreader_status_label.setStyleSheet("color: orange; font-size: 10px;")
        self._japreader_launch_btn.setEnabled(False)
        log_debug("japReader not found in common locations")
        return None

    def _browse_japreader_path(self) -> None:
        """Browse for japReader executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Locate japReader",
            os.path.expanduser("~"),
            "Executable (*.exe);;All Files (*.*)"
        )

        if file_path:
            self._japreader_path_edit.setText(file_path)
            if os.path.isfile(file_path):
                self._japreader_status_label.setText("✓ japReader path set")
                self._japreader_status_label.setStyleSheet("color: green; font-size: 10px;")
                self._japreader_launch_btn.setEnabled(True)
                self._settings["japreader_path"] = file_path
                log_info(f"japReader path manually set: {file_path}")

    def _launch_japreader(self) -> None:
        """Launch japReader application."""
        path = self._japreader_path_edit.text()

        if not path or not os.path.isfile(path):
            QMessageBox.warning(
                self,
                "Cannot Launch",
                "japReader executable not found.\n\n"
                "Please browse to the correct location."
            )
            return

        try:
            # Launch without waiting (detached process)
            subprocess.Popen(
                [path],
                cwd=os.path.dirname(path),
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
            log_info(f"Launched japReader from: {path}")
            self._japreader_status_label.setText("✓ japReader launched")
            self._japreader_status_label.setStyleSheet("color: green; font-size: 10px;")
        except Exception as e:
            log_error(f"Failed to launch japReader: {e}")
            QMessageBox.critical(
                self,
                "Launch Failed",
                f"Failed to launch japReader:\n{e}"
            )

    def _create_about_tab(self) -> QWidget:
        """Create the about tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        title = QLabel("代書")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Daisho - Japanese OCR")
        subtitle.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(subtitle)

        version = QLabel("Version 2.0.0")
        layout.addWidget(version)

        description = QLabel(
            "A high-precision Japanese OCR desktop application.\n\n"
            "Features:\n"
            "- Multiple OCR engines (manga-ocr, PaddleOCR)\n"
            "- Transparent overlay for easy region selection\n"
            "- Advanced image preprocessing options\n"
            "- Global hotkey and mouse button support\n"
            "- Macro recording for workflow automation\n"
            "- GPU acceleration support"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        links = QLabel(
            '<a href="https://github.com/kha-white/manga-ocr">manga-ocr</a> · '
            '<a href="https://github.com/PaddlePaddle/PaddleOCR">PaddleOCR</a>'
        )
        links.setOpenExternalLinks(True)
        layout.addWidget(links)

        layout.addStretch()
        return widget

    def _load_settings(self) -> None:
        """Load current settings into UI controls."""
        self._hotkey_edit.set_hotkey(
            self._settings.get("capture_hotkey", "ctrl+shift")
        )

        # OCR Engine
        engine = self._settings.get("ocr_engine", OCREngine.MANGA_OCR.value)
        engine_index = self._engine_combo.findData(engine)
        if engine_index >= 0:
            self._engine_combo.setCurrentIndex(engine_index)
        self._update_engine_description()

        mode = self._settings.get("preprocessing_mode", "none")
        index = self._preprocess_combo.findData(mode)
        if index >= 0:
            self._preprocess_combo.setCurrentIndex(index)

        self._auto_copy_cb.setChecked(
            self._settings.get("auto_copy", True)
        )
        self._show_notification_cb.setChecked(
            self._settings.get("show_notification", True)
        )
        self._start_minimized_cb.setChecked(
            self._settings.get("start_minimized", True)
        )

        self._macro_enabled_cb.setChecked(
            self._settings.get("macro_enabled", False)
        )
        self._kill_key_edit.set_hotkey(
            self._settings.get("kill_key", "f12")
        )

        # Display macro if present
        macro_events = self._settings.get("macro_events", [])
        if macro_events:
            self._macro_display.setText(f"{len(macro_events)} events recorded")
        else:
            self._macro_display.setText("")

        # japReader settings
        self._japreader_autolaunch_cb.setChecked(
            self._settings.get("japreader_autolaunch", False)
        )

    def _apply_settings(self) -> None:
        """Apply settings without closing dialog."""
        self._settings["capture_hotkey"] = self._hotkey_edit.get_hotkey()
        self._settings["ocr_engine"] = self._engine_combo.currentData()
        self._settings["preprocessing_mode"] = self._preprocess_combo.currentData()
        self._settings["auto_copy"] = self._auto_copy_cb.isChecked()
        self._settings["show_notification"] = self._show_notification_cb.isChecked()
        self._settings["start_minimized"] = self._start_minimized_cb.isChecked()
        self._settings["macro_enabled"] = self._macro_enabled_cb.isChecked()
        self._settings["kill_key"] = self._kill_key_edit.get_hotkey()

        # japReader settings
        self._settings["japreader_autolaunch"] = self._japreader_autolaunch_cb.isChecked()
        japreader_path = self._japreader_path_edit.text()
        if japreader_path:
            self._settings["japreader_path"] = japreader_path

        self.settingsChanged.emit(self._settings)

    def _ok_clicked(self) -> None:
        """Apply settings and close."""
        self._apply_settings()
        self.accept()

    def _on_engine_change(self, index: int) -> None:
        """Handle OCR engine selection change."""
        self._update_engine_description()

    def _update_engine_description(self) -> None:
        """Update the engine description label based on current selection."""
        engine_value = self._engine_combo.currentData()
        try:
            engine = OCREngine(engine_value)
            description = get_engine_description(engine)
            self._engine_desc_label.setText(description)
        except (ValueError, KeyError):
            self._engine_desc_label.setText("")

    def _record_macro(self) -> None:
        """Start macro recording (handled by main app)."""
        QMessageBox.information(
            self,
            "Record Macro",
            "Macro recording will start when you close this dialog.\n\n"
            "Perform your actions, then press the kill key to stop."
        )
        self._settings["_start_macro_recording"] = True

    def _clear_macro(self) -> None:
        """Clear the recorded macro."""
        self._settings["macro_events"] = []
        self._macro_display.setText("")

    def get_settings(self) -> dict:
        """Get the current settings."""
        self._apply_settings()
        return self._settings
