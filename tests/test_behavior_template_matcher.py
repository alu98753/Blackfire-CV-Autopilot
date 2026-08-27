"""
test_behavior_template_matcher.py — Issue #8 & #9 行為守護測試

T9-A~C : _nms() 私有方法單元測試（NMS 距離計算正確性）
T9-D~F : match() / match_all() 整合行為測試（合成影像）
T8-A~C : _pyramid_precheck() / _apply_brightness_filter() 單元測試
"""
import unittest
from unittest.mock import patch
import numpy as np
import cv2
import os
import shutil
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.matcher import TemplateMatcher, DEFAULT_MATCH_SCALES


# ──────────────────────────────────────────────
# 輔助函式
# ──────────────────────────────────────────────
def _distinctive_template(block_size):
    """
    製作具有獨特紋理的模板（左半亮右半暗棋盤格），
    避免純色方塊在均一背景上產生到處高分的問題。
    """
    tmpl = np.zeros((block_size, block_size, 3), dtype=np.uint8)
    half = block_size // 2
    tmpl[:half, :half] = (255, 255, 255)   # 左上白
    tmpl[half:, half:] = (200, 200, 200)   # 右下淺灰
    tmpl[:half, half:] = (50, 50, 50)      # 右上深灰
    tmpl[half:, :half] = (100, 100, 100)   # 左下中灰
    return tmpl


def _screen_with_instances(screen_h, screen_w, template, positions):
    """
    在深灰色背景（32,32,32）上，將 template 貼到 positions 各位置。
    背景非純黑，避免 TM_CCOEFF_NORMED 在所有 40x40 區域都誤配。
    """
    screen = np.full((screen_h, screen_w, 3), 32, dtype=np.uint8)
    h, w = template.shape[:2]
    for x, y in positions:
        screen[y:y + h, x:x + w] = template
    return screen


def _write_template(templates_dir, filename, block_size):
    """儲存獨特紋理模板，回傳 filename。"""
    tmpl = _distinctive_template(block_size)
    cv2.imwrite(os.path.join(templates_dir, filename), tmpl)
    return filename


# ══════════════════════════════════════════════
# Issue #9 — NMS 行為測試
# ══════════════════════════════════════════════
class TestNMSBehavior(unittest.TestCase):
    """T9-A ~ T9-F"""

    def setUp(self):
        self.templates_dir = "test_templates_nms"
        os.makedirs(self.templates_dir, exist_ok=True)
        self.matcher = TemplateMatcher(
            templates_dir=self.templates_dir,
            template_scale=1.0,
            auto_scale=False,
        )

    def tearDown(self):
        if os.path.exists(self.templates_dir):
            shutil.rmtree(self.templates_dir)

    # ── T9-A ──────────────────────────────────
    def test_T9A_nms_collapses_adjacent_candidates(self):
        """
        T9-A: 三個相鄰候選點（間距 1px）→ NMS 只保留信心度最高的一個。
        """
        raw = [
            (100, 100, 0.95),  # 最高，最先加入
            (101, 100, 0.93),
            (102, 100, 0.91),
        ]
        result = self.matcher._nms(raw, min_dist_x=20, min_dist_y=20)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], (100, 100, 0.95))

    # ── T9-B ──────────────────────────────────
    def test_T9B_nms_preserves_distant_candidates(self):
        """
        T9-B: 兩個相距 200px 的候選點（遠超 min_dist=30）→ 兩者都保留。
        """
        raw = [
            (300, 100, 0.95),
            (100, 100, 0.90),
        ]
        result = self.matcher._nms(raw, min_dist_x=30, min_dist_y=30)
        self.assertEqual(len(result), 2)

    # ── T9-C ──────────────────────────────────
    def test_T9C_nms_boundary_exactly_at_min_dist_not_suppressed(self):
        """
        T9-C: 兩點距離恰等於 min_dist（30px）→ `< 30` 不含等號，兩者都保留。
        """
        raw = [
            (100, 100, 0.95),
            (130, 100, 0.90),  # x 差距恰好 = 30
        ]
        result = self.matcher._nms(raw, min_dist_x=30, min_dist_y=30)
        self.assertEqual(len(result), 2)

    # ── T9-D ──────────────────────────────────
    def test_T9D_match_returns_single_best_for_overlapping_pattern(self):
        """
        T9-D: 40x40 模板，畫面上兩個相鄰（間距 3px）相同紋理方塊。
        match() 只應回傳 1 個最佳點（兩個方塊間距 3px < NMS 半徑 20px，被壓成同一 cluster）。
        """
        block = 40
        tmpl = _distinctive_template(block)
        _write_template(self.templates_dir, "overlap.png", block)

        # 兩個方塊中心相差 3px，完全在 NMS 半徑（20px）內
        screen = _screen_with_instances(300, 600, tmpl, [(100, 100), (103, 100)])

        pos, conf = self.matcher.match(screen, "overlap.png", threshold=0.85)

        self.assertIsNotNone(pos, msg="應找到匹配點")
        self.assertGreater(conf, 0.85)

    # ── T9-E ──────────────────────────────────
    def test_T9E_match_all_returns_two_distinct_instances(self):
        """
        T9-E: 40x40 獨特紋理模板，畫面上兩個相距 200px 的相同方塊。
        match_all() 應回傳 2 個獨立結果。
        """
        block = 40
        tmpl = _distinctive_template(block)
        _write_template(self.templates_dir, "two_icons.png", block)

        # 兩個實例中心相距 200px，遠超 NMS 半徑（20px）
        screen = _screen_with_instances(300, 600, tmpl, [(50, 100), (250, 100)])

        results = self.matcher.match_all(screen, "two_icons.png", threshold=0.85)

        self.assertEqual(len(results), 2,
                         msg=f"Expected 2 distinct instances, got {len(results)}")

    # ── T9-F ──────────────────────────────────
    def test_T9F_small_template_nms_precision_after_unification(self):
        """
        T9-F: 20x20 小模板，兩個實例相距 25px（不重疊，且 25px > NMS 半徑 10px）。
        match_all() 應回傳 2 個獨立結果。

        注意：兩個方塊不能視覺重疊（x=50 和 x=65 各寬 20px 會重疊），
        所以 x=50 和 x=80（間距 30px，20px 方塊無重疊）是正確設計。
        """
        block = 20
        tmpl = _distinctive_template(block)
        _write_template(self.templates_dir, "small_icon.png", block)

        # 兩個實例：x=50(→70) 與 x=80(→100)，無視覺重疊，間距 30px > NMS 半徑 10px
        screen = _screen_with_instances(200, 400, tmpl, [(50, 80), (80, 80)])

        results = self.matcher.match_all(screen, "small_icon.png", threshold=0.85)

        self.assertEqual(len(results), 2,
                         msg=f"20x20 模板 NMS 半徑=10px，間距 30px > 10px，應保留 2 個，got {len(results)}")



# ══════════════════════════════════════════════
# Issue #8 — match() 方法分解行為測試
# ══════════════════════════════════════════════
class TestMatchMethodDecomposition(unittest.TestCase):
    """T8-A ~ T8-C"""

    def setUp(self):
        self.templates_dir = "test_templates_decomp"
        os.makedirs(self.templates_dir, exist_ok=True)
        self.matcher = TemplateMatcher(
            templates_dir=self.templates_dir,
            template_scale=1.0,
            auto_scale=False,
        )

    def tearDown(self):
        if os.path.exists(self.templates_dir):
            shutil.rmtree(self.templates_dir)

    # ── T8-A ──────────────────────────────────
    def test_T8A_pyramid_precheck_rejects_obvious_no_match(self):
        """
        T8-A: 雜訊灰色畫面（無目標模板）+ 高對比紅藍漸層模板 →
        金字塔預檢應回傳 False（縮圖信心度 < threshold - 0.10）。

        注意：全黑 + 全白模板是 TM_CCOEFF_NORMED 的退化情況（方差為 0 時輸出 1.0），
        不適合用來測試「無法匹配」情境。改用有紋理的背景 + 不出現在畫面的模板。
        """
        rng = np.random.default_rng(42)
        # 雜訊灰色背景（無結構，無法匹配高對比模板）
        screen = rng.integers(80, 120, (1080, 1920, 3), dtype=np.uint8)

        # 高對比藍紅模板（不存在於畫面中）
        template = np.zeros((80, 80, 3), dtype=np.uint8)
        template[:, :40] = (255, 0, 0)   # 左半藍
        template[:, 40:] = (0, 0, 255)   # 右半紅

        passed, max_val = self.matcher._pyramid_precheck(screen, template, threshold=0.9)

        self.assertFalse(passed, msg="雜訊背景對高對比模板應預檢失敗")
        self.assertIsNotNone(max_val)
        self.assertLess(max_val, 0.9 - 0.10 + 0.01,
                        msg=f"預檢信心度 {max_val:.4f} 應低於 {0.9 - 0.10:.2f}")

    # ── T8-B ──────────────────────────────────
    def test_T8B_pyramid_precheck_passes_for_obvious_match(self):
        """
        T8-B: 畫面中有明確匹配區域 → 金字塔預檢應回傳 True（允許繼續全解析度比對）。
        """
        block = 80
        template = np.ones((block, block, 3), dtype=np.uint8) * 200
        screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        screen[100:100 + block, 200:200 + block] = template

        passed, _ = self.matcher._pyramid_precheck(screen, template, threshold=0.8)

        self.assertTrue(passed, msg="畫面中有匹配區域時預檢應通過")

    # ── T8-C ──────────────────────────────────
    def test_T8C_apply_brightness_filter_rejects_dark_region(self):
        """
        T8-C: 候選點所在區域比模板暗很多（亮度比 < brightness_threshold）→ 回傳 None。
        """
        block = 40
        template = np.ones((block, block, 3), dtype=np.uint8) * 200  # 亮模板

        # 暗畫面，候選點區域亮度比 ≈ 20/200 = 0.1（遠低於 0.7）
        screen = np.ones((200, 400, 3), dtype=np.uint8) * 20

        candidates = [(50, 50, 0.90)]  # 一個候選點
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

        result = self.matcher._apply_brightness_filter(
            candidates, screen_gray, template_gray, temp_h=block, temp_w=block,
            brightness_threshold=0.7, template_name="test.png"
        )

        self.assertIsNone(result, msg="亮度不足時 _apply_brightness_filter 應回傳 None")


if __name__ == "__main__":
    unittest.main()
