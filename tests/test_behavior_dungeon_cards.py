import unittest
import numpy as np
import os
import time
from unittest.mock import MagicMock, patch
from states.handlers.navigation import NavigationHandler
from states.handlers.collect_only import CollectOnlyHandler
from config import GAME_CONFIGS
from utils.scene_detector import SceneInfo, SceneType

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
        self.handler.card_alignment_tab = "dungeon"
        self.rect = {"left": 100, "top": 50, "width": 1000, "height": 800}

    def test_collect_only_resumes_saved_dungeon_config_when_cooldown_expires(self):
        """A cooldown fallback must retain enough context to re-enter dungeon mode."""
        dungeon_config = GAME_CONFIGS["dungeon"].copy()
        dungeon_config["auto_resume_dungeon_on_cd"] = True
        self.mock_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.mock_machine.dungeon_cooldown_return_config = dungeon_config
        self.mock_machine.need_diamond_collection = False
        self.mock_machine.need_bread_collection = False
        self.mock_machine.enable_bread = False
        self.mock_machine.has_available_dungeon.return_value = True
        self.mock_machine.STATE_UNKNOWN = "UNKNOWN"

        handler = CollectOnlyHandler(self.mock_machine)
        handler.handle(None, self.rect)

        self.assertEqual(self.mock_machine.config, dungeon_config)
        self.assertIsNone(self.mock_machine.dungeon_cooldown_return_config)
        self.mock_machine.transition_to.assert_called_once_with("UNKNOWN")

    # =========================================================================
    # 2.1 地下城卡片定位與對齊行為測試
    # =========================================================================

    @patch("os.path.exists", return_value=True)
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_locked_cards_on_other_lobby_switch_tab_before_dungeon_scan(
        self, mock_match_template, mock_resize, mock_imread, _mock_exists
    ):
        """A dungeon intent cannot authorize dungeon scanning on another lobby tab."""
        self.handler.scene_detector = MagicMock()
        self.handler.scene_detector.matcher = self.mock_matcher
        self.handler.scene_detector.detect.return_value = SceneInfo(
            scene_type=SceneType.LOBBY_OTHER,
            is_lobby=True,
        )

        def match_side_effect(_img, template, **_kwargs):
            if template == "dungeons/dungeon.png":
                return ((400, 100), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect
        mock_imread.return_value = np.ones((41, 238, 3), dtype=np.uint8)
        mock_resize.side_effect = lambda image, _size: image
        mock_match_template.return_value = np.array([[0.95]], dtype=np.float32)

        self.handler.handle(np.zeros((800, 1000, 3), dtype=np.uint8), self.rect)

        mock_match_template.assert_not_called()
        self.mock_mouse.drag.assert_not_called()
        self.mock_mouse.click.assert_called_once_with(500, 150)

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
        Given: 已確認在地下城頁籤，畫面看得到 locked_entry.png，但無任何可打卡片，且 card_alignment_attempts < 7
        When: 執行 NavigationHandler.handle()
        Then: 觸發向右長滑動 (CardListNavigator.reset_to_left)，且 card_alignment_attempts 遞增為 1
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
        self.handler.card_alignment_attempts = 0

        self.handler.handle(screen_img, self.rect)

        # 驗證執行向右拉回滑動 drag
        self.mock_mouse.drag.assert_called_once_with(
            300, 450, 900, 450, duration=0.8, inertia=False
        )
        self.assertEqual(self.handler.card_alignment_attempts, 1)

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

        # 斷言地下城 1 的冷卻時間寫入約 now + 600
        cd_until = self.mock_machine.dungeon_cooldowns.get(1, 0.0)
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

        # 斷言地下城 1 的冷卻時間寫入約 now + 30
        cd_until = self.mock_machine.dungeon_cooldowns.get(1, 0.0)
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

        # 斷言地下城 1 被判定為未解鎖，冷卻時間設為 float('inf')
        self.assertEqual(self.mock_machine.dungeon_cooldowns.get(1), float('inf'))

    # =========================================================================
    # 2.4 全冷卻混合模式防死鎖切換測試
    # =========================================================================

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_2_4_all_dungeons_cooldown_in_mix_mode_switches_to_stage_tab(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """
        [2.4 Behavior Test]
        Given: 混合模式 (type="mix") 下，地下城卡片在畫面上但檢測到冷卻木牌 (全冷卻)
        When: 執行 NavigationHandler.handle()
        Then: 自動呼叫 _switch_to_stage_or_back 點擊 select_stage.png 切換至關卡頁籤防死鎖
        """
        mock_exists.return_value = True
        self.mock_machine.stamina_retreat_start_time = None
        self.mock_machine.config = GAME_CONFIGS["mix"].copy()
        self.mock_machine.config["greedy_allowed_indices"] = [1]
        self.mock_machine.dungeon_cooldowns = {1: time.time() + 600.0}
        mock_detect_cd.return_value = (True, 600.0, "10:00")

        def fake_match(img, template, threshold=0.6, *args, **kwargs):
            if template == "common/select_stage.png":
                return ((150, 250), 0.85)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match

        mock_imread.return_value = np.zeros((50, 50, 3), dtype=np.uint8)
        mock_resize.side_effect = lambda img, dsize: img
        mock_matchTemplate.return_value = np.array([[0.85]], dtype=np.float32)

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)

        self.handler.handle(screen_img, self.rect)

        # 斷言發射點擊 (250, 300) (加上 rect offset left=100, top=50) 點擊 select_stage.png 切換頁籤
        self.mock_mouse.click.assert_called_once_with(250, 300)

    # =========================================================================
    # 2.5 全冷卻且無關卡頁籤時退回城鎮測試
    # =========================================================================

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_2_5_switch_to_stage_clicks_goback_town_when_select_stage_missing(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """
        [2.5 Behavior Test]
        Given: 全冷卻狀態切換頁籤時，畫面上無 common/select_stage.png，但看得到 goback_town.png
        When: 執行 NavigationHandler.handle()
        Then: 點擊 goback_town.png 退回城鎮
        """
        mock_exists.return_value = True
        self.mock_machine.stamina_retreat_start_time = None
        self.mock_machine.original_config = None
        self.mock_machine.config["type"] = "mix"
        self.mock_machine.config["greedy_allowed_indices"] = [1]
        self.mock_machine.dungeon_cooldowns = {1: time.time() + 600.0}
        mock_detect_cd.return_value = (True, 600.0, "10:00")

        def fake_match(img, template, threshold=0.6, *args, **kwargs):
            if template == "goback_town.png":
                return ((60, 450), 0.85)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match

        mock_imread.return_value = np.zeros((50, 50, 3), dtype=np.uint8)
        mock_resize.side_effect = lambda img, dsize: img
        mock_matchTemplate.return_value = np.array([[0.85]], dtype=np.float32)

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)

        self.handler.handle(screen_img, self.rect)

        # 斷言發射點擊 (160, 500) (加上 rect offset left=100, top=50) 點擊 goback_town.png 退回城鎮
        self.mock_mouse.click.assert_called_once_with(160, 500)

    # =========================================================================
    # 2.6 地下城多次滑動無卡片極限退回城鎮測試
    # =========================================================================

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_2_6_dungeon_mode_max_card_alignment_attempts_clicks_goback_town(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """
        [2.6 Behavior Test]
        Given: dungeon 模式下連滑 card_alignment_attempts >= 7 仍無可打卡片，看得到 goback_town.png
        When: 執行 NavigationHandler.handle()
        Then: 點擊 goback_town.png 退回城鎮，且重置 card_alignment_attempts 為 0
        """
        mock_exists.return_value = True
        self.mock_machine.stamina_retreat_start_time = None
        self.mock_machine.original_config = None
        self.mock_machine.config["type"] = "dungeon"
        self.handler.card_alignment_attempts = 7
        mock_detect_cd.return_value = (False, None, "")

        def imread_side_effect(path):
            if "locked_entry.png" in path:
                return np.ones((41, 238, 3), dtype=np.uint8) * 99
            return np.ones((50, 100, 3), dtype=np.uint8) * 5

        def match_side_effect(screen, templ, method):
            if np.array_equal(templ[0,0], [99, 99, 99]):
                return np.array([[0.95]], dtype=np.float32)
            return np.array([[0.0]], dtype=np.float32)

        def fake_match(img, template, threshold=0.6, *args, **kwargs):
            if template == "goback_town.png":
                return ((60, 450), 0.85)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        mock_imread.side_effect = imread_side_effect
        mock_resize.side_effect = lambda img, dsize: img
        mock_matchTemplate.side_effect = match_side_effect

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)

        self.handler.handle(screen_img, self.rect)

        # 驗證點擊 goback_town.png
        self.mock_mouse.click.assert_called_once_with(160, 500)
        # 驗證重置 card_alignment_attempts 為 0
        self.assertEqual(self.handler.card_alignment_attempts, 0)

if __name__ == "__main__":
    unittest.main()
