"""
Image Operations - Advanced preprocessing pipelines for OCR accuracy.

This module provides multiple preprocessing modes optimized for Japanese text
recognition, particularly from manga and screen captures.
"""

from __future__ import annotations
from enum import Enum
from typing import Tuple
import numpy as np
from PIL import Image

# Try to import OpenCV, fall back gracefully
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("Warning: opencv-python-headless not installed. Advanced preprocessing disabled.")


class PreprocessingMode(Enum):
    """Available preprocessing modes."""
    NONE = "none"           # Recommended: manga-ocr handles everything
    MINIMAL = "minimal"     # Light contrast enhancement
    ENHANCED = "enhanced"   # Balanced: upscaling + contrast + sharpening
    ADVANCED = "advanced"   # Full OpenCV pipeline with adaptive thresholding


# Default parameters
UPSCALE_FACTOR = 2.0
ADAPTIVE_BLOCK_SIZE = 11
ADAPTIVE_C = 2
DENOISE_STRENGTH = 10
MAX_DIMENSION = 2048
MIN_DIMENSION = 32


def preprocess_image(
    image: Image.Image,
    mode: PreprocessingMode = PreprocessingMode.NONE
) -> Image.Image:
    """
    Preprocess an image for OCR based on the selected mode.

    Args:
        image: PIL Image to preprocess
        mode: Preprocessing mode to use

    Returns:
        Preprocessed PIL Image in RGB format
    """
    if mode == PreprocessingMode.NONE:
        return preprocess_none(image)
    elif mode == PreprocessingMode.MINIMAL:
        return preprocess_minimal(image)
    elif mode == PreprocessingMode.ENHANCED:
        return preprocess_enhanced(image)
    elif mode == PreprocessingMode.ADVANCED:
        return preprocess_advanced(image)
    else:
        return preprocess_none(image)


def preprocess_none(image: Image.Image) -> Image.Image:
    """
    No preprocessing - just ensure RGB format.

    RECOMMENDED MODE: manga-ocr is trained to handle:
    - Low quality images
    - Text overlaid on images
    - Various fonts and furigana
    - Both vertical and horizontal text

    The model's robustness means preprocessing is often unnecessary.
    """
    if image.mode != 'RGB':
        return image.convert('RGB')
    return image


def preprocess_minimal(image: Image.Image) -> Image.Image:
    """
    Minimal preprocessing with light contrast enhancement.

    Good for slightly faded or low-contrast screenshots.
    """
    from PIL import ImageEnhance

    # Ensure RGB
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # Light contrast boost
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.2)

    return image


def preprocess_enhanced(image: Image.Image) -> Image.Image:
    """
    Enhanced preprocessing with upscaling and sharpening.

    Good balance between speed and accuracy for most screen captures.
    Uses Lanczos resampling for high-quality upscaling.
    """
    from PIL import ImageEnhance, ImageFilter

    # Ensure RGB
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # Upscale by 2x using Lanczos interpolation
    width, height = image.size
    new_size = (int(width * UPSCALE_FACTOR), int(height * UPSCALE_FACTOR))
    image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Moderate contrast enhancement
    contrast_enhancer = ImageEnhance.Contrast(image)
    image = contrast_enhancer.enhance(1.4)

    # Sharpness enhancement for better character definition
    sharpness_enhancer = ImageEnhance.Sharpness(image)
    image = sharpness_enhancer.enhance(1.3)

    return image


def preprocess_advanced(image: Image.Image) -> Image.Image:
    """
    Advanced OpenCV-based preprocessing pipeline.

    Full pipeline as specified in the research document:
    1. Grayscale conversion
    2. 2x Lanczos upscaling
    3. Adaptive Gaussian thresholding
    4. Non-local means denoising

    Best for challenging images with complex backgrounds or low quality.
    """
    if not OPENCV_AVAILABLE:
        print("OpenCV not available, falling back to enhanced mode")
        return preprocess_enhanced(image)

    # Convert PIL to OpenCV format (RGB -> BGR)
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img_cv = img_array

    # Step 1: Convert to grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Step 2: Upscale by 2x using Lanczos interpolation
    height, width = gray.shape
    new_width = int(width * UPSCALE_FACTOR)
    new_height = int(height * UPSCALE_FACTOR)
    upscaled = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)

    # Step 3: Adaptive Gaussian thresholding
    # This handles varying background brightness common in manga
    binary = cv2.adaptiveThreshold(
        upscaled,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        ADAPTIVE_BLOCK_SIZE,
        ADAPTIVE_C
    )

    # Step 4: Non-local means denoising
    # Removes noise while preserving edges
    denoised = cv2.fastNlMeansDenoising(binary, None, DENOISE_STRENGTH, 7, 21)

    # Convert back to PIL RGB format (manga-ocr requirement)
    result = Image.fromarray(denoised).convert('RGB')

    return result


def optimize_image_size(image: Image.Image, target_height: int = 64) -> Image.Image:
    """
    Optimize image size for OCR performance.

    manga-ocr works best with text at approximately 32-64px character height.
    This function scales images to match that target.

    Args:
        image: Input PIL Image
        target_height: Target character height in pixels

    Returns:
        Resized image
    """
    width, height = image.size

    # Estimate character height (rough heuristic for Japanese text)
    # Assumes text fills roughly 1/5 to 1/10 of the capture height
    estimated_char_height = min(width, height) / 8

    # Downscale very large images
    if max(width, height) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(width, height)
        new_size = (int(width * ratio), int(height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        width, height = new_size

    # Upscale if characters are too small
    if estimated_char_height < MIN_DIMENSION:
        scale = target_height / estimated_char_height
        scale = min(scale, 3.0)  # Cap at 3x to avoid excessive scaling
        new_size = (int(width * scale), int(height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    return image


def pil_to_cv2(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV BGR format."""
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    return img_array


def cv2_to_pil(img_cv: np.ndarray) -> Image.Image:
    """Convert OpenCV BGR image to PIL RGB format."""
    if len(img_cv.shape) == 3:
        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    else:
        img_rgb = img_cv
    return Image.fromarray(img_rgb)


def get_available_modes() -> list[PreprocessingMode]:
    """Get list of available preprocessing modes based on installed packages."""
    modes = [
        PreprocessingMode.NONE,
        PreprocessingMode.MINIMAL,
        PreprocessingMode.ENHANCED,
    ]

    if OPENCV_AVAILABLE:
        modes.append(PreprocessingMode.ADVANCED)

    return modes


def mode_description(mode: PreprocessingMode) -> str:
    """Get human-readable description of a preprocessing mode."""
    descriptions = {
        PreprocessingMode.NONE: "None (Recommended for manga-ocr)",
        PreprocessingMode.MINIMAL: "Minimal (Light contrast boost)",
        PreprocessingMode.ENHANCED: "Enhanced (Upscale + sharpen)",
        PreprocessingMode.ADVANCED: "Advanced (Full OpenCV pipeline)",
    }
    return descriptions.get(mode, str(mode.value))
