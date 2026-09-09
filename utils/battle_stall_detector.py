"""Health bar stall detection for battle scene.

Provides a pure, stateless perception helper to extract a lightweight
signature of the ally/enemy health bar region to detect stalled battles.
"""

from typing import Any
import cv2
import numpy as np


def extract_health_bar_signature(screen_img: Any) -> int:
    """Extract a lightweight red-pixel count signature from the battle health-bar ROI.
    
    In 1920x1080 (or any scaled game view), the combat health bars sit at
    approximately 62% to 70% of the screen height across the horizontal width.
    
    Returns:
        int: Total number of active red health bar pixels in the ROI.
             If screen_img is invalid, returns -1.
    """
    if screen_img is None or not hasattr(screen_img, "shape") or len(screen_img.shape) < 2:
        return -1

    height, width = screen_img.shape[:2]
    # Scoped ROI: bottom combat strip where health bars reside
    y_start = int(height * 0.60)
    y_end = int(height * 0.72)
    roi = screen_img[y_start:y_end, :]

    if roi.size == 0:
        return -1

    # Convert to HSV to isolate the characteristic combat health bar red
    try:
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        # Red spans both ends of the Hue circle: [0, 10] and [170, 180]
        lower_red1 = np.array([0, 120, 120], dtype=np.uint8)
        upper_red1 = np.array([10, 255, 255], dtype=np.uint8)
        lower_red2 = np.array([170, 120, 120], dtype=np.uint8)
        upper_red2 = np.array([180, 255, 255], dtype=np.uint8)

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        return int(cv2.countNonZero(red_mask))
    except Exception:
        return -1
