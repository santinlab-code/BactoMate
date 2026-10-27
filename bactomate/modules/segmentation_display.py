"""Display-only cell outlines; label masks and scientific measurements are untouched."""
from __future__ import annotations

import numpy as np

DEFAULT_OUTLINE_COLOR = (0, 255, 0)


def label_outlines(mask: np.ndarray) -> np.ndarray:
    """One-pixel inner edges, including touching labels and image borders."""
    labels = np.asarray(mask)
    if labels.ndim != 2:
        raise ValueError("Expected a 2D label mask")
    padded = np.pad(labels, 1, mode="constant")
    edge = ((labels != padded[:-2, 1:-1]) |
            (labels != padded[2:, 1:-1]) |
            (labels != padded[1:-1, :-2]) |
            (labels != padded[1:-1, 2:]))
    return (labels > 0) & edge


def segmentation_outline_rgb(image, mask, color=DEFAULT_OUTLINE_COLOR):
    """Draw opaque outlines on grayscale, retaining cell interiors/background."""
    image = np.asarray(image)
    mask = np.asarray(mask)
    if image.ndim != 2 or image.shape != mask.shape:
        raise ValueError("Image and label mask must have matching 2D shapes")
    rgb_color = np.asarray(color)
    if rgb_color.shape != (3,) or not np.all(np.isfinite(rgb_color)) or np.any((rgb_color < 0) | (rgb_color > 255)):
        raise ValueError("Outline color must contain three RGB values in [0, 255]")
    if image.dtype == np.uint8:
        gray = image
    else:
        values = np.nan_to_num(image.astype(np.float64))
        lo, hi = values.min(), values.max()
        gray = ((values - lo) / (hi - lo) * 255).clip(0, 255).astype(np.uint8) if hi > lo else np.zeros(image.shape, np.uint8)
    rgb = np.repeat(gray[..., None], 3, axis=2)
    rgb[label_outlines(mask)] = rgb_color.astype(np.uint8)
    return rgb
