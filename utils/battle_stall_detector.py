"""Health bar stall detection for battle scene.

Provides a pure, stateless perception helper to extract a lightweight
signature of the ally/enemy health bar region to detect stalled battles,
with semantic debug visualization routed through utils.debug_artifacts.
"""

from typing import Any
import logging
import cv2
import numpy as np

from utils.debug_artifacts import write_debug_image


def extract_health_bar_signature(
    screen_img: Any,
    top_ratio: float = 0.64,
    bottom_ratio: float = 0.69,
    save_debug: bool = False,
) -> int:
    """Extract a lightweight red-pixel count signature from the battle health-bar ROI.

    In 1920x1080 (or any scaled game view), the combat health bars sit at
    the specified height ratios (default 64% to 69% to isolate health bars from character bodies).

    Args:
        screen_img: Full screenshot image (numpy ndarray in BGR).
        top_ratio: Top boundary ratio of screen height (default: 0.64).
        bottom_ratio: Bottom boundary ratio of screen height (default: 0.69).
        save_debug: If True, writes annotated debug images under scratch/debug/:
                    - debug_battle_stall_roi.png (full screen with ROI bounding box)
                    - debug_battle_stall_mask.png (ROI, red mask, and overlay)

    Returns:
        int: Total number of active red health bar pixels in the ROI.
             If screen_img is invalid, returns -1.
    """
    if screen_img is None or not hasattr(screen_img, "shape") or len(screen_img.shape) < 2:
        return -1

    height, width = screen_img.shape[:2]
    # Scoped ROI: narrow horizontal strip strictly isolating health bars
    y_start = max(0, int(height * top_ratio))
    y_end = min(height, int(height * bottom_ratio))
    roi = screen_img[y_start:y_end, :]

    if roi.size == 0 or y_end <= y_start:
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

        red_count = int(cv2.countNonZero(red_mask))

        if save_debug:
            _save_battle_stall_debug_artifacts(
                screen_img, roi, red_mask, y_start, y_end, top_ratio, bottom_ratio, red_count
            )

        return red_count
    except Exception as exc:
        logging.debug("[BattleStallDetector] Extraction failed: %s", exc)
        return -1


def _save_battle_stall_debug_artifacts(
    screen_img: np.ndarray,
    roi: np.ndarray,
    red_mask: np.ndarray,
    y_start: int,
    y_end: int,
    top_ratio: float,
    bottom_ratio: float,
    red_count: int,
) -> None:
    """Generate semantic visual debug artifacts and route to scratch/debug/."""
    try:
        height, width = screen_img.shape[:2]

        # 1. Full-screen ROI bounding box visualization
        roi_debug = screen_img.copy()
        box_color = (0, 255, 0)  # Bright green
        cv2.rectangle(roi_debug, (0, y_start), (width - 1, y_end - 1), box_color, 2)

        label = f"Battle HP ROI: Y=[{y_start}:{y_end}] ({top_ratio*100:.1f}%-{bottom_ratio*100:.1f}%) | Red: {red_count}px"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 1
        (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        label_y1 = max(0, y_start - th - baseline - 8)
        label_y2 = y_start
        cv2.rectangle(roi_debug, (0, label_y1), (tw + 16, label_y2), (0, 0, 0), -1)
        cv2.putText(roi_debug, label, (8, y_start - 6), font, font_scale, (0, 255, 255), thickness, cv2.LINE_AA)

        write_debug_image("debug_battle_stall_roi.png", roi_debug)

        # 2. Detailed 3-panel ROI comparison: [Raw ROI] | [Binary Mask] | [Overlay]
        mask_3ch = cv2.cvtColor(red_mask, cv2.COLOR_GRAY2BGR)

        # Create overlay: highlight detected red pixels with bright magenta
        overlay = roi.copy()
        highlight_color = np.zeros_like(roi)
        highlight_color[red_mask > 0] = [255, 0, 255]  # Magenta
        cv2.addWeighted(highlight_color, 0.6, overlay, 1.0, 0, overlay)

        # Add section labels to each panel
        def _add_panel_title(img: np.ndarray, title: str) -> np.ndarray:
            labeled = img.copy()
            cv2.rectangle(labeled, (0, 0), (360, 24), (20, 20, 20), -1)
            cv2.putText(labeled, title, (6, 17), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            return labeled

        panel_raw = _add_panel_title(roi, "1. Cropped Combat ROI")
        panel_mask = _add_panel_title(mask_3ch, f"2. Red Mask ({red_count} px)")
        panel_overlay = _add_panel_title(overlay, "3. Health Bar Detection Overlay")

        # Vertical stack of the three panels for easy viewing
        divider = np.zeros((4, roi.shape[1], 3), dtype=np.uint8)
        divider[:] = (0, 255, 255)  # Yellow separation bar
        combo = np.vstack([panel_raw, divider, panel_mask, divider, panel_overlay])

        write_debug_image("debug_battle_stall_mask.png", combo)
        logging.info("📸 [BattleStallDetector] Debug artifacts saved: debug_battle_stall_roi.png, debug_battle_stall_mask.png")
    except Exception as exc:
        logging.debug("[BattleStallDetector] Failed to generate debug artifacts: %s", exc)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from config import get_battle_stall_settings
    stall_cfg = get_battle_stall_settings()
    top_r = stall_cfg["roi_top_ratio"]
    bot_r = stall_cfg["roi_bottom_ratio"]

    sample_path = Path("tests/fixtures/battle_stall_sample.png")
    if len(sys.argv) > 1:
        sample_path = Path(sys.argv[1])

    if not sample_path.exists():
        print(f"[ERROR] Sample image not found: {sample_path}")
        sys.exit(1)

    test_img = cv2.imread(str(sample_path))
    if test_img is None:
        print(f"[ERROR] Failed to load image: {sample_path}")
        sys.exit(1)

    print(f"[TEST] Testing Battle Stall Detection on: {sample_path} ({test_img.shape[1]}x{test_img.shape[0]})")
    print(f"[CONFIG] Active TOML Ratios: top={top_r*100:.1f}%, bottom={bot_r*100:.1f}%")
    sig = extract_health_bar_signature(test_img, top_ratio=top_r, bottom_ratio=bot_r, save_debug=True)
    print(f"[SUCCESS] Extracted Health Bar Signature (Red Pixels): {sig}")
    print("[OUTPUT] Debug images written to scratch/debug/:")
    print("   - scratch/debug/debug_battle_stall_roi.png")
    print("   - scratch/debug/debug_battle_stall_mask.png")
