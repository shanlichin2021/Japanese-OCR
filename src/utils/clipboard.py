"""
Clipboard Utilities - Cross-platform clipboard operations.

Uses Qt's QClipboard for better integration and MIME type support,
with pyperclip as fallback.
"""

from __future__ import annotations
from typing import Optional
from PIL import Image
import io


class ClipboardManager:
    """
    Manages clipboard operations with Qt and pyperclip support.

    Prefers Qt's QClipboard when available for better integration
    and MIME type support (text + image simultaneously).
    """

    def __init__(self, use_qt: bool = True) -> None:
        """
        Initialize the clipboard manager.

        Args:
            use_qt: Whether to prefer Qt clipboard (requires QApplication)
        """
        self._use_qt = use_qt
        self._qt_clipboard = None

    def _get_qt_clipboard(self):
        """Get Qt clipboard instance if available."""
        if not self._use_qt:
            return None

        if self._qt_clipboard is not None:
            return self._qt_clipboard

        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QClipboard

            app = QApplication.instance()
            if app is not None:
                self._qt_clipboard = app.clipboard()
                return self._qt_clipboard
        except ImportError:
            pass

        return None

    def copy_text(self, text: str) -> bool:
        """
        Copy text to clipboard.

        Args:
            text: Text to copy

        Returns:
            True if successful
        """
        # Try Qt first
        qt_clip = self._get_qt_clipboard()
        if qt_clip is not None:
            try:
                qt_clip.setText(text)
                return True
            except Exception as e:
                print(f"Qt clipboard error: {e}")

        # Fall back to pyperclip
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except Exception as e:
            print(f"pyperclip error: {e}")
            return False

    def copy_image(self, image: Image.Image) -> bool:
        """
        Copy image to clipboard.

        Args:
            image: PIL Image to copy

        Returns:
            True if successful
        """
        qt_clip = self._get_qt_clipboard()
        if qt_clip is not None:
            try:
                from PyQt6.QtGui import QImage, QPixmap

                # Convert PIL Image to QImage
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')

                data = image.tobytes('raw', 'RGBA')
                qimage = QImage(
                    data,
                    image.width,
                    image.height,
                    QImage.Format.Format_RGBA8888
                )
                qt_clip.setPixmap(QPixmap.fromImage(qimage))
                return True
            except Exception as e:
                print(f"Qt image clipboard error: {e}")

        return False

    def copy_text_and_image(self, text: str, image: Image.Image) -> bool:
        """
        Copy both text and image to clipboard using MIME types.

        Args:
            text: Text to copy
            image: PIL Image to copy

        Returns:
            True if successful (at least text was copied)
        """
        qt_clip = self._get_qt_clipboard()
        if qt_clip is not None:
            try:
                from PyQt6.QtCore import QMimeData
                from PyQt6.QtGui import QImage, QPixmap

                mime_data = QMimeData()

                # Add text
                mime_data.setText(text)

                # Add image
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')

                data = image.tobytes('raw', 'RGBA')
                qimage = QImage(
                    data,
                    image.width,
                    image.height,
                    QImage.Format.Format_RGBA8888
                )
                mime_data.setImageData(qimage)

                qt_clip.setMimeData(mime_data)
                return True
            except Exception as e:
                print(f"Qt MIME clipboard error: {e}")

        # Fall back to text only
        return self.copy_text(text)

    def get_text(self) -> Optional[str]:
        """
        Get text from clipboard.

        Returns:
            Clipboard text or None if empty/unavailable
        """
        qt_clip = self._get_qt_clipboard()
        if qt_clip is not None:
            try:
                text = qt_clip.text()
                return text if text else None
            except Exception:
                pass

        try:
            import pyperclip
            text = pyperclip.paste()
            return text if text else None
        except Exception:
            return None

    def get_image(self) -> Optional[Image.Image]:
        """
        Get image from clipboard.

        Returns:
            PIL Image or None if no image in clipboard
        """
        qt_clip = self._get_qt_clipboard()
        if qt_clip is not None:
            try:
                from PyQt6.QtGui import QImage

                qimage = qt_clip.image()
                if qimage.isNull():
                    return None

                # Convert QImage to PIL Image
                qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
                width = qimage.width()
                height = qimage.height()

                ptr = qimage.bits()
                ptr.setsize(qimage.sizeInBytes())

                image = Image.frombytes(
                    'RGBA',
                    (width, height),
                    bytes(ptr),
                    'raw',
                    'RGBA'
                )
                return image
            except Exception as e:
                print(f"Qt image read error: {e}")

        return None


# Global clipboard manager instance
_clipboard_manager: Optional[ClipboardManager] = None


def get_clipboard() -> ClipboardManager:
    """Get the global clipboard manager instance."""
    global _clipboard_manager
    if _clipboard_manager is None:
        _clipboard_manager = ClipboardManager()
    return _clipboard_manager


def copy_text(text: str) -> bool:
    """Convenience function to copy text to clipboard."""
    return get_clipboard().copy_text(text)


def copy_image(image: Image.Image) -> bool:
    """Convenience function to copy image to clipboard."""
    return get_clipboard().copy_image(image)


def get_text() -> Optional[str]:
    """Convenience function to get text from clipboard."""
    return get_clipboard().get_text()
