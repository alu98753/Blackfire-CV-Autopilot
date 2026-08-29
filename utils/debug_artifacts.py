"""Centralized, project-local storage for debug image artifacts."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEBUG_ARTIFACT_DIR = PROJECT_ROOT / "scratch" / "debug"
DEBUG_FILENAME_PREFIX = "debug_"
DEBUG_IMAGE_SUFFIX = ".png"


def debug_image_path(filename: str) -> Path:
    """Return the managed path for a debug PNG, rejecting unsafe names."""
    path = Path(filename)
    if path.name != filename or not filename.startswith(DEBUG_FILENAME_PREFIX) or path.suffix.lower() != DEBUG_IMAGE_SUFFIX:
        raise ValueError("Debug image filenames must be a basename matching debug_*.png")
    return DEBUG_ARTIFACT_DIR / path.name


def write_debug_image(filename: str, image: np.ndarray) -> bool:
    """Write an image under scratch/debug without interrupting runtime flows."""
    try:
        output_path = debug_image_path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output_path), image):
            logging.warning("[DebugArtifacts] OpenCV could not write debug image: %s", output_path)
            return False
        logging.info("[DebugArtifacts] Debug image written to: %s", output_path)
        return True
    except (OSError, ValueError, cv2.error) as exc:
        logging.warning("[DebugArtifacts] Failed to write %s: %s", filename, exc)
        return False
