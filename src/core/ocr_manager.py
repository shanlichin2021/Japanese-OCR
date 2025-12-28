"""
OCR Manager - Unified interface for multiple OCR engines.

This module provides a manager class that can switch between different
OCR engines (manga-ocr, PaddleOCR) while providing a consistent interface.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Callable
from PIL import Image

from ..utils.logger import log_info, log_error, log_debug


class OCREngine(Enum):
    """Available OCR engines."""
    MANGA_OCR = "manga_ocr"
    PADDLE_OCR = "paddle_ocr"


# Engine display names and descriptions
ENGINE_INFO = {
    OCREngine.MANGA_OCR: {
        "name": "manga-ocr",
        "description": "Vision Encoder-Decoder model optimized for manga/games. Best accuracy for stylized text.",
    },
    OCREngine.PADDLE_OCR: {
        "name": "PaddleOCR (japan_PP-OCRv3)",
        "description": "Lightweight model (8.8MB). Faster inference, good for general Japanese text.",
    },
}


def get_engine_name(engine: OCREngine) -> str:
    """Get display name for an engine."""
    return ENGINE_INFO.get(engine, {}).get("name", engine.value)


def get_engine_description(engine: OCREngine) -> str:
    """Get description for an engine."""
    return ENGINE_INFO.get(engine, {}).get("description", "")


class OCRManager:
    """
    Unified manager for OCR engines.

    Provides a consistent interface for loading models, performing OCR,
    and switching between different engines.
    """

    def __init__(self) -> None:
        """Initialize the OCR manager."""
        self._current_engine = OCREngine.MANGA_OCR
        self._manga_ocr = None
        self._paddle_ocr = None
        self._active_engine = None

    @property
    def current_engine(self) -> OCREngine:
        """Get the currently selected engine."""
        return self._current_engine

    @property
    def is_loaded(self) -> bool:
        """Check if the current engine is loaded."""
        engine = self._get_engine_instance()
        return engine is not None and engine.is_loaded

    @property
    def is_loading(self) -> bool:
        """Check if the current engine is loading."""
        engine = self._get_engine_instance()
        return engine is not None and engine.is_loading

    @property
    def load_error(self) -> Optional[str]:
        """Get load error from current engine."""
        engine = self._get_engine_instance()
        return engine.load_error if engine else None

    @property
    def uses_gpu(self) -> bool:
        """Check if current engine uses GPU."""
        engine = self._get_engine_instance()
        return engine.uses_gpu if engine else False

    def _get_engine_instance(self):
        """Get the current engine instance."""
        if self._current_engine == OCREngine.MANGA_OCR:
            if self._manga_ocr is None:
                from .ocr_engine import get_ocr_engine
                self._manga_ocr = get_ocr_engine()
            return self._manga_ocr
        elif self._current_engine == OCREngine.PADDLE_OCR:
            if self._paddle_ocr is None:
                from .paddle_ocr_engine import get_paddle_ocr_engine
                self._paddle_ocr = get_paddle_ocr_engine()
            return self._paddle_ocr
        return None

    def set_engine(self, engine: OCREngine) -> None:
        """
        Set the active OCR engine.

        Note: This doesn't automatically load the new engine.
        Call load_model_async() after changing engines.

        Args:
            engine: The engine to use
        """
        if engine != self._current_engine:
            log_info(f"Switching OCR engine from {self._current_engine.value} to {engine.value}")
            self._current_engine = engine

    def load_model_async(self, callback: Optional[Callable[[bool, Optional[str]], None]] = None) -> None:
        """
        Load the current engine's model asynchronously.

        Args:
            callback: Optional function called with (success, error_message)
        """
        engine = self._get_engine_instance()
        if engine:
            log_info(f"Loading {get_engine_name(self._current_engine)} model...")
            engine.load_model_async(callback)
        elif callback:
            callback(False, "No engine available")

    def perform_ocr(self, image: Image.Image) -> str:
        """
        Perform OCR using the current engine.

        Args:
            image: PIL Image to process

        Returns:
            Extracted text

        Raises:
            RuntimeError: If engine not loaded or OCR fails
        """
        engine = self._get_engine_instance()
        if engine is None:
            raise RuntimeError("No OCR engine available")

        if not engine.is_loaded:
            raise RuntimeError(f"{get_engine_name(self._current_engine)} model not loaded")

        return engine.perform_ocr(image)

    def unload_current(self) -> None:
        """Unload the current engine to free memory."""
        engine = self._get_engine_instance()
        if engine and engine.is_loaded:
            log_info(f"Unloading {get_engine_name(self._current_engine)} model...")
            engine.unload_model()

    def unload_all(self) -> None:
        """Unload all engines to free memory."""
        if self._manga_ocr and self._manga_ocr.is_loaded:
            self._manga_ocr.unload_model()
        if self._paddle_ocr and self._paddle_ocr.is_loaded:
            self._paddle_ocr.unload_model()


# Global manager instance
_manager: Optional[OCRManager] = None


def get_ocr_manager() -> OCRManager:
    """Get the global OCR manager instance."""
    global _manager
    if _manager is None:
        _manager = OCRManager()
    return _manager
