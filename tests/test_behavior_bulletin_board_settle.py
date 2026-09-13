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

    def _make_mock_match(self, quit=True, reset=False, task=False, task_after=False, tidy=False, disasm=False):
        """輔助 mock matcher，根據 ROI 幾何回傳正確的局部座標"""
        def mock_match(screen_img, template_name, **kw):
            if template_name == "common/quit.png" and quit:
                # quit_roi x starts at 400 for 800px width. Local 300 => Global 700
                is_roi = screen_img.shape[1] < 800
                return ((300, 100) if is_roi else (700, 100), 0.90)
            elif template_name == "town_building/bulletin_board/reset.png" and reset:
                # reset_roi y starts at 360 for 600px height. Local (300, 140) => Global (300, 500)
                is_roi = screen_img.shape[0] < 600
                return ((300, 140) if is_roi else (300, 500), 0.90)
            elif template_name == "town_building/bulletin_board/task.png" and task:
                return ((200, 300), 0.72)
            elif template_name == "town_building/bulletin_board/task_after.png" and task_after:
                return ((200, 300), 0.72)
            elif template_name == "common/tidy.png" and tidy:
                return ((500, 400), 0.88)
            elif template_name == "common/Disassembly.png" and disasm:
                return ((600, 400), 0.88)
            return (None, 0.0)
        return mock_match

    def test_wait_board_open_does_not_kill_overlay_during_settle_window(self):
        """
        [契約 1 驗證] 剛進入 WAIT_BOARD_OPEN 時 (經過 1.0 秒 < 2.5 秒)，
        即使畫面偵測到 quit.png 但告示牌專屬特徵尚未就緒 (動畫過渡期)，
        絕不觸發關閉覆蓋層，維持在 WAIT_BOARD_OPEN 靜待沉澱。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.wait_board_open_start_time = 100.0
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True)

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
        立即推進至 CHECK_RESET，重置 open_attempts，完全零延遲。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.wait_board_open_start_time = 100.0
        self.handler.open_attempts = 1
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True, reset=True)

        with patch("states.handlers.bulletin_board.time.time", return_value=100.5):
            self.handler.handle(self.fake_img, self.rect)

            # 斷言：立即切換至 CHECK_RESET 且 open_attempts 重置為 0
            self.assertEqual(self.handler.step_phase, "CHECK_RESET")
            self.assertEqual(self.handler.open_attempts, 0)
            self.mock_machine.notify_ui_progress.assert_called_once()

    def test_wait_board_open_unknown_overlay_single_retry_recovers_to_init(self):
        """
        [契約 3 驗證] 處於 WAIT_BOARD_OPEN 且經過時間超過 2.5 秒 (如 103.0 秒)，
        若畫面只有 quit.png 且無任何告示牌正向特徵亦非背包，判定為 UNKNOWN_OVERLAY，
        關閉後進行有界重試 (open_attempts + 1)，未超限前退回 INIT。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.wait_board_open_start_time = 100.0
        self.handler.open_attempts = 0
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True)

        with patch("states.handlers.bulletin_board.time.time", return_value=103.0), \
             patch.object(self.handler, "click_and_wait_until_gone") as mock_wait_gone:
            self.handler.handle(self.fake_img, self.rect)

            # 斷言：關閉未知覆蓋層，open_attempts 計入 1，退回 INIT
            mock_wait_gone.assert_called_once_with("common/quit.png", 700, 100, self.rect, timeout=3.0, threshold=0.80)
            self.assertEqual(self.handler.open_attempts, 1)
            self.assertEqual(self.handler.step_phase, "INIT")

    def test_wait_board_open_known_interference_dismisses_immediately(self):
        """
        [契約 4 驗證] 處於 WAIT_BOARD_OPEN 時，若偵測到 quit.png 且有明確背包特徵 (tidy.png)，
        立即判定為 KNOWN_INTERFERENCE，閉環關閉以利重試。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.wait_board_open_start_time = 100.0
        self.handler.open_attempts = 0
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True, tidy=True)

        with patch("states.handlers.bulletin_board.time.time", return_value=101.0), \
             patch.object(self.handler, "click_and_wait_until_gone") as mock_wait_gone:
            self.handler.handle(self.fake_img, self.rect)

            # 斷言：判定為干擾層立即關閉，退回 INIT，不需等待 2.5 秒沉澱
            mock_wait_gone.assert_called_once_with("common/quit.png", 700, 100, self.rect, timeout=3.0, threshold=0.80)
            self.assertEqual(self.handler.open_attempts, 1)
            self.assertEqual(self.handler.step_phase, "INIT")

    def test_unknown_overlay_exceeds_budget_defers_and_pops_subflow(self):
        """
        [契約 5 驗證 - Anti-Livelock] 連續 UNKNOWN_OVERLAY 達到 MAX_OPEN_ATTEMPTS 上限時，
        系統主動觸發 defer_subflow 並 pop_and_next_town_subflow，絕不陷入無限閉環死鎖。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.wait_board_open_start_time = 100.0
        self.handler.open_attempts = 1  # 已經嘗試過 1 次
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True)

        with patch("states.handlers.bulletin_board.time.time", return_value=103.0), \
             patch.object(self.handler, "click_and_wait_until_gone") as mock_wait_gone:
            self.handler.handle(self.fake_img, self.rect)

            # 斷言：關閉彈窗
            mock_wait_gone.assert_called_once()
            # 斷言：調用 defer_subflow 180 秒冷卻退避
            self.mock_machine.daily_manager.defer_subflow.assert_called_once_with("bulletin_board", 180)
            # 斷言：消費佇列切換下一個任務
            self.mock_machine.pop_and_next_town_subflow.assert_called_once()

    def test_wait_board_open_hard_timeout_single_retry_recovers_to_init(self):
        """
        [契約 6 驗證] 處於 WAIT_BOARD_OPEN 且超過 5.0 秒，畫面完全未見任何彈窗 (quit.png 都沒出現)，
        判定進店點擊遺失，未達上限前自癒退回 INIT 重新發起進店。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.click_building_time = 100.0
        self.handler.open_attempts = 0
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=False)

        with patch("states.handlers.bulletin_board.time.time", return_value=106.0):
            self.handler.handle(self.fake_img, self.rect)

            # 斷言：硬逾時退回 INIT 重新發起進店，嘗試次數累加
            self.assertEqual(self.handler.open_attempts, 1)
            self.assertEqual(self.handler.step_phase, "INIT")

    def test_hard_timeout_exceeds_budget_defers_and_pops_subflow(self):
        """
        [契約 7 驗證 - Anti-Livelock] 點擊建築開窗連續逾時達到 MAX_OPEN_ATTEMPTS 上限，
        觸發 defer_subflow 並切換佇列。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.click_building_time = 100.0
        self.handler.open_attempts = 1
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=False)

        with patch("states.handlers.bulletin_board.time.time", return_value=106.0):
            self.handler.handle(self.fake_img, self.rect)

            self.mock_machine.daily_manager.defer_subflow.assert_called_once_with("bulletin_board", 180)
            self.mock_machine.pop_and_next_town_subflow.assert_called_once()

    def test_is_inside_bulletin_board_with_before_only(self):
        """
        [契約 8 驗證] 驗證 Before 獨立通道：
        當剛進告示牌且任務全未接取時，畫面上只有 task.png (Before)，無 reset 與 task_after。
        只要 task.png 信心度 >= 0.70，單憑此特徵即可判定身處告示牌。
        """
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True, task=True)
        self.assertTrue(self.handler._is_inside_bulletin_board(self.fake_img, self.mock_machine.config))

    def test_is_inside_bulletin_board_with_after_only(self):
        """
        [契約 9 驗證] 驗證 After 獨立通道：
        當所有任務皆已接取時，畫面上只有 task_after.png (After)，無 reset 與 task.png。
        只要 task_after.png 信心度 >= 0.70，單憑此特徵即可判定身處告示牌。
        """
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True, task_after=True)
        self.assertTrue(self.handler._is_inside_bulletin_board(self.fake_img, self.mock_machine.config))

    def test_observe_bulletin_board_classification_semantics(self):
        """
        [契約 10 驗證] 驗證 observe_bulletin_board 之四種分類語意
        """
        from utils.bulletin_board_detector import observe_bulletin_board

        # 1. NO_OVERLAY
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=False)
        obs1 = observe_bulletin_board(self.fake_img, self.handler.matcher, self.mock_machine.config)
        self.assertEqual(obs1.classification, "NO_OVERLAY")

        # 2. KNOWN_INTERFERENCE
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True, tidy=True)
        obs2 = observe_bulletin_board(self.fake_img, self.handler.matcher, self.mock_machine.config)
        self.assertEqual(obs2.classification, "KNOWN_INTERFERENCE")
        self.assertTrue(obs2.has_bag)

        # 3. UNKNOWN_OVERLAY
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True)
        obs3 = observe_bulletin_board(self.fake_img, self.handler.matcher, self.mock_machine.config)
        self.assertEqual(obs3.classification, "UNKNOWN_OVERLAY")
        self.assertFalse(obs3.has_bag)

        # 4. BOARD_CONFIRMED
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True, reset=True)
        obs4 = observe_bulletin_board(self.fake_img, self.handler.matcher, self.mock_machine.config)
        self.assertEqual(obs4.classification, "BOARD_CONFIRMED")

    def test_feature_evidence_roi_miss_with_global_hit_never_passes_decision(self):
        """
        [契約 11 驗證 - 決策與診斷嚴格分離]
        當模板在預期 ROI 內 miss (例如 task 在左側只有 0.40)，但畫面右側 (ROI 外部) 出現高相似度 (0.85)：
        決策模型絕不得判定為通過 (passed 必為 False, 分類必為 UNKNOWN_OVERLAY)！
        且診斷資訊必須正確標註 STRONG_MATCH_OUTSIDE_EXPECTED_ROI。
        """
        from utils.bulletin_board_detector import observe_bulletin_board

        def mock_match_roi_miss_global_hit(img, template_name, threshold=0.65, **kw):
            if template_name == "common/quit.png":
                return ((700, 100), 0.90)
            elif template_name == "town_building/bulletin_board/task.png":
                # 若傳入為 ROI 局部圖 (寬度 < 800)，回傳低分未通過
                if img.shape[1] < 800:
                    return (None, 0.40)
                # 若傳入為全圖 (寬度 == 800)，在右側 (X=700 > 480) 出現強干擾
                return ((700, 300), 0.85)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match_roi_miss_global_hit
        obs = observe_bulletin_board(self.fake_img, self.handler.matcher, self.mock_machine.config)

        # 斷言：決策絕不可通過
        self.assertEqual(obs.classification, "UNKNOWN_OVERLAY")
        ev_task = obs.evidence_map["task"]
        self.assertFalse(ev_task.passed)
        self.assertEqual(ev_task.primary_reason, "STRONG_MATCH_OUTSIDE_EXPECTED_ROI")
        self.assertIn("STRONG_MATCH_OUTSIDE_EXPECTED_ROI", ev_task.diagnostic_flags)
        self.assertEqual(ev_task.global_position, (700, 300))
        self.assertGreaterEqual(ev_task.global_score, 0.80)

    def test_feature_evidence_near_threshold_diagnosis(self):
        """
        [契約 12 驗證 - Near Miss 語意診斷]
        當 ROI 比對分數僅差 threshold <= 0.05 (例如 threshold 0.65, 觀測 0.62)：
        passed 為 False，但 primary_reason 必須標註為 NEAR_THRESHOLD。
        """
        from utils.bulletin_board_detector import observe_bulletin_board

        def mock_match_near_miss(img, template_name, threshold=0.65, **kw):
            if template_name == "common/quit.png":
                return ((700, 100), 0.90)
            elif template_name == "town_building/bulletin_board/task.png":
                return (None, 0.62)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match_near_miss
        obs = observe_bulletin_board(self.fake_img, self.handler.matcher, self.mock_machine.config)

        ev_task = obs.evidence_map["task"]
        self.assertFalse(ev_task.passed)
        self.assertEqual(ev_task.primary_reason, "NEAR_THRESHOLD")

    def test_diagnostic_report_formatting(self):
        """
        [契約 13 驗證 - 結構化診斷日誌格式]
        驗證 format_diagnostic_report 包含 Gate, Positive evidence, Negative evidence,
        Likely diagnosis, Candidate scales 與 Best scale。
        """
        from utils.bulletin_board_detector import observe_bulletin_board

        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True)
        obs = observe_bulletin_board(self.fake_img, self.handler.matcher, self.mock_machine.config)

        report = obs.diagnostic_report
        self.assertIn("[BulletinBoardDetector] classification=UNKNOWN_OVERLAY", report)
        self.assertIn("Gate:\n  quit: PASS", report)
        self.assertIn("Positive evidence:", report)
        self.assertIn("Negative evidence:", report)
        self.assertIn("bag_tidy: ABSENT", report)
        self.assertIn("Candidate scales:", report)
        self.assertIn("Best scale: unavailable", report)

    def test_suspected_target_overlay_logging(self):
        """
        [契約 14 驗證 - SUSPECTED_TARGET_OVERLAY 因果語意]
        在點擊建築後進入 WAIT_BOARD_OPEN，若出現 quit 且無背包特徵但缺乏正向特徵：
        日誌必須包含 SUSPECTED_TARGET_OVERLAY 標籤並輸出 diagnostic_report。
        """
        self.handler.step_phase = "WAIT_BOARD_OPEN"
        self.handler.click_building_time = 100.0  # 剛點擊過告示牌建築
        self.handler.wait_board_open_start_time = 100.0
        self.handler.open_attempts = 0
        self.handler.matcher.match.side_effect = self._make_mock_match(quit=True)

        with patch("states.handlers.bulletin_board.time.time", return_value=103.0), \
             patch.object(self.handler, "click_and_wait_until_gone") as mock_wait_gone, \
             patch("states.handlers.bulletin_board.logging.warning") as mock_log_warn:
            self.handler.handle(self.fake_img, self.rect)

            # 斷言：日誌中包含 SUSPECTED_TARGET_OVERLAY
            has_suspected_tag = any("SUSPECTED_TARGET_OVERLAY" in str(c) for c in mock_log_warn.call_args_list)
            self.assertTrue(has_suspected_tag)


if __name__ == "__main__":
    unittest.main()
