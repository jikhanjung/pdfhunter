"""Image preprocessing for OCR."""

from typing import Literal

import cv2
import numpy as np
from PIL import Image


class ImagePreprocessor:
    """Preprocessor for OCR images."""

    def __init__(
        self,
        grayscale: bool = True,
        denoise: bool = True,
        deskew: bool = False,
        threshold: Literal["none", "binary", "adaptive"] = "none",
    ):
        """Initialize preprocessor.

        Args:
            grayscale: Convert to grayscale
            denoise: Apply mild denoising
            deskew: Correct image skew
            threshold: Thresholding method
        """
        self.grayscale = grayscale
        self.denoise = denoise
        self.deskew = deskew
        self.threshold = threshold

    def process(self, image: Image.Image) -> Image.Image:
        """Process image for OCR.

        Args:
            image: PIL Image to process

        Returns:
            Processed PIL Image
        """
        # Convert PIL to OpenCV format
        img = np.array(image)

        # Convert RGB to BGR if needed
        if len(img.shape) == 3 and img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # Grayscale conversion
        if self.grayscale and len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Denoising
        if self.denoise:
            if len(img.shape) == 2:
                img = cv2.fastNlMeansDenoising(img, h=10)
            else:
                img = cv2.fastNlMeansDenoisingColored(img, h=10)

        # Deskew
        if self.deskew:
            img = self._deskew(img)

        # Thresholding
        if self.threshold == "binary":
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif self.threshold == "adaptive":
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.adaptiveThreshold(
                img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

        # Convert back to PIL
        if len(img.shape) == 2:
            return Image.fromarray(img)
        else:
            return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """Correct image skew.

        Args:
            img: OpenCV image

        Returns:
            Deskewed image
        """
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Detect lines using Hough transform
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10
        )

        if lines is None or len(lines) == 0:
            return img

        # Calculate angles
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 != 0:
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                # Only consider near-horizontal lines
                if abs(angle) < 45:
                    angles.append(angle)

        if not angles:
            return img

        # Median angle
        median_angle = np.median(angles)

        # Rotate image
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(
            img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

        return rotated


def create_default_preprocessor() -> ImagePreprocessor:
    """Create preprocessor with default settings for bibliographic OCR."""
    return ImagePreprocessor(
        grayscale=True,
        denoise=True,
        deskew=False,  # Only enable if needed
        threshold="none",  # Avoid over-processing
    )
