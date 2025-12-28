"""
PaddleOCR Engine Wrapper - Japanese OCR model support.

This module provides a wrapper around PaddleOCR for Japanese text recognition.
Updated for PaddleOCR 3.x API which uses predict() method instead of ocr().

Note: PaddleOCR 3.x introduced significant API changes from 2.x.
See: https://pypi.org/project/paddleocr/
"""

from __future__ import annotations
import threading
from typing import Optional, List, Tuple, Callable
from PIL import Image
import numpy as np

from ..utils.logger import log_info, log_error, log_debug, log_warning


class PaddleOCRWrapper:
    """
    Wrapper for PaddleOCR with Japanese language support.

    Uses PaddleOCR 3.x API with Japanese recognition model.
    Supports both GPU and CPU inference.
    """

    _instance: Optional[PaddleOCRWrapper] = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls) -> PaddleOCRWrapper:
        """Thread-safe singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the PaddleOCR wrapper (only runs once due to singleton)."""
        if PaddleOCRWrapper._initialized:
            return

        self._ocr = None
        self._is_loaded = False
        self._is_loading = False
        self._load_error: Optional[str] = None
        self._load_lock = threading.Lock()
        self._load_event = threading.Event()
        self._use_gpu = False

        PaddleOCRWrapper._initialized = True

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
        Load the PaddleOCR model in a background thread.

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
        """Synchronously load the PaddleOCR model."""
        with self._load_lock:
            if self._is_loaded:
                return

            self._is_loading = True
            self._load_error = None
            self._load_event.clear()  # Reset event for fresh load

            try:
                log_info("Loading PaddleOCR japan_PP-OCRv3 model...")
                log_info("Note: First run may download models (~100MB). Please wait...")

                # Check for GPU availability
                try:
                    import paddle
                    log_debug("Checking PaddlePaddle GPU support...")
                    if paddle.device.is_compiled_with_cuda():
                        # Check if GPU is actually available
                        gpu_count = paddle.device.cuda.device_count()
                        if gpu_count > 0:
                            self._use_gpu = True
                            log_info(f"PaddlePaddle CUDA available, GPU count: {gpu_count}")
                        else:
                            log_info("PaddlePaddle compiled with CUDA but no GPU found, using CPU")
                    else:
                        log_info("PaddlePaddle CPU version, using CPU")
                except Exception as e:
                    log_debug(f"GPU check failed: {e}, defaulting to CPU")

                # Import and initialize PaddleOCR
                log_debug("Importing PaddleOCR module...")
                from paddleocr import PaddleOCR

                # Configure for Japanese OCR
                # PaddleOCR 3.x API - uses predict() method
                log_info("Initializing PaddleOCR (downloading models if needed)...")

                # PaddleOCR 3.x initialization parameters
                # See: https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html
                self._ocr = PaddleOCR(
                    lang='japan',  # Japanese recognition model
                    use_doc_orientation_classify=False,  # Disable document orientation (not needed for screen capture)
                    use_doc_unwarping=False,  # Disable document unwarping
                    use_textline_orientation=True,  # Enable for vertical text support
                )

                self._is_loaded = True
                log_info("PaddleOCR Japanese model loaded successfully!")

            except ImportError as e:
                self._load_error = (
                    "PaddleOCR is not installed.\n"
                    "Please run: pip install paddleocr"
                )
                log_error(f"Import error: {e}")

            except Exception as e:
                error_str = str(e)
                if "paddle" in error_str.lower():
                    self._load_error = (
                        f"PaddlePaddle error: {e}\n\n"
                        "Try reinstalling PaddlePaddle:\n"
                        "  pip uninstall paddlepaddle\n"
                        "  pip install paddlepaddle"
                    )
                else:
                    self._load_error = f"Error loading PaddleOCR: {e}"
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
            image: PIL Image to process

        Returns:
            Extracted text as string, or empty string if none found

        Raises:
            RuntimeError: If model is not loaded
        """
        if not self._is_loaded:
            if self._load_error:
                raise RuntimeError(f"OCR model failed to load: {self._load_error}")
            raise RuntimeError("OCR model not loaded. Call load_model_async() first.")

        if self._ocr is None:
            raise RuntimeError("OCR model is None despite being marked as loaded")

        try:
            # Convert PIL Image to numpy array (PaddleOCR expects numpy/path)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            img_array = np.array(image)

            log_debug(f"Running PaddleOCR on image shape: {img_array.shape}")

            # PaddleOCR 3.x uses predict() method instead of ocr()
            # Returns a list of Result objects
            results = self._ocr.predict(img_array)

            log_debug(f"PaddleOCR result count: {len(results) if results else 0}")

            if results is None or len(results) == 0:
                log_debug("PaddleOCR returned no results")
                return ""

            # Extract text from PaddleOCR 3.x Result objects
            # Each Result has: rec_texts (list of strings), rec_scores (list of floats)
            texts = []
            for idx, res in enumerate(results):
                log_debug(f"Processing result {idx}: {type(res)}")

                # Try to access rec_texts attribute (PaddleOCR 3.x structure)
                if hasattr(res, 'rec_texts') and res.rec_texts:
                    rec_texts = res.rec_texts
                    rec_scores = getattr(res, 'rec_scores', [1.0] * len(rec_texts))

                    for text, score in zip(rec_texts, rec_scores):
                        log_debug(f"Found text: '{text}' with confidence: {score:.2f}")
                        if text and score > 0.3:
                            texts.append(text)
                            log_debug(f"Accepted: '{text}' (conf: {score:.2f})")

                # Fallback: try dictionary-style access
                elif isinstance(res, dict):
                    if 'rec_texts' in res:
                        rec_texts = res['rec_texts']
                        rec_scores = res.get('rec_scores', [1.0] * len(rec_texts))
                        for text, score in zip(rec_texts, rec_scores):
                            if text and score > 0.3:
                                texts.append(text)
                                log_debug(f"Accepted (dict): '{text}' (conf: {score:.2f})")

                # Legacy fallback for older API structure [[box, (text, conf)], ...]
                elif isinstance(res, list):
                    log_debug(f"Trying legacy result parsing for list: {res}")
                    for detection in res:
                        if detection is None or not isinstance(detection, (list, tuple)):
                            continue
                        if len(detection) >= 2:
                            text_info = detection[1]
                            if isinstance(text_info, (list, tuple)) and len(text_info) >= 1:
                                text = text_info[0]
                                confidence = text_info[1] if len(text_info) > 1 else 1.0
                                if text and confidence > 0.3:
                                    texts.append(str(text))
                                    log_debug(f"Accepted (legacy): '{text}' (conf: {confidence:.2f})")

                else:
                    log_debug(f"Unknown result type: {type(res)}, value: {res}")

            # Join all detected text
            full_text = ''.join(texts)
            log_debug(f"Final extracted text: '{full_text}'")
            return full_text.strip()

        except Exception as e:
            log_error(f"PaddleOCR inference error: {e}")
            raise RuntimeError(f"OCR inference failed: {e}")

    def unload_model(self) -> None:
        """Unload the model to free memory."""
        with self._load_lock:
            if self._ocr is not None:
                del self._ocr
                self._ocr = None

            self._is_loaded = False
            self._is_loading = False
            self._load_error = None
            self._load_event.clear()

            # Try to free GPU memory
            try:
                import paddle
                paddle.device.cuda.empty_cache()
            except Exception:
                pass

            log_info("PaddleOCR model unloaded")


# Convenience function to get the singleton instance
def get_paddle_ocr_engine() -> PaddleOCRWrapper:
    """Get the singleton PaddleOCR engine instance."""
    return PaddleOCRWrapper()
