import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import numpy as np

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from states.login_flow import _wait_for_town
from states.handlers.explore import ExploreHandler


class TestDungeonRelaunchRecovery(unittest.TestCase):
    """
    地下城意外重開與每層起點 (dungeons/leave.png) 重連恢復 Subflow 單元測試套件
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)
        self.machine.config = {"name": "地下城模式", "type": "dungeon", "explore_priorities": ["dungeons/leave.png"]}
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    @patch("os.path.exists")
    def test_1_login_flow_recognizes_dungeon_leave(self, mock_exists):
        """
        測試 1：登入流程等待時，當畫面上出現 dungeons/leave.png 時，能立即認定登入完成，設定 is_in_dungeon = True 並調用 detect_current_state
        """
        self.mock_capturer.get_window_rect.return_value = self.rect
        self.mock_capturer.capture.return_value = self.fake_img

        # 模擬只對 dungeons/leave.png 存在且匹配成功
        mock_exists.side_effect = lambda path: "dungeons/leave.png" in path.replace("\\", "/")
        self.mock_matcher.match.side_effect = lambda img, tpl, threshold=0.75: ((100, 100), 0.92) if tpl == "dungeons/leave.png" else (None, 0.0)

        with patch.object(self.machine, "detect_current_state") as mock_detect:
            _wait_for_town(self.machine, self.rect)
            self.assertTrue(self.machine.is_in_dungeon)
            mock_detect.assert_called_once()

    @patch("os.path.exists")
    def test_2_detect_current_state_mode_agnostic_dungeon_leave(self, mock_exists):
        """
        測試 2：不限模式 (Mode-Agnostic)：無論 config 為 dungeon, mix, stage, 還是 daily，全域定位遇到 dungeons/leave.png 均鎖定 is_in_dungeon = True 並轉移至 STATE_DUNGEON_EXPLORING
        """
        mock_exists.side_effect = lambda path: "dungeons/leave.png" in path.replace("\\", "/")
        self.mock_matcher.match.side_effect = lambda img, tpl, threshold=0.8: ((100, 100), 0.90) if tpl == "dungeons/leave.png" else (None, 0.0)

        modes = ["dungeon", "mix", "stage", "daily"]
        for mode in modes:
            self.machine.config = {"name": f"{mode}測試", "type": mode, "explore_priorities": []}
            self.machine.is_in_dungeon = False
            self.machine.current_state = self.machine.STATE_UNKNOWN

            self.machine.detect_current_state(self.fake_img, self.rect)

            self.assertTrue(self.machine.is_in_dungeon)
            self.assertEqual(self.machine.current_state, self.machine.STATE_DUNGEON_EXPLORING)

    @patch("os.path.exists")
    def test_3_explore_handler_handles_leave_anchor(self, mock_exists):
        """
        測試 3：ExploreHandler 處理 dungeons/leave.png 錨點時，維持 is_in_dungeon = True、重置樓層記憶與 no_explore_match_count，且絕對不發送點擊
        """
        handler = ExploreHandler(self.machine)
        self.machine.is_in_dungeon = True
        self.machine.dungeon_floor_transitioning = True
        self.machine.chest_opened_this_floor = True
        self.machine.config = {
            "type": "dungeon",
            "explore_priorities": ["dungeons/leave.png"]
        }

        mock_exists.return_value = True
        self.mock_matcher.match.side_effect = lambda img, tpl, threshold=0.8: ((50, 50), 0.95) if tpl == "dungeons/leave.png" else (None, 0.0)

        handler.handle(self.fake_img, self.rect)

        # 斷言 is_in_dungeon 為 True
        self.assertTrue(self.machine.is_in_dungeon)
        # 斷言樓層過渡記憶被重置
        self.assertFalse(self.machine.dungeon_floor_transitioning)
        self.assertFalse(self.machine.chest_opened_this_floor)
        # 斷言救援計數器被重置為 0
        self.assertEqual(handler.no_explore_match_count, 0)
        # 斷言 leave.png 為錨點，絕不點擊 exit 按鈕
        self.mock_mouse.click.assert_not_called()


if __name__ == "__main__":
    unittest.main()
