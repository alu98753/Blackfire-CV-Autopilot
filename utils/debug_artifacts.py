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
DEFAULT_MAX_DEBUG_IMAGES = 40
DEFAULT_MAX_DEBUG_BYTES = 200 * 1024 * 1024


def debug_image_path(filename: str) -> Path:
    """Return the managed path for a debug PNG, rejecting unsafe names."""
    path = Path(filename)
    if path.name != filename or not filename.startswith(DEBUG_FILENAME_PREFIX) or path.suffix.lower() != DEBUG_IMAGE_SUFFIX:
        raise ValueError("Debug image filenames must be a basename matching debug_*.png")
    return DEBUG_ARTIFACT_DIR / path.name


def prune_debug_images(
    max_images: int = DEFAULT_MAX_DEBUG_IMAGES,
    max_bytes: int = DEFAULT_MAX_DEBUG_BYTES,
) -> None:
    """Bound disposable diagnostics without allowing cleanup failures to affect play."""
    try:
        files = sorted(
            (path for path in DEBUG_ARTIFACT_DIR.glob(f"{DEBUG_FILENAME_PREFIX}*{DEBUG_IMAGE_SUFFIX}") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        total_bytes = 0
        for index, path in enumerate(files):
            size = path.stat().st_size
            if index >= max_images or total_bytes + size > max_bytes:
                try:
                    path.unlink()
                except OSError as exc:
                    logging.debug("[DebugArtifacts] Could not prune %s: %s", path, exc)
            else:
                total_bytes += size
    except OSError as exc:
        logging.debug("[DebugArtifacts] Could not inspect debug artifacts: %s", exc)


def write_debug_image(filename: str, image: np.ndarray) -> bool:
    """Write an image under scratch/debug without interrupting runtime flows."""
    try:
        output_path = debug_image_path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output_path), image):
            logging.warning("[DebugArtifacts] OpenCV could not write debug image: %s", output_path)
            return False
        logging.info("[DebugArtifacts] Debug image written to: %s", output_path)
        prune_debug_images()
        return True
    except (OSError, ValueError, cv2.error) as exc:
        logging.warning("[DebugArtifacts] Failed to write %s: %s", filename, exc)
        return False
