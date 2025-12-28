"""
Transparent Capture Overlay - PyQt6 implementation.

A frameless, transparent, always-on-top window for selecting screen regions.
Mimics the original Tkinter overlay behavior with red border, black interior,
and hotkey toggle button.
"""

from __future__ import annotations
from typing import Optional, Tuple, TYPE_CHECKING
from enum import Enum, auto
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QApplication, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QCursor,
    QPixmap, QScreen, QGuiApplication
)
from PIL import Image, ImageGrab

if TYPE_CHECKING:
    from PyQt6.QtGui import QMouseEvent, QPaintEvent


class ResizeEdge(Enum):
    """Edges and corners for resize detection."""
    NONE = auto()
    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
    TOP_LEFT = auto()
    TOP_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()


class CaptureWindow(QMainWindow):
    """
    Transparent, frameless overlay window for screen region capture.

    Mimics original Tkinter behavior:
    - Red border (2px) around the window
    - Black semi-transparent interior
    - Toggle button in top-right corner
    - Draggable from interior area
    - Resizable from edges/corners
    """

    # Signals
    captureCompleted = pyqtSignal(object)  # Emits PIL Image
    geometryChanged = pyqtSignal(QRect)

    # Constants
    BORDER_WIDTH = 2
    RESIZE_MARGIN = 8
    MIN_SIZE = 35
    OVERLAY_ALPHA = 0.25  # 25% opacity like original

    # Colors matching original
    BORDER_COLOR = QColor(255, 0, 0)  # Red border
    INTERIOR_COLOR = QColor(0, 0, 0)  # Black interior

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the capture overlay window."""
        super().__init__(parent)

        # State
        self._dragging = False
        self._resizing = False
        self._drag_start: Optional[QPoint] = None
        self._resize_edge = ResizeEdge.NONE
        self._initial_geometry: Optional[QRect] = None
        self._hotkey_enabled = True  # Hotkey toggle state

        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        """Configure window flags and attributes for transparency."""
        # Window flags: frameless, always on top, tool window (no taskbar)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Set window opacity (like Tkinter's alpha)
        self.setWindowOpacity(self.OVERLAY_ALPHA)

        # Set minimum size
        self.setMinimumSize(self.MIN_SIZE, self.MIN_SIZE)

        # Initial geometry
        self.setGeometry(100, 100, 300, 50)

        # Track mouse for cursor changes
        self.setMouseTracking(True)

        # Red background for border effect
        self.setStyleSheet("background-color: red;")

    def _setup_ui(self) -> None:
        """Set up UI elements - black interior frame and toggle button."""
        # Create central widget with layout
        central = QWidget(self)
        central.setMouseTracking(True)
        self.setCentralWidget(central)

        # Black interior frame (with margin for red border)
        self._interior = QFrame(central)
        self._interior.setStyleSheet("background-color: black; border: 1px solid black;")
        self._interior.setMouseTracking(True)

        # Toggle button in top-right corner
        # Red = hotkey active, Yellow = hotkey paused
        self._toggle_btn = QPushButton("停", self)
        self._toggle_btn.setFixedSize(24, 24)
        self._toggle_btn.clicked.connect(self._toggle_hotkey)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: red;
                color: white;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)

        # Position elements
        self._update_interior_geometry()

    def resizeEvent(self, event) -> None:
        """Handle resize to reposition interior and button."""
        super().resizeEvent(event)
        self._update_interior_geometry()

    def _update_interior_geometry(self) -> None:
        """Update interior frame and button positions."""
        # Interior frame fills window minus border
        margin = self.BORDER_WIDTH
        self._interior.setGeometry(
            margin, margin,
            self.width() - 2 * margin,
            self.height() - 2 * margin
        )

        # Position toggle button in top-right corner
        btn_margin = 5
        self._toggle_btn.move(
            self.width() - self._toggle_btn.width() - btn_margin,
            btn_margin
        )
        self._toggle_btn.raise_()  # Keep on top

    def _toggle_hotkey(self) -> None:
        """Toggle the hotkey capture on/off."""
        self._hotkey_enabled = not self._hotkey_enabled

        if self._hotkey_enabled:
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: red;
                    color: white;
                    border: none;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #cc0000;
                }
            """)
            print("Hotkey capture active")
        else:
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: yellow;
                    color: black;
                    border: none;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #cccc00;
                }
            """)
            print("Hotkey capture paused")

    @property
    def hotkey_enabled(self) -> bool:
        """Check if hotkey is enabled."""
        return self._hotkey_enabled

    @hotkey_enabled.setter
    def hotkey_enabled(self, value: bool) -> None:
        """Set hotkey enabled state."""
        if value != self._hotkey_enabled:
            self._toggle_hotkey()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for drag/resize initiation."""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position().toPoint()
        edge = self._get_resize_edge(pos)

        if edge != ResizeEdge.NONE:
            # Start resizing - just record the edge, we'll calculate incrementally
            self._resizing = True
            self._resize_edge = edge
        else:
            # Start dragging
            self._dragging = True
            self._drag_start = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for dragging, resizing, and cursor updates."""
        if self._dragging and self._drag_start is not None:
            # Move window
            new_pos = event.globalPosition().toPoint() - self._drag_start
            self.move(new_pos)

        elif self._resizing:
            # Resize window incrementally (like original Tkinter version)
            self._do_resize(event.globalPosition().toPoint())

        else:
            # Update cursor based on position
            pos = event.position().toPoint()
            edge = self._get_resize_edge(pos)
            self._update_cursor(edge)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._dragging or self._resizing:
                self.geometryChanged.emit(self.geometry())

            self._dragging = False
            self._resizing = False
            self._drag_start = None
            self._resize_edge = ResizeEdge.NONE
            self._initial_geometry = None

    def keyPressEvent(self, event) -> None:
        """Handle key press - Escape to hide."""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        super().keyPressEvent(event)

    def _get_resize_edge(self, pos: QPoint) -> ResizeEdge:
        """Determine which edge/corner the mouse is near."""
        m = self.RESIZE_MARGIN
        w = self.width()
        h = self.height()
        x = pos.x()
        y = pos.y()

        # Check corners first (they take priority)
        if x < m and y < m:
            return ResizeEdge.TOP_LEFT
        if x > w - m and y < m:
            return ResizeEdge.TOP_RIGHT
        if x < m and y > h - m:
            return ResizeEdge.BOTTOM_LEFT
        if x > w - m and y > h - m:
            return ResizeEdge.BOTTOM_RIGHT

        # Check edges
        if x < m:
            return ResizeEdge.LEFT
        if x > w - m:
            return ResizeEdge.RIGHT
        if y < m:
            return ResizeEdge.TOP
        if y > h - m:
            return ResizeEdge.BOTTOM

        return ResizeEdge.NONE

    def _update_cursor(self, edge: ResizeEdge) -> None:
        """Update cursor based on resize edge."""
        cursors = {
            ResizeEdge.NONE: Qt.CursorShape.ArrowCursor,
            ResizeEdge.TOP: Qt.CursorShape.SizeVerCursor,
            ResizeEdge.BOTTOM: Qt.CursorShape.SizeVerCursor,
            ResizeEdge.LEFT: Qt.CursorShape.SizeHorCursor,
            ResizeEdge.RIGHT: Qt.CursorShape.SizeHorCursor,
            ResizeEdge.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            ResizeEdge.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            ResizeEdge.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            ResizeEdge.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
        }
        self.setCursor(cursors.get(edge, Qt.CursorShape.ArrowCursor))

    def _do_resize(self, global_pos: QPoint) -> None:
        """
        Perform resize based on current edge and mouse position.

        Uses incremental approach like original Tkinter version:
        - Get CURRENT geometry each frame
        - Calculate dx/dy relative to current window position
        - Apply changes independently per axis
        """
        # Get current geometry (not initial - this is key!)
        x = self.x()
        y = self.y()
        w = self.width()
        h = self.height()

        # Calculate mouse position relative to window origin
        # This matches Tkinter's event.x_root - self.winfo_rootx()
        dx = global_pos.x() - x
        dy = global_pos.y() - y

        # East edge: width = mouse x position relative to window
        if self._resize_edge in (ResizeEdge.RIGHT, ResizeEdge.TOP_RIGHT, ResizeEdge.BOTTOM_RIGHT):
            w = max(self.MIN_SIZE, dx)

        # South edge: height = mouse y position relative to window
        if self._resize_edge in (ResizeEdge.BOTTOM, ResizeEdge.BOTTOM_LEFT, ResizeEdge.BOTTOM_RIGHT):
            h = max(self.MIN_SIZE, dy)

        # West edge: need to move x and adjust width
        if self._resize_edge in (ResizeEdge.LEFT, ResizeEdge.TOP_LEFT, ResizeEdge.BOTTOM_LEFT):
            new_w = w - dx
            if new_w >= self.MIN_SIZE:
                w = new_w
                x += dx
            else:
                # Clamp to minimum - don't move x
                w = self.MIN_SIZE

        # North edge: need to move y and adjust height
        if self._resize_edge in (ResizeEdge.TOP, ResizeEdge.TOP_LEFT, ResizeEdge.TOP_RIGHT):
            new_h = h - dy
            if new_h >= self.MIN_SIZE:
                h = new_h
                y += dy
            else:
                # Clamp to minimum - don't move y
                h = self.MIN_SIZE

        self.setGeometry(x, y, w, h)

    def capture_region(self) -> None:
        """
        Capture the screen region covered by this overlay.

        Uses PIL ImageGrab for better Windows multi-monitor support.
        Hides the overlay, captures the screen, then shows it again.
        Emits captureCompleted signal with the captured PIL Image.
        """
        if not self._hotkey_enabled:
            print("Hotkey is paused. Click toggle button to enable.")
            return

        # Get interior frame coordinates (the actual capture area)
        # Use window geometry plus border offset
        geo = self.geometry()
        border = self.BORDER_WIDTH

        x1 = geo.x() + border
        y1 = geo.y() + border
        x2 = geo.x() + geo.width() - border
        y2 = geo.y() + geo.height() - border

        # Hide overlay
        self.hide()

        # Force the hide to take effect
        QApplication.processEvents()

        # Small delay to ensure screen updates (like original's 50ms)
        QTimer.singleShot(50, lambda: self._do_capture(x1, y1, x2, y2))

    def _do_capture(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Perform the actual screen capture using PIL ImageGrab."""
        screenshot = None
        try:
            # Use PIL ImageGrab for better Windows/multi-monitor support
            try:
                screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2), all_screens=True)
            except TypeError:
                # Fallback for systems that don't support all_screens
                screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))

            if screenshot:
                # Emit the captured image as PIL Image
                self.captureCompleted.emit(screenshot)

        except Exception as e:
            print(f"Capture error: {e}")

        finally:
            # Show overlay again
            self.show()

    def get_capture_rect(self) -> Tuple[int, int, int, int]:
        """Get the capture region as (x, y, width, height)."""
        geo = self.geometry()
        return (geo.x(), geo.y(), geo.width(), geo.height())

    def set_capture_rect(self, x: int, y: int, width: int, height: int) -> None:
        """Set the capture region."""
        self.setGeometry(x, y, max(width, self.MIN_SIZE), max(height, self.MIN_SIZE))

    def save_geometry_string(self) -> str:
        """Save geometry as a string for settings persistence."""
        geo = self.geometry()
        return f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"

    def restore_geometry_string(self, geometry_str: str) -> bool:
        """
        Restore geometry from a string.

        Args:
            geometry_str: Format "WxH+X+Y" (e.g., "300x100+100+100")

        Returns:
            True if successfully restored
        """
        try:
            # Parse "WxH+X+Y" format
            parts = geometry_str.replace('x', '+').split('+')
            if len(parts) >= 4:
                w, h, x, y = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])

                # Validate position is on screen
                if self._is_position_valid(x, y, w, h):
                    self.setGeometry(x, y, max(w, self.MIN_SIZE), max(h, self.MIN_SIZE))
                    return True

        except (ValueError, IndexError):
            pass

        return False

    def _is_position_valid(self, x: int, y: int, w: int, h: int) -> bool:
        """Check if the given position is visible on any screen."""
        rect = QRect(x, y, w, h)
        for screen in QGuiApplication.screens():
            if screen.geometry().intersects(rect):
                return True
        return False


def pixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    """Convert QPixmap to PIL Image."""
    qimage = pixmap.toImage()
    qimage = qimage.convertToFormat(qimage.Format.Format_RGBA8888)

    width = qimage.width()
    height = qimage.height()

    ptr = qimage.bits()
    ptr.setsize(qimage.sizeInBytes())

    return Image.frombytes('RGBA', (width, height), bytes(ptr), 'raw', 'RGBA')
