import unittest
from unittest.mock import MagicMock
import numpy as np
from utils.town_building_detector import (
    detect_building_with_red_dot,
    is_true_red_dot,
    BuildingCheckResult,
)


class TestTownBuildingDetector(unittest.TestCase):
    """測試城鎮建築與下方紅點純感知檢測器 (utils/town_building_detector.py)"""

    def setUp(self):
        self.mock_matcher = MagicMock()
        self.mock_matcher.templates_dir = "templates"
        from vision.matcher import TemplateMatcher
        self.mock_matcher.compute_candidate_scales = TemplateMatcher().compute_candidate_scales
        self.dummy_screen = np.zeros((600, 800, 3), dtype=np.uint8)

    def test_is_true_red_dot_with_pure_red(self):
        """測試：純紅色 Patch (BGR: 0, 0, 240) 應被判定為真紅點"""
        red_patch = np.zeros((24, 24, 3), dtype=np.uint8)
        red_patch[:, :] = (30, 40, 230)  # BGR 格式，紅為主，少量綠藍
        is_red, ratio = is_true_red_dot(red_patch)
        self.assertTrue(is_red)
        self.assertGreater(ratio, 0.8)

    def test_is_true_red_dot_with_orange(self):
        """測試：橘色 Patch (BGR: 20, 130, 240) 應被嚴格過濾排除"""
        orange_patch = np.zeros((24, 24, 3), dtype=np.uint8)
        orange_patch[:, :] = (20, 130, 240)  # BGR 格式，標準橘色
        is_red, ratio = is_true_red_dot(orange_patch)
        self.assertFalse(is_red)
        self.assertLess(ratio, 0.1)

    def test_is_true_red_dot_with_gray_or_empty(self):
        """測試：灰色、全黑、無效維度 Patch 應回傳 False 與 0.0"""
        gray_patch = np.full((24, 24, 3), 128, dtype=np.uint8)
        self.assertFalse(is_true_red_dot(gray_patch)[0])
        self.assertFalse(is_true_red_dot(np.zeros((24, 24, 3), dtype=np.uint8))[0])
        self.assertFalse(is_true_red_dot(None)[0])
        self.assertFalse(is_true_red_dot(np.array([]))[0])

    def test_none_input_handling(self):
        """測試：當傳入空畫面或無 matcher 時，優雅回傳 found_building=False"""
        res1 = detect_building_with_red_dot(None, "dummy.png", self.mock_matcher)
        self.assertFalse(res1.found_building)
        self.assertFalse(res1.has_red_dot)

        res2 = detect_building_with_red_dot(self.dummy_screen, "dummy.png", None)
        self.assertFalse(res2.found_building)
        self.assertFalse(res2.has_red_dot)

    def test_building_not_found(self):
        """測試：當畫面上找不到建築時，回傳 found_building=False, has_red_dot=False"""
        self.mock_matcher.match.return_value = (None, 0.0)
        res = detect_building_with_red_dot(self.dummy_screen, "building.png", self.mock_matcher)
        self.assertFalse(res.found_building)
        self.assertFalse(res.has_red_dot)
        self.assertIsNone(res.building_pos)

    def test_building_found_without_red_dot(self):
        """測試：建築存在但下方無紅點，回傳 found_building=True, has_red_dot=False"""
        def fake_match(img, template, threshold=0.75, **kwargs):
            if template == "building.png":
                return ((200, 300), 0.85)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        res = detect_building_with_red_dot(self.dummy_screen, "building.png", self.mock_matcher)
        self.assertTrue(res.found_building)
        self.assertFalse(res.has_red_dot)
        self.assertEqual(res.building_pos, (200, 300))
        self.assertIsNone(res.red_dot_pos)
        self.assertAlmostEqual(res.confidence_building, 0.85)

    def test_building_found_with_red_dot(self):
        """測試：建築存在且下方帶有真紅點，回傳 found_building=True, has_red_dot=True 且計算全局座標"""
        screen = np.full((600, 800, 3), (30, 40, 230), dtype=np.uint8)

        def fake_match(img, template, threshold=0.75, **kwargs):
            if template == "building.png":
                return ((200, 300), 0.90)
            elif template == "town_building/red_dot.png":
                return ((50, 40), 0.88)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        res = detect_building_with_red_dot(screen, "building.png", self.mock_matcher)
        self.assertTrue(res.found_building)
        self.assertTrue(res.has_red_dot)
        self.assertEqual(res.building_pos, (200, 300))
        self.assertIsNotNone(res.red_dot_pos)
        self.assertAlmostEqual(res.confidence_building, 0.90)
        self.assertAlmostEqual(res.confidence_red_dot, 0.88)

    def test_building_found_with_orange_dot_ignored(self):
        """測試：建築存在且模板比對命中，但色彩為橘色任務驚嘆號時，應被色彩門禁過濾為 has_red_dot=False"""
        screen = np.full((600, 800, 3), (20, 130, 240), dtype=np.uint8)  # 橘色畫面

        def fake_match(img, template, threshold=0.75, **kwargs):
            if template == "building.png":
                return ((200, 300), 0.90)
            elif template == "town_building/red_dot.png":
                return ((50, 40), 0.89)  # 幾何模板相似度很高
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        res = detect_building_with_red_dot(screen, "building.png", self.mock_matcher)
        self.assertTrue(res.found_building)
        self.assertFalse(res.has_red_dot)  # 色彩門禁成功攔截
        self.assertIsNone(res.red_dot_pos)

    def test_debug_tag_and_tag_resolution(self):
        """測試：debug_tag 能正確推斷或手動指定"""
        from utils.town_building_detector import _resolve_debug_tag
        self.assertEqual(_resolve_debug_tag("custom", "any.png"), "custom")
        self.assertEqual(_resolve_debug_tag(None, "town_building/mysterious_treasure/mysterious_treasure.png"), "chest")
        self.assertEqual(_resolve_debug_tag(None, "town_building/Tavern/Tavern.png"), "hero_draw")
        self.assertEqual(_resolve_debug_tag(None, "town_building/Blood_Altar/Blood_Altar.png"), "blood_altar")
        self.assertEqual(_resolve_debug_tag(None, "town_building/bulletin_board/task.png"), "bulletin_board")
        self.assertEqual(_resolve_debug_tag(None, "other.png"), "building")

    def test_multi_scale_red_dot_matching(self):
        """測試：多尺度紅點候選比對，當某一尺度命中且為真紅點時成功判定"""
        screen = np.full((600, 800, 3), (30, 40, 230), dtype=np.uint8)

        def fake_match(img, template, threshold=0.60, **kwargs):
            if template == "building.png":
                return ((200, 300), 0.90)
            elif template == "town_building/red_dot.png":
                scales = kwargs.get("scales")
                if kwargs.get("scale") == 1.0 or (scales and any(abs(s - 1.0) < 1e-3 for s in scales)):
                    return ((60, 50), 0.82)
                return (None, 0.45)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        res = detect_building_with_red_dot(
            screen, "building.png", self.mock_matcher, debug_tag="test_multiscale"
        )
        self.assertTrue(res.found_building)
        self.assertTrue(res.has_red_dot)
        self.assertAlmostEqual(res.confidence_red_dot, 0.82)


if __name__ == "__main__":
    unittest.main()
