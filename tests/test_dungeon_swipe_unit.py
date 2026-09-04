import unittest
import numpy as np
import os
import time
import logging
from unittest.mock import MagicMock, patch
from states.handlers.navigation import NavigationHandler
from config import GAME_CONFIGS

class TestDungeonSwipeLogic(unittest.TestCase):
    """
    專門防歸回測試 (Regression Tests)：
    鎖定 NavigationHandler 中針對地下城 (Dungeon) 的左右滑動與選關邏輯。
    包含：
    1. 防呆拉回滑動 (無卡片可見時向右長滑動)
    2. 防呆滑動次數上限處理 (回到大廳/返回)
    3. 目標卡片在右側時向左滑動 (Drag Left)
    4. 目標卡片在左側時向右滑動 (Drag Right)
    5. 目標卡片在畫面上時直接點擊不引發滑動
    """

    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()

import unittest
import numpy as np
import os
import time
import logging
from unittest.mock import MagicMock, patch
from states.handlers.navigation import NavigationHandler
from config import GAME_CONFIGS

class TestDungeonSwipeLogic(unittest.TestCase):
    """
    專門防歸回測試 (Regression Tests)：
    鎖定 NavigationHandler 中針對地下城 (Dungeon) 的左右滑動與選關邏輯。
    包含：
    1. 防呆拉回滑動 (無卡片可見時向右長滑動)
    2. 防呆滑動次數上限處理 (回到大廳/返回)
    3. 目標卡片在右側時向左滑動 (Drag Left)
    4. 目標卡片在左側時向右滑動 (Drag Right)
    5. 目標卡片在畫面上時直接點擊不引發滑動
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

        self.mock_machine.config = GAME_CONFIGS["dungeon"].copy()
        self.mock_machine.config["greedy_dungeon"] = True
        self.mock_machine.config["greedy_allowed_indices"] = [1, 2, 3, 4]

        self.handler = NavigationHandler(self.mock_machine)
        self.handler.mouse = self.mock_mouse
        self.handler.matcher = self.mock_matcher
        self.handler.card_alignment_tab = "dungeon"

        self.rect = {"left": 100, "top": 50, "width": 1000, "height": 800}

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_fallback_swipe_when_no_unlocked_dungeon_visible(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """[地下城滑動測試 1] 已確認地下城頁且無可見解鎖卡片時，發動防呆長拖曳拉回。"""
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

        # 驗證執行右滑 drag: start_x = 100 + 200 = 300, end_x = 100 + 800 = 900, y_pos = 50 + 400 = 450
        self.mock_mouse.drag.assert_called_once_with(
            300, 450, 900, 450, duration=0.8, inertia=False
        )
        self.assertEqual(self.handler.card_alignment_attempts, 1)

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_fallback_swipe_max_count_exceeded_switches_back(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """[地下城滑動測試 2] 防呆滑動達到上限 7 次後，點擊 goback_town 返回"""
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

        def mock_match(screen, templ, threshold=0.8, **kwargs):
            if "goback_town.png" in templ:
                return (50, 50), 0.9
            return None, 0.0

        self.mock_matcher.match.side_effect = mock_match

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)
        self.handler.card_alignment_attempts = 7

        self.handler.handle(screen_img, self.rect)

        self.mock_mouse.drag.assert_not_called()
        self.mock_mouse.click.assert_called_once_with(150, 100)
        self.assertEqual(self.handler.card_alignment_attempts, 0)

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_swipe_left_when_target_on_right(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """[地下城滑動測試 3] 可見卡片為 index 0，目標為 index 3 (在右側) ➔ 發動向左滑動 (Drag Left)"""
        mock_exists.return_value = True
        mock_detect_cd.return_value = (False, None, "")

        def imread_side_effect(path):
            if "Slime_entry.png" in path:
                return np.ones((50, 100, 3), dtype=np.uint8) * 10
            return np.ones((50, 100, 3), dtype=np.uint8) * 5

        def resize_side_effect(img, dsize):
            return img

        def match_side_effect(screen, templ, method):
            if np.array_equal(templ[0,0], [10, 10, 10]):
                return np.array([[0.90]], dtype=np.float32)
            return np.array([[0.0]], dtype=np.float32)

        mock_imread.side_effect = imread_side_effect
        mock_resize.side_effect = resize_side_effect
        mock_matchTemplate.side_effect = match_side_effect

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)

        self.handler.handle(screen_img, self.rect)

        self.mock_mouse.drag.assert_called_once_with(700, 450, 500, 450, duration=0.8, inertia=False)

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_swipe_right_when_target_on_left(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """[地下城滑動測試 4] 可見卡片為 index 3，目標為 index 1 (在左側) ➔ 發動向右滑動 (Drag Right)"""
        mock_exists.return_value = True
        mock_detect_cd.return_value = (False, None, "")

        self.mock_machine.dungeon_cooldowns = {4: time.time() + 999, 3: time.time() + 999}

        def imread_side_effect(path):
            if "Ruins_entry.png" in path:
                return np.ones((50, 100, 3), dtype=np.uint8) * 40
            return np.ones((50, 100, 3), dtype=np.uint8) * 5

        def resize_side_effect(img, dsize):
            return img

        def match_side_effect(screen, templ, method):
            if np.array_equal(templ[0,0], [40, 40, 40]):
                return np.array([[0.90]], dtype=np.float32)
            return np.array([[0.0]], dtype=np.float32)

        mock_imread.side_effect = imread_side_effect
        mock_resize.side_effect = resize_side_effect
        mock_matchTemplate.side_effect = match_side_effect

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)

        self.handler.handle(screen_img, self.rect)

        self.mock_mouse.drag.assert_called_once_with(500, 450, 700, 450, duration=0.8, inertia=False)

    @patch("states.handlers.navigation.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    @patch("cv2.imread")
    @patch("cv2.resize")
    @patch("cv2.matchTemplate")
    def test_target_dungeon_visible_clicks_without_swiping(
        self, mock_matchTemplate, mock_resize, mock_imread, mock_exists, mock_detect_cd
    ):
        """[地下城滑動測試 5] 目標卡片在畫面上時直接點擊，完全不觸發 drag"""
        mock_exists.return_value = True
        mock_detect_cd.return_value = (False, None, "")

        def imread_side_effect(path):
            if "Ruins_entry.png" in path:
                return np.ones((50, 100, 3), dtype=np.uint8) * 40
            return np.ones((50, 100, 3), dtype=np.uint8) * 5

        def resize_side_effect(img, dsize):
            return img

        def match_side_effect(screen, templ, method):
            if np.array_equal(templ[0,0], [40, 40, 40]):
                return np.array([[0.90]], dtype=np.float32)
            return np.array([[0.0]], dtype=np.float32)

        mock_imread.side_effect = imread_side_effect
        mock_resize.side_effect = resize_side_effect
        mock_matchTemplate.side_effect = match_side_effect

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)

        self.handler.handle(screen_img, self.rect)

        self.mock_mouse.drag.assert_not_called()
        self.assertTrue(self.mock_mouse.click.called)
        self.assertEqual(self.mock_machine.current_dungeon_index, 4)
        self.assertTrue(self.mock_machine.is_in_dungeon)
        self.assertEqual(self.handler.card_alignment_attempts, 0)

if __name__ == "__main__":
    unittest.main()
