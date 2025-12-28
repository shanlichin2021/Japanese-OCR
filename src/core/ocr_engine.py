"""
OCR Engine Wrapper - Singleton pattern for manga-ocr model management.

This module provides a thread-safe singleton wrapper around the manga-ocr library,
handling model loading, GPU/CPU fallback, and image processing.
"""

from __future__ import annotations
import threading
from typing import Optional, Callable, TYPE_CHECKING
from PIL import Image

from ..utils.logger import log_info, log_error, log_debug, log_warning

if TYPE_CHECKING:
    from manga_ocr import MangaOcr


class MangaOCRWrapper:
    """
    Singleton wrapper for manga-ocr model to manage heavy model loading.

    The model is loaded once and reused across all OCR operations.
    Thread-safe initialization ensures only one model instance exists.
    """

    _instance: Optional[MangaOCRWrapper] = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls) -> MangaOCRWrapper:
        """Thread-safe singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the OCR wrapper (only runs once due to singleton)."""
        if MangaOCRWrapper._initialized:
            return

        self._mocr: Optional[MangaOcr] = None
        self._is_loaded = False
        self._is_loading = False
        self._load_error: Optional[str] = None
        self._load_lock = threading.Lock()
        self._load_event = threading.Event()
        self._use_gpu = False

        MangaOCRWrapper._initialized = True

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded and ready."""
        return self._is_loaded

    @property
    def is_loading(self) -> bool:
        """Check if the model is currently being loaded."""
        return self._is_loading

    @property
    def load_error(self) -> Optional[str]:
        """Get any error that occurred during loading."""
        return self._load_error

    @property
    def uses_gpu(self) -> bool:
        """Check if the model is using GPU acceleration."""
        return self._use_gpu

    def load_model_async(self, callback: Optional[Callable[[bool, Optional[str]], None]] = None) -> None:
        """
        Load the manga-ocr model in a background thread.

        Args:
            callback: Optional function to call when loading completes.
                     Called with (success: bool, error_message: Optional[str])
        """
        if self._is_loaded or self._is_loading:
            if callback:
                callback(self._is_loaded, self._load_error)
            return

        def load_thread():
            self._load_model_sync()
            if callback:
                callback(self._is_loaded, self._load_error)

        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()

    def _load_model_sync(self) -> None:
        """Synchronously load the manga-ocr model."""
        with self._load_lock:
            if self._is_loaded:
                return

            self._is_loading = True
            self._load_error = None
            self._load_event.clear()  # Reset event for fresh load

            try:
                log_info("Loading manga-ocr model...")
                log_info("Note: First run may download model (~400MB). Please wait...")

                # Check for GPU availability
                try:
                    import torch
                    log_debug("Checking PyTorch GPU support...")
                    if torch.cuda.is_available():
                        self._use_gpu = True
                        log_info(f"CUDA available: {torch.cuda.get_device_name(0)}")
                    else:
                        log_info("CUDA not available, using CPU")
                except ImportError:
                    log_warning("PyTorch not found for GPU check")

                # Load the model
                log_debug("Importing manga_ocr module...")
                from manga_ocr import MangaOcr

                log_info("Initializing manga-ocr model (downloading if needed)...")
                self._mocr = MangaOcr()

                self._is_loaded = True
                log_info("manga-ocr model loaded successfully!")

            except ImportError as e:
                self._load_error = (
                    "manga-ocr is not installed.\n"
                    "Please run: pip install manga-ocr"
                )
                log_error(f"Import error: {e}")

            except RuntimeError as e:
                error_str = str(e)
                if "CUDA" in error_str or "GPU" in error_str:
                    self._load_error = (
                        f"GPU/CUDA error: {e}\n\n"
                        "Try installing CPU-only PyTorch:\n"
                        "  pip uninstall torch\n"
                        "  pip install torch --index-url https://download.pytorch.org/whl/cpu"
                    )
                else:
                    self._load_error = f"Runtime error loading model: {e}"
                log_error(f"Runtime error: {e}")

            except Exception as e:
                import platform
                if platform.system() == "Windows" and ("DLL" in str(e) or "WinError" in str(e)):
                    self._load_error = (
                        "A required system library is missing.\n\n"
                        "Solutions:\n"
                        "1. Install Microsoft Visual C++ Redistributable\n"
                        "2. Try CPU-only PyTorch:\n"
                        "   pip uninstall torch\n"
                        "   pip install torch --index-url https://download.pytorch.org/whl/cpu"
                    )
                else:
                    self._load_error = f"Unexpected error: {e}"
                log_error(f"Error loading model: {e}")

            finally:
                self._is_loading = False
                self._load_event.set()

    def wait_for_load(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for the model to finish loading.

        Args:
            timeout: Maximum seconds to wait (None = wait forever)

        Returns:
            True if model loaded successfully, False otherwise
        """
        self._load_event.wait(timeout)
        return self._is_loaded

    def perform_ocr(self, image: Image.Image) -> str:
        """
        Perform OCR on a PIL Image.

        Args:
            image: PIL Image to process (should be preprocessed)

        Returns:
            Extracted text as string, or empty string if none found

        Raises:
            RuntimeError: If model is not loaded
        """
        if not self._is_loaded:
            if self._load_error:
                raise RuntimeError(f"OCR model failed to load: {self._load_error}")
            raise RuntimeError("OCR model not loaded. Call load_model_async() first.")

        if self._mocr is None:
            raise RuntimeError("OCR model is None despite being marked as loaded")

        try:
            # Ensure image is RGB (manga-ocr requirement)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Run inference
            result = self._mocr(image)
            return result.strip() if result else ""

        except RuntimeError as e:
            error_str = str(e)
            # Handle CUDA out of memory
            if "out of memory" in error_str.lower():
                log_error("GPU out of memory during OCR inference")
                raise RuntimeError(
                    "GPU out of memory. Try:\n"
                    "1. Close other GPU-intensive applications\n"
                    "2. Use a smaller capture area\n"
                    "3. Switch to CPU-only PyTorch"
                )
            raise

    def unload_model(self) -> None:
        """Unload the model to free memory."""
        with self._load_lock:
            if self._mocr is not None:
                del self._mocr
                self._mocr = None

            self._is_loaded = False
            self._is_loading = False
            self._load_error = None
            self._load_event.clear()

            # Try to free GPU memory
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

            log_info("manga-ocr model unloaded")


# Convenience function to get the singleton instance
def get_ocr_engine() -> MangaOCRWrapper:
    """Get the singleton OCR engine instance."""
    return MangaOCRWrapper()
