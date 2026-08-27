import unittest
from unittest.mock import MagicMock, patch
import time

from states.state_machine import GameStateMachine
from utils.keyboard_listener import (
    PauseController,
    TRIGGER_MODE_CTRL_SPACE,
    TRIGGER_MODE_TRIPLE_SPACE,
    VK_CONTROL,
    VK_SPACE
)

class TestBehaviorPauseResume(unittest.TestCase):
    """
    測試可插拔熱鍵策略 (Ctrl+Space / Triple-Space)、背景執行緒與內部計時器補償行為
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_capturer.hwnd = 12345
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.state_machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)

    def test_pause_resume_lifecycle(self):
        """
        測試基本 pause / resume / toggle_pause 狀態機生命週期
        """
        self.assertFalse(self.state_machine.is_paused)
        self.assertIsNone(self.state_machine.pause_start_time)

        # 1. 觸發暫停
        self.state_machine.pause()
        self.assertTrue(self.state_machine.is_paused)
        self.assertIsNotNone(self.state_machine.pause_start_time)

        # 2. 觸發恢復
        duration = self.state_machine.resume()
        self.assertFalse(self.state_machine.is_paused)
        self.assertIsNone(self.state_machine.pause_start_time)
        self.assertTrue(self.state_machine.just_resumed_from_user)
        self.assertGreaterEqual(duration, 0.0)

        # 3. 測試 toggle_pause
        is_paused = self.state_machine.toggle_pause()
        self.assertTrue(is_paused)
        self.assertTrue(self.state_machine.is_paused)

        is_paused = self.state_machine.toggle_pause()
        self.assertFalse(is_paused)
        self.assertFalse(self.state_machine.is_paused)

    def test_internal_timers_compensation_math(self):
        """
        測試內部安全/防卡死計時器的精確數學補償
        """
        self.state_machine.last_state_change = 1000.0
        self.state_machine.battle_start_time = 900.0
        self.state_machine.stashed_context = {"timestamp": 950.0}
        self.state_machine.missing_time_common_door = 800.0

        loading_handler = self.state_machine.handlers.get(self.state_machine.STATE_LOADING)
        if loading_handler:
            loading_handler.loading_start_time = 700.0

        battle_handler = self.state_machine.handlers.get(self.state_machine.STATE_BATTLE)
        if battle_handler:
            battle_handler.non_battle_feature_start_time = 850.0

        # 執行 120 秒補償
        self.state_machine.compensate_internal_timers(120.0)

        self.assertEqual(self.state_machine.last_state_change, 1120.0)
        self.assertEqual(self.state_machine.battle_start_time, 1020.0)
        self.assertEqual(self.state_machine.stashed_context["timestamp"], 1070.0)
        self.assertEqual(self.state_machine.missing_time_common_door, 920.0)

        if loading_handler:
            self.assertEqual(loading_handler.loading_start_time, 820.0)
        if battle_handler:
            self.assertEqual(battle_handler.non_battle_feature_start_time, 970.0)

        self.assertFalse(self.state_machine.user_operating)
        self.assertTrue(self.state_machine.just_resumed_from_user)

    def test_game_cooldowns_not_affected(self):
        """
        【關鍵邊界保護】驗證客觀遊戲數據與冷卻時間絕不被手動暫停補償篡改
        """
        self.state_machine.dungeon_cooldowns = {0: 500.0, 1: 600.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.state_machine.last_bread_collection_time = 700.0
        self.state_machine.last_diamond_collection_time = 800.0

        # 執行 300 秒長暫停補償
        self.state_machine.compensate_internal_timers(300.0)

        # 斷言客觀遊戲冷卻時間完全未受影響
        self.assertEqual(self.state_machine.dungeon_cooldowns[0], 500.0)
        self.assertEqual(self.state_machine.dungeon_cooldowns[1], 600.0)
        self.assertEqual(self.state_machine.last_bread_collection_time, 700.0)
        self.assertEqual(self.state_machine.last_diamond_collection_time, 800.0)

    def test_watchdog_immunity_after_long_pause(self):
        """
        測試暫停超過 90 秒後恢復，Watchdog 絕對不會因停滯誤判為卡死
        """
        now = time.time()
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.last_state_change = now - 40.0

        self.state_machine.pause()
        self.state_machine.pause_start_time = now - 120.0
        self.state_machine.resume()

        is_stuck = self.state_machine.exception_watchdog.check(None)
        self.assertFalse(is_stuck)

    @patch("ctypes.windll.user32.GetForegroundWindow")
    @patch("ctypes.windll.kernel32.GetConsoleWindow")
    @patch("ctypes.windll.user32.GetAsyncKeyState")
    def test_ctrl_space_trigger(self, mock_get_async_key, mock_get_console, mock_get_fg):
        """
        測試 Ctrl + Space 組合鍵單次觸發機制
        """
        mock_get_console.return_value = 11111
        mock_get_fg.return_value = 11111

        controller = PauseController(capturer=self.mock_capturer, trigger_mode=TRIGGER_MODE_CTRL_SPACE, start_thread=False)

        def mock_key_side_effect(vk):
            if vk == VK_CONTROL:
                return 0x8000 # Ctrl 按下
            if vk == VK_SPACE:
                return 0x8000 # Space 按下
            return 0x0

        mock_get_async_key.side_effect = mock_key_side_effect

        # 同時按下 Ctrl + Space -> 立即觸發
        res = controller._poll_once(time.time())
        self.assertTrue(res)
        self.assertTrue(controller.check_toggle_triggered())

    def test_triple_space_cadence_interval_success(self):
        """
        測試 Triple-Space 相鄰節奏間隔小於 1.5 秒時連按 3 次觸發
        """
        controller = PauseController(capturer=self.mock_capturer, trigger_mode=TRIGGER_MODE_TRIPLE_SPACE, cadence_timeout_sec=1.5, start_thread=False)

        res1 = controller._on_triple_tap_registered(100.0)
        self.assertFalse(res1)
        self.assertEqual(controller.tap_count, 1)

        res2 = controller._on_triple_tap_registered(100.8)
        self.assertFalse(res2)
        self.assertEqual(controller.tap_count, 2)

        res3 = controller._on_triple_tap_registered(101.6)
        self.assertTrue(res3)
        self.assertEqual(controller.tap_count, 0)
        self.assertTrue(controller.check_toggle_triggered())

    def test_set_trigger_mode_switch(self):
        """
        測試動態切換熱鍵策略模式
        """
        controller = PauseController(capturer=self.mock_capturer, trigger_mode=TRIGGER_MODE_CTRL_SPACE, start_thread=False)
        self.assertEqual(controller.trigger_mode, TRIGGER_MODE_CTRL_SPACE)
        self.assertIn("Ctrl + Space", controller.get_trigger_hint())

        controller.set_trigger_mode(TRIGGER_MODE_TRIPLE_SPACE)
        self.assertEqual(controller.trigger_mode, TRIGGER_MODE_TRIPLE_SPACE)
        self.assertIn("3 次", controller.get_trigger_hint())

    @patch("ctypes.windll.user32.GetForegroundWindow")
    @patch("ctypes.windll.kernel32.GetConsoleWindow")
    @patch("ctypes.windll.user32.GetAsyncKeyState")
    def test_focus_window_filter(self, mock_get_async_key, mock_get_console, mock_get_fg):
        """
        測試視窗焦點過濾：前景視窗為第三方視窗時被 100% 過濾
        """
        mock_get_console.return_value = 11111
        mock_get_fg.return_value = 99999 # 瀏覽器等非目標視窗
        mock_get_async_key.return_value = 0x8000

        controller = PauseController(capturer=self.mock_capturer, start_thread=False)
        controller._poll_once()

        self.assertFalse(controller.check_toggle_triggered())

    @patch("ctypes.windll.user32.GetForegroundWindow")
    @patch("ctypes.windll.kernel32.GetConsoleWindow")
    @patch("ctypes.windll.user32.GetWindowTextW")
    @patch("ctypes.windll.user32.GetWindowTextLengthW")
    @patch("ctypes.windll.user32.GetClassNameW")
    @patch("ctypes.windll.user32.GetWindowThreadProcessId")
    def test_focus_filter_rejects_vscode_chrome_and_explorer(
        self, mock_get_pid, mock_get_class, mock_get_len, mock_get_text, mock_get_console, mock_get_fg
    ):
        """
        【防誤觸關鍵測試】驗證包含 'python', 'BlackfireCrusade_tool', 'terminal' 關鍵字的
        VS Code、Chrome 瀏覽器與檔案總管視窗均被 100% 精準拒絕，絕不觸發暫停快捷鍵。
        """
        mock_get_console.return_value = 11111
        mock_get_fg.return_value = 77777 # 第三方視窗 HWND
        mock_get_pid.side_effect = lambda hwnd, byref_pid: None # PID 不匹配

        controller = PauseController(capturer=self.mock_capturer, start_thread=False)

        # 案例 1: VS Code 視窗 (標題包含 python 與專案路徑 BlackfireCrusade_tool)
        def mock_vscode_title(hwnd, buff, length):
            buff.value = "keyboard_listener.py - BlackfireCrusade_tool - Visual Studio Code"
            return len(buff.value)

        mock_get_len.return_value = 60
        mock_get_text.side_effect = mock_vscode_title
        mock_get_class.side_effect = lambda hwnd, buff, length: setattr(buff, "value", "Chrome_WidgetWin_1")

        self.assertFalse(controller.is_console_window_active())
        self.assertFalse(controller.is_game_window_active())
        self.assertFalse(controller.is_target_window_active())

        # 案例 2: Chrome 瀏覽器 (標題包含 Python Tutorial)
        def mock_chrome_title(hwnd, buff, length):
            buff.value = "Python 3 Tutorial & Reference - Google Chrome"
            return len(buff.value)

        mock_get_text.side_effect = mock_chrome_title
        mock_get_class.side_effect = lambda hwnd, buff, length: setattr(buff, "value", "Chrome_WidgetWin_1")

        self.assertFalse(controller.is_console_window_active())
        self.assertFalse(controller.is_game_window_active())
        self.assertFalse(controller.is_target_window_active())

        # 案例 3: 檔案總管 (標題為 BlackfireCrusade_tool)
        def mock_explorer_title(hwnd, buff, length):
            buff.value = "BlackfireCrusade_tool"
            return len(buff.value)

        mock_get_text.side_effect = mock_explorer_title
        mock_get_class.side_effect = lambda hwnd, buff, length: setattr(buff, "value", "CabinetWClass")

        self.assertFalse(controller.is_console_window_active())
        self.assertFalse(controller.is_game_window_active())
        self.assertFalse(controller.is_target_window_active())

    @patch("ctypes.windll.user32.GetForegroundWindow")
    @patch("ctypes.windll.kernel32.GetConsoleWindow")
    def test_focus_filter_accepts_console_by_hwnd(self, mock_get_console, mock_get_fg):
        """
        測試前景 HWND 與 GetConsoleWindow() 相符時精準判定為目標視窗
        """
        mock_get_console.return_value = 12345
        mock_get_fg.return_value = 12345

        controller = PauseController(capturer=self.mock_capturer, start_thread=False)
        self.assertTrue(controller.is_console_window_active())
        self.assertTrue(controller.is_target_window_active())

    @patch("ctypes.windll.user32.GetForegroundWindow")
    @patch("ctypes.windll.kernel32.GetConsoleWindow")
    @patch("ctypes.windll.user32.GetWindowThreadProcessId")
    @patch("os.getpid")
    def test_focus_filter_accepts_console_by_pid(self, mock_getpid, mock_get_pid, mock_get_console, mock_get_fg):
        """
        測試前景視窗進程 PID 與當前 Python 進程 PID 相符時精準判定為目標視窗
        """
        mock_get_console.return_value = 99999
        mock_get_fg.return_value = 88888
        mock_getpid.return_value = 5555

        def mock_pid_fill(hwnd, byref_pid):
            byref_pid._obj.value = 5555
            return 1

        mock_get_pid.side_effect = mock_pid_fill

        controller = PauseController(capturer=self.mock_capturer, start_thread=False)
        self.assertTrue(controller.is_console_window_active())
        self.assertTrue(controller.is_target_window_active())

    @patch("ctypes.windll.user32.GetForegroundWindow")
    def test_focus_filter_accepts_game_by_hwnd(self, mock_get_fg):
        """
        測試前景 HWND 與 capturer.hwnd 相符時精準判定為目標視窗
        """
        mock_get_fg.return_value = 12345 # 與 self.mock_capturer.hwnd 一致

        controller = PauseController(capturer=self.mock_capturer, start_thread=False)
        self.assertTrue(controller.is_game_window_active())
        self.assertTrue(controller.is_target_window_active())


    def test_mouse_click_aborts_immediately_when_state_machine_is_paused(self):
        """
        【雙層防護驗證】測試當 is_paused_fn() == True 時，
        底層 mouse.click() / mouse.drag() 於發射前透過 check_user_intervention() 立刻熔斷攔截。
        """
        from actions.mouse import MouseController

        # 以可變旗標模擬 state_machine.is_paused 的切換 (Issue #11 callback 接線)
        paused_flag = [False]
        mouse = MouseController(human_like=False, is_paused_fn=lambda: paused_flag[0])

        # 1. 正常運行狀態 (is_paused_fn 回傳 False) -> check_user_intervention 應為 False
        paused_flag[0] = False
        self.assertFalse(mouse.check_user_intervention())

        # 2. 手動暫停狀態 (is_paused_fn 回傳 True) -> check_user_intervention 應為 True，且 click() 直接回傳 False
        paused_flag[0] = True
        self.assertTrue(mouse.check_user_intervention())

        # 呼叫 click 應被立即攔截拒絕
        res_click = mouse.click(500, 500)
        self.assertFalse(res_click)

        # 呼叫 drag 應被立即攔截拒絕
        res_drag = mouse.drag(500, 500, 600, 600)
        self.assertFalse(res_drag)


    def test_mouse_freeze_in_place_with_resume_event(self):
        """
        【門閥定格驗證】驗證 MouseController 搭配 resume_event 時：
        1. 在暫停 (clear) 期間，動作執行緒在 _wait_if_paused() 原地定格等待；
        2. 當上層觸發恢復 (set) 時，動作執行緒立即解除定格並順利放行執行。
        """
        import threading
        from actions.mouse import MouseController

        resume_event = threading.Event()
        resume_event.set() # 預設放行
        mouse = MouseController(human_like=False, resume_event=resume_event)

        # 1. 正常放行狀態
        with patch.object(mouse, '_finalize_action', return_value=True):
            with patch('pyautogui.moveTo'), patch('pyautogui.mouseDown'), patch('pyautogui.mouseUp'):
                res = mouse.click(100, 200)
                self.assertTrue(res)

        # 2. 測試阻斷與恢復
        resume_event.clear() # 阻斷
        execution_order = []

        def worker():
            execution_order.append("start")
            with patch.object(mouse, '_finalize_action', return_value=True):
                with patch('pyautogui.moveTo'), patch('pyautogui.mouseDown'), patch('pyautogui.mouseUp'):
                    mouse.click(100, 200)
            execution_order.append("finished")

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.05)

        # 斷言：執行緒在暫停期間處於定格等待，尚未完成
        self.assertEqual(execution_order, ["start"])
        self.assertTrue(t.is_alive())

        # 恢復放行
        resume_event.set()
        t.join(timeout=1.0)

        # 斷言：恢復後順利放行完畢
        self.assertEqual(execution_order, ["start", "finished"])

    def test_click_and_wait_until_gone_freezes_on_pause(self):
        """
        【輪詢定格驗證】驗證 BaseStateHandler.click_and_wait_until_gone 在輪詢途中若被暫停，
        會在 resume_event.wait() 原地等待，不盲目發起補點擊或超時。
        """
        import threading
        from states.handlers.base import BaseStateHandler

        class DummyHandler(BaseStateHandler):
            def handle(self, screen_img, rect):
                pass

        handler = DummyHandler(self.state_machine)
        self.state_machine.resume_event.set()

        # 暫停狀態機
        self.state_machine.pause()
        self.assertFalse(self.state_machine.resume_event.is_set())

        execution_order = []

        def worker():
            execution_order.append("waiting_start")
            with patch.object(handler.mouse, 'click'):
                with patch('os.path.exists', return_value=True):
                    self.mock_capturer.capture.return_value = "dummy_img"
                    self.mock_matcher.match.return_value = (None, 0.0) # 消失
                    handler.click_and_wait_until_gone(
                        "common/quit.png", 100, 200, 
                        {"left": 0, "top": 0, "width": 800, "height": 600}, 
                        timeout=1.0, check_interval=0.02, post_delay=0.0
                    )
            execution_order.append("waiting_done")

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.05)

        # 斷言：輪詢在暫停狀態下被定格
        self.assertEqual(execution_order, ["waiting_start"])
        self.assertTrue(t.is_alive())

        # 恢復狀態機
        self.state_machine.resume()
        t.join(timeout=2.0)

        # 斷言：恢復後完成輪詢退出
        self.assertEqual(execution_order, ["waiting_start", "waiting_done"])


    def test_pause_controller_instant_callback_triggers_state_machine_pause(self):
        """
        【即時回調定格驗證】驗證 PauseController 捕獲熱鍵時直接呼叫 on_toggle 回調，
        使 state_machine 在背景執行緒中立即 pause() 並阻斷 resume_event，
        進而使主執行緒正在執行的動作瞬間原地定格！
        """
        import threading
        from actions.mouse import MouseController

        mouse = MouseController(human_like=False, resume_event=self.state_machine.resume_event)
        self.state_machine.resume_event.set()
        self.assertFalse(self.state_machine.is_paused)

        # 建立附帶 on_toggle 的 PauseController (非執行緒模式以便精確測試單步 poll)
        controller = PauseController(capturer=self.mock_capturer, start_thread=False, on_toggle=self.state_machine.toggle_pause)

        # 模擬正在背景執行的滑鼠動作
        execution_order = []

        def worker_loop():
            execution_order.append("step_1_done")
            with patch.object(mouse, '_finalize_action', return_value=True):
                with patch('pyautogui.moveTo'), patch('pyautogui.mouseDown'), patch('pyautogui.mouseUp'):
                    mouse.click(100, 100) # 此動作應可正常通過
            execution_order.append("step_2_entering")
            with patch.object(mouse, '_finalize_action', return_value=True):
                with patch('pyautogui.moveTo'), patch('pyautogui.mouseDown'), patch('pyautogui.mouseUp'):
                    mouse.click(200, 200) # 此動作將在暫停後被阻斷定格
            execution_order.append("step_2_finished")

        # 觸發熱鍵暫停
        with patch.object(controller, 'is_target_window_active', return_value=True):
            with patch('ctypes.windll.user32.GetAsyncKeyState', side_effect=lambda vk: 0x8000 if vk in (VK_CONTROL, VK_SPACE) else 0):
                controller._poll_once(time.time())

        # 斷言：狀態機已被即時回調暫停，門閥已關閉
        self.assertTrue(self.state_machine.is_paused)
        self.assertFalse(self.state_machine.resume_event.is_set())

        # 啟動 worker 執行緒
        t = threading.Thread(target=worker_loop)
        t.start()
        time.sleep(0.05)

        # 斷言：worker 在進入第 1 個動作時直接在 _wait_if_paused 定格
        self.assertEqual(execution_order, ["step_1_done"])
        self.assertTrue(t.is_alive())

        # 模擬按鍵釋放 (key_pressed 復位)
        with patch.object(controller, 'is_target_window_active', return_value=True):
            with patch('ctypes.windll.user32.GetAsyncKeyState', return_value=0):
                controller._poll_once(time.time() + 0.2)

        # 再次觸發熱鍵恢復
        with patch.object(controller, 'is_target_window_active', return_value=True):
            with patch('ctypes.windll.user32.GetAsyncKeyState', side_effect=lambda vk: 0x8000 if vk in (VK_CONTROL, VK_SPACE) else 0):
                controller._poll_once(time.time() + 1.0)

        # 斷言：狀態機已恢復
        self.assertFalse(self.state_machine.is_paused)
        self.assertTrue(self.state_machine.resume_event.is_set())

        t.join(timeout=1.0)
        self.assertEqual(execution_order, ["step_1_done", "step_2_entering", "step_2_finished"])


if __name__ == "__main__":
    unittest.main()


