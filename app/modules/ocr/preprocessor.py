"""
AegisClaim AI - Image Preprocessor
OpenCV-based preprocessing for improving OCR accuracy on scanned documents.
"""
import logging
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger("aegisclaim.ocr.preprocessor")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available. Image preprocessing will be limited.")

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ImagePreprocessor:
    """
    Preprocesses document images to improve OCR accuracy.
    Handles grayscale conversion, denoising, deskewing, and thresholding.
    """

    @staticmethod
    def preprocess(image_path: str, language: str = "eng") -> "Image.Image":
        """
        Full preprocessing pipeline for a document image.
        
        Args:
            image_path: Path to the image file
            language: OCR language (affects some preprocessing choices)
            
        Returns:
            Preprocessed PIL Image ready for OCR
        """
        if CV2_AVAILABLE:
            return ImagePreprocessor._preprocess_opencv(image_path, language)
        elif PIL_AVAILABLE:
            return ImagePreprocessor._preprocess_pil(image_path)
        else:
            raise RuntimeError("Neither OpenCV nor PIL available for image preprocessing")

    @staticmethod
    def _preprocess_opencv(image_path: str, language: str = "eng") -> "Image.Image":
        """Advanced preprocessing using OpenCV."""
        # Read image
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Deskew
        gray = ImagePreprocessor._deskew(gray)

        # Noise removal
        denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

        # Adaptive threshold - works better for documents with varying lighting
        # Use different block sizes for different scripts
        block_size = 15
        if language in ("chi_sim", "jpn", "kor"):
            block_size = 21  # Larger block for CJK characters
        elif language in ("ara", "hin", "ben", "tam", "tel"):
            block_size = 17  # Medium block for complex scripts

        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, block_size, 8
        )

        # Morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        # Slight sharpening
        sharpen_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(cleaned, -1, sharpen_kernel)

        # Convert back to PIL Image
        pil_image = Image.fromarray(sharpened)
        return pil_image

    @staticmethod
    def _preprocess_pil(image_path: str) -> "Image.Image":
        """Basic preprocessing using PIL only."""
        img = Image.open(image_path)

        # Convert to grayscale
        img = img.convert('L')

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)

        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)

        # Apply threshold
        img = img.point(lambda x: 0 if x < 128 else 255, '1')
        img = img.convert('L')

        return img

    @staticmethod
    def _deskew(image: np.ndarray) -> np.ndarray:
        """Correct skew in scanned documents."""
        try:
            coords = np.column_stack(np.where(image > 0))
            if len(coords) < 10:
                return image
            angle = cv2.minAreaRect(coords)[-1]

            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            # Only correct if skew is significant but not too extreme
            if abs(angle) > 0.5 and abs(angle) < 15:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    image, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
                return rotated
        except Exception as e:
            logger.warning(f"Deskew failed: {e}")

        return image

    @staticmethod
    def detect_tables(image_path: str) -> list[dict]:
        """
        Detect table regions in a document image.
        Returns bounding boxes of detected tables.
        """
        if not CV2_AVAILABLE:
            return []

        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return []

        # Binary threshold
        _, binary = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY_INV)

        # Detect horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

        # Detect vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

        # Combine
        table_mask = cv2.add(horizontal, vertical)

        # Find contours
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        tables = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 100 and h > 50:  # Minimum table size
                tables.append({
                    "x": int(x), "y": int(y),
                    "width": int(w), "height": int(h)
                })

        return sorted(tables, key=lambda t: t["y"])
