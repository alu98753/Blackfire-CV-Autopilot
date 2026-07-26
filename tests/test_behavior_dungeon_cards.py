import unittest
import numpy as np
import os
import time
from unittest.mock import MagicMock, patch
from states.handlers.navigation import NavigationHandler
from config import GAME_CONFIGS

class TestBehaviorDungeonCards(unittest.TestCase):
    """
    地下城卡片掃描與冷卻退避行為測試集 (Google Software Dev Standard)
    專注於 Given 卡片/冷卻情境 ➔ When 觸發 handle ➔ Then 斷言卡片對齊滑動與冷卻狀態轉移
    """
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()

        self.mock_machine.mouse = self.mock_mouse
        self.mock_machine.capturer = self.mock_capturer
        self.mock_machine.matcher = self.mock_matcher
        self.mock_matcher.match.return_value = (None, 0.0)
        self.mock_matcher.match_mutually_exclusive_tabs.return_value = (False, True, (0, 0), 0.95)

        self.mock_machine.dungeon_cooldowns = {}
        self.mock_machine.fallback_swipe_count = 0
        self.mock_machine.last_dungeon_scroll_time = 0.0
        self.mock_machine.current_dungeon_index = None
        self.mock_machine.is_in_dungeon = False
        self.mock_machine.need_bag_cleaning = False
        self.mock_machine.diamond_window_opened = False
        self.mock_machine.bread_window_opened = False
        self.mock_machine.need_diamond_collection = False
        self.mock_machine.need_bread_collection = False
        self.mock_machine.enable_bread = False
        self.mock_machine.is_daily_pipeline_active.return_value = False
        self.mock_machine.has_available_dungeon.return_value = True

        self.mock_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.mock_machine.config["greedy_dungeon"] = True
        self.mock_machine.config["greedy_allowed_indices"] = [0, 1, 2, 3, 4]

        self.handler = NavigationHandler(self.mock_machine)
        self.handler.mouse = self.mock_mouse
        self.handler.matcher = self.mock_matcher
        self.rect = {"left": 100, "top": 50, "width": 1000, "height": 800}

    # =========================================================================
    # 2.1 地下城卡片定位與對齊行為測試
    # =========================================================================

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_2_1_no_visible_dungeons_triggers_reset_to_left_swipe(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """
        [2.1 Behavior Test]
        Given: 地下城選關介面看得到 locked_entry.png (判定為地下城選關頁面)，但無任何可打卡片，且 fallback_swipe_count < 3
        When: 執行 NavigationHandler.handle()
        Then: 觸發向右長滑動 (CardListNavigator.reset_to_left)，且 fallback_swipe_count 遞增為 1
        """
        mock_exists.return_value = True
        mock_detect_cd.return_value = (False, None, "")

        def imread_side_effect(path):
            if "locked_entry.png" in path:
                return np.ones((41, 238, 3), dtype=np.uint8) * 99
            return np.ones((50, 100, 3), dtype=np.uint8) * 5

        def resize_side_effect(img, dsize):
            return img

        def match_side_effect(screen, templ, method):
            if np.array_equal(templ[0,0], [99, 99, 99]):
                return np.array([[0.95]], dtype=np.float32)
            return np.array([[0.0]], dtype=np.float32)

        mock_imread.side_effect = imread_side_effect
        mock_resize.side_effect = resize_side_effect
        mock_matchTemplate.side_effect = match_side_effect

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)
        self.mock_machine.fallback_swipe_count = 0

        self.handler.handle(screen_img, self.rect)

        # 驗證執行向右拉回滑動 drag
        self.mock_mouse.drag.assert_called_once_with(300, 450, 900, 450)
        self.assertEqual(self.mock_machine.fallback_swipe_count, 1)

    # =========================================================================
    # 2.2 冷卻木牌 OCR 解析與退避行為測試
    # =========================================================================

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_2_2_cooldown_sign_detected_with_ocr_updates_cooldown_timestamp(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """
        [2.2 Behavior Test A]
        Given: 貪婪模式下 Slime_entry 在畫面上，且檢測到冷卻木牌、OCR 成功辨識出剩餘 600 秒
        When: 執行 NavigationHandler.handle()
        Then: dungeon_cooldowns[0] 被寫入約 now + 600 秒之冷卻時間戳記，不發射點擊
        """
        mock_exists.return_value = True
        mock_detect_cd.return_value = (True, 600.0, "10:00")

        def match_side_effect(screen, templ, method):
            return np.array([[0.85]], dtype=np.float32)

        mock_imread.return_value = np.zeros((50, 50, 3), dtype=np.uint8)
        mock_resize.side_effect = lambda img, dsize: img
        mock_matchTemplate.side_effect = match_side_effect

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)
        now_before = time.time()

        self.handler.handle(screen_img, self.rect)

        # 斷言地下城 0 的冷卻時間寫入約 now + 600
        cd_until = self.mock_machine.dungeon_cooldowns.get(0, 0.0)
        self.assertGreaterEqual(cd_until, now_before + 595.0)
        self.assertLessEqual(cd_until, now_before + 605.0)

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_2_2_cooldown_sign_detected_ocr_failed_uses_30s_fallback(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """
        [2.2 Behavior Test B]
        Given: 貪婪模式下 Slime_entry 檢測到冷卻木牌，但 OCR 解析時間失敗 (parsed_secs=None)
        When: 執行 NavigationHandler.handle()
        Then: dungeon_cooldowns[0] 被寫入 30 秒臨時退避時間 (now + 30.0)
        """
        mock_exists.return_value = True
        mock_detect_cd.return_value = (True, None, "unreadable")

        def match_side_effect(screen, templ, method):
            return np.array([[0.85]], dtype=np.float32)

        mock_imread.return_value = np.zeros((50, 50, 3), dtype=np.uint8)
        mock_resize.side_effect = lambda img, dsize: img
        mock_matchTemplate.side_effect = match_side_effect

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)
        now_before = time.time()

        self.handler.handle(screen_img, self.rect)

        # 斷言地下城 0 的冷卻時間寫入約 now + 30
        cd_until = self.mock_machine.dungeon_cooldowns.get(0, 0.0)
        self.assertGreaterEqual(cd_until, now_before + 28.0)
        self.assertLessEqual(cd_until, now_before + 32.0)

    # =========================================================================
    # 2.3 亮骨頭未解鎖過濾行為測試
    # =========================================================================

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_2_3_light_skull_similarity_below_threshold_sets_inf_cooldown(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """
        [2.3 Behavior Test]
        Given: 貪婪模式下 Slime_entry 在畫面上無冷卻木牌，但亮骨頭 (light_skull.png) 比對相似度 0.50 (< 0.75)
        When: 執行 NavigationHandler.handle()
        Then: dungeon_cooldowns[0] 被寫入 float('inf') (永久不可打)，跳過該關卡
        """
        mock_exists.return_value = True
        # 無冷卻木牌
        mock_detect_cd.return_value = (False, None, "")

        def imread_side_effect(path):
            if "light_skull.png" in path:
                return np.ones((10, 10, 3), dtype=np.uint8) * 10
            return np.ones((50, 50, 3), dtype=np.uint8) * 5

        def match_side_effect(screen, templ, method):
            if np.array_equal(templ[0,0], [10, 10, 10]):
                # 亮骨頭相似度 0.50 (低於 0.75 閥值)
                return np.array([[0.50]], dtype=np.float32)
            # Slime_entry 入口在 (200, 100) 匹配成功 0.85
            res = np.zeros((800 - templ.shape[0] + 1, 1000 - templ.shape[1] + 1), dtype=np.float32)
            res[100, 200] = 0.85
            return res

        mock_imread.side_effect = imread_side_effect
        mock_resize.side_effect = lambda img, dsize: img
        mock_matchTemplate.side_effect = match_side_effect

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)

        self.handler.handle(screen_img, self.rect)

        # 斷言地下城 0 被判定為未解鎖，冷卻時間設為 float('inf')
        self.assertEqual(self.mock_machine.dungeon_cooldowns.get(0), float('inf'))

if __name__ == "__main__":
    unittest.main()
