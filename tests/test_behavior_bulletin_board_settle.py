import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import numpy as np

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.handlers.bulletin_board import BulletinBoardHandler, BOARD_OPEN_SETTLE_TIMEOUT, BOARD_OPEN_HARD_TIMEOUT


class TestBehaviorBulletinBoardSettle(unittest.TestCase):
    """
    懸賞告示牌 WAIT_BOARD_OPEN 有界沉澱等待時間 (Bounded Settle Wait) 行為測試套件
    """

    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.config = {
            "type": "bulletin_board",
            "building_btn": "town_building/bulletin_board/bulletin_board.png",
            "reset_btn": "town_building/bulletin_board/reset.png",
            "quit_btn": "common/quit.png",
            "task_btn": "town_building/bulletin_board/task.png",
        }
        self.mock_machine.current_town_subflow = "bulletin_board"

        self.handler = BulletinBoardHandler(self.mock_machine)
        self.handler.matcher = MagicMock()
        self.handler.mouse = MagicMock()
        self.fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 800, "height": 600}

    def test_wait_board_open_does_not_kill_overlay_during_settle_window(self):
        """
        [契約 1 驗證] 剛進入 WAIT_BOARD_OPEN 時 (經過 1.0 秒 < 2.5 秒)，
        即使畫面偵測到 quit.png 但告示牌專屬特徵尚未就緒 (動畫過渡期)，
        絕不觸發關閉覆蓋層，維持在 WAIT_BOARD_OPEN 靜待沉澱。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.wait_board_open_start_time = 100.0

        # 模擬畫面：僅有 quit.png，無 reset/task 告示牌特徵
        def mock_match(screen_img, template_name, **kw):
            if template_name == "common/quit.png":
                return ((700, 100), 0.90)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match

        # 模擬當前時間為 101.0 秒 (經過 1.0 秒)
        with patch("states.handlers.bulletin_board.time.time", return_value=101.0), \
             patch.object(self.handler, "click_and_wait_until_gone") as mock_wait_gone:
            self.handler.handle(self.fake_img, self.rect)

            # 斷言：絕不可呼叫關閉按鈕，維持在 WAIT_BOARD_OPEN
            mock_wait_gone.assert_not_called()
            self.assertEqual(self.handler.step_phase, "WAIT_BOARD_OPEN")

    def test_wait_board_open_transitions_immediately_when_board_detected(self):
        """
        [契約 2 驗證] 處於 WAIT_BOARD_OPEN 時，只要告示牌專屬特徵 (如 reset.png) 一出現，
        立即推進至 CHECK_RESET，完全零延遲。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.wait_board_open_start_time = 100.0

        # 模擬畫面：同時有 quit.png 與 reset.png
        def mock_match(screen_img, template_name, **kw):
            if template_name == "common/quit.png":
                return ((700, 100), 0.90)
            elif template_name == "town_building/bulletin_board/reset.png":
                return ((300, 500), 0.90)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match

        with patch("states.handlers.bulletin_board.time.time", return_value=100.5):
            self.handler.handle(self.fake_img, self.rect)

            # 斷言：立即切換至 CHECK_RESET
            self.assertEqual(self.handler.step_phase, "CHECK_RESET")
            self.mock_machine.notify_ui_progress.assert_called_once()

    def test_wait_board_open_dismisses_overlay_after_timeout(self):
        """
        [契約 3 驗證] 處於 WAIT_BOARD_OPEN 且經過時間超過 2.5 秒 (如 103.0 秒)，
        若畫面依然只有 quit.png 且無任何告示牌特徵，判定為非告示牌之殘留干擾覆蓋層，
        觸發 click_and_wait_until_gone 關閉並退回 INIT 重試。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.wait_board_open_start_time = 100.0

        def mock_match(screen_img, template_name, **kw):
            if template_name == "common/quit.png":
                return ((700, 100), 0.90)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match

        # 模擬當前時間為 103.0 秒 (經過 3.0 秒 > 2.5 秒)
        with patch("states.handlers.bulletin_board.time.time", return_value=103.0), \
             patch.object(self.handler, "click_and_wait_until_gone") as mock_wait_gone:
            self.handler.handle(self.fake_img, self.rect)

            # 斷言：超時後判定為干擾覆蓋層並閉環關閉，退回 INIT
            mock_wait_gone.assert_called_once_with("common/quit.png", 700, 100, self.rect, timeout=3.0, threshold=0.80)
            self.assertEqual(self.handler.step_phase, "INIT")

    def test_wait_board_open_hard_timeout_recovers_to_init(self):
        """
        [契約 4 驗證] 處於 WAIT_BOARD_OPEN 且超過 5.0 秒，畫面完全未見任何彈窗 (quit.png 都沒出現)，
        判定進店點擊遺失，自癒退回 INIT 重新發起進店。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.wait_board_open_start_time = 100.0

        # 模擬畫面：完全沒有 quit.png，可能還在城鎮
        def mock_match(screen_img, template_name, **kw):
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match

        # 模擬當前時間為 106.0 秒 (經過 6.0 秒 > 5.0 秒)
        with patch("states.handlers.bulletin_board.time.time", return_value=106.0):
            self.handler.handle(self.fake_img, self.rect)

            # 斷言：硬逾時退回 INIT 重新發起進店
            self.assertEqual(self.handler.step_phase, "INIT")

    def test_is_inside_bulletin_board_with_before_only(self):
        """
        [契約 5 驗證] 驗證 Before 獨立通道：
        當剛進告示牌且任務全未接取時，畫面上只有 task.png (Before)，無 reset 與 task_after。
        只要 task.png 信心度 >= 0.70，單憑此特徵即可判定身處告示牌。
        """
        def mock_match(screen_img, template_name, **kw):
            if template_name == "common/quit.png":
                return ((700, 100), 0.90)
            elif template_name == "town_building/bulletin_board/task.png":
                return ((200, 300), 0.72)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match
        self.assertTrue(self.handler._is_inside_bulletin_board(self.fake_img, self.mock_machine.config))

    def test_is_inside_bulletin_board_with_after_only(self):
        """
        [契約 6 驗證] 驗證 After 獨立通道：
        當所有任務皆已接取時，畫面上只有 task_after.png (After)，無 reset 與 task.png。
        只要 task_after.png 信心度 >= 0.70，單憑此特徵即可判定身處告示牌。
        """
        def mock_match(screen_img, template_name, **kw):
            if template_name == "common/quit.png":
                return ((700, 100), 0.90)
            elif template_name == "town_building/bulletin_board/task_after.png":
                return ((200, 300), 0.72)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match
        self.assertTrue(self.handler._is_inside_bulletin_board(self.fake_img, self.mock_machine.config))


if __name__ == "__main__":
    unittest.main()
