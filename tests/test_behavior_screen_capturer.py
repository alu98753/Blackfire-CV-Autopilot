"""
test_behavior_screen_capturer.py — Issue #4 行為守護測試

T4-A: 視窗已在目標顯示器且已最大化 → 立即 return True，不觸碰 Win32 API
T4-B: 視窗在目標顯示器但未最大化 → 只 maximize，不 SetWindowPos
T4-C: 視窗最小化（IsIconic）→ 先 SW_RESTORE 再移動再最大化
T4-D: 無效 monitor_index → 立即 return False
"""
import unittest
from unittest.mock import patch, call, MagicMock
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capture.screen import ScreenCapturer
import win32con


def _make_capturer():
    return ScreenCapturer(window_title="TestWindow", backend_mode=False, monitor_index=1)


def _patch_win32(mock_hwnd=12345, monitors=None, mon_info=None,
                 win_rect_side_effect=None, is_zoomed=False, is_iconic=False):
    """回傳一個 context manager dict，統一 patch Win32 相關呼叫。"""
    if monitors is None:
        monitors = [("hmon1", None, None)]
    if mon_info is None:
        # Monitor 1: (0, 0, 1920, 1080)
        mon_info = {"Monitor": (0, 0, 1920, 1080), "Device": r"\\.\DISPLAY1"}
    if win_rect_side_effect is None:
        # 視窗中心在 (960, 540)，在 Monitor 1 內
        win_rect_side_effect = [(0, 0, 1920, 1080)]

    return {
        "get_hwnd": patch("capture.screen.ScreenCapturer.get_hwnd", return_value=mock_hwnd),
        "enum_monitors": patch("win32api.EnumDisplayMonitors", return_value=monitors),
        "get_mon_info": patch("win32api.GetMonitorInfo", return_value=mon_info),
        "get_win_rect": patch("win32gui.GetWindowRect", side_effect=win_rect_side_effect),
        "is_zoomed": patch("ctypes.windll.user32.IsZoomed", return_value=int(is_zoomed)),
        "is_iconic": patch("ctypes.windll.user32.IsIconic", return_value=int(is_iconic)),
        "show_win": patch("win32gui.ShowWindow"),
        "set_pos": patch("win32gui.SetWindowPos"),
        "set_fg": patch("ctypes.windll.user32.SetForegroundWindow"),
        "send_msg": patch("win32gui.SendMessage"),
        "is_window": patch("win32gui.IsWindow", return_value=True),
    }


class TestEnsureWindowOnMonitorBehavior(unittest.TestCase):
    """T4-A ~ T4-D"""

    def setUp(self):
        self.capturer = _make_capturer()

    # ── T4-A ──────────────────────────────────
    def test_T4A_already_on_target_maximized_returns_true_no_move(self):
        """
        T4-A: 視窗已在目標顯示器（中心在 Monitor 1）且已最大化。
        → 應立即 return True，不應呼叫 SetWindowPos 或 ShowWindow(SW_RESTORE)。
        """
        patches = _patch_win32(
            win_rect_side_effect=[(0, 0, 1920, 1080)],  # 視窗 = Monitor 1 完整範圍
            is_zoomed=True,
            is_iconic=False,
        )
        with patches["get_hwnd"], patches["enum_monitors"], patches["get_mon_info"], \
             patches["get_win_rect"], patches["is_zoomed"], patches["is_iconic"], \
             patches["show_win"] as mock_show, patches["set_pos"] as mock_set_pos, \
             patches["set_fg"], patches["send_msg"], patches["is_window"]:

            result = self.capturer.ensure_window_on_monitor(monitor_index=1)

            self.assertTrue(result, msg="視窗已在目標且最大化，應回傳 True")
            mock_set_pos.assert_not_called()
            # ShowWindow 不應被呼叫（SW_RESTORE 或 SW_SHOWMAXIMIZED 均不應觸發）
            for c in mock_show.call_args_list:
                flag = c.args[1] if len(c.args) > 1 else c[0][1]
                self.assertNotEqual(flag, win32con.SW_RESTORE,
                                    "不應呼叫 SW_RESTORE（視窗已在目標且最大化）")

    # ── T4-B ──────────────────────────────────
    def test_T4B_on_target_not_maximized_maximizes_without_moving(self):
        """
        T4-B: 視窗在目標顯示器但未最大化（is_zoomed=False, is_iconic=False）。
        → 應呼叫 SW_SHOWMAXIMIZED，但不應呼叫 SetWindowPos。
        """
        patches = _patch_win32(
            # 第一次取 rect（邏輯判斷用），第二次取 rect（驗證用）
            win_rect_side_effect=[(0, 0, 1920, 1080), (0, 0, 1920, 1080)],
            is_zoomed=False,
            is_iconic=False,
        )
        with patches["get_hwnd"], patches["enum_monitors"], patches["get_mon_info"], \
             patches["get_win_rect"], patches["is_zoomed"], patches["is_iconic"], \
             patches["show_win"] as mock_show, patches["set_pos"] as mock_set_pos, \
             patches["set_fg"], patches["send_msg"], patches["is_window"]:

            self.capturer.ensure_window_on_monitor(monitor_index=1)

            mock_set_pos.assert_not_called()
            show_flags = [c.args[1] if len(c.args) > 1 else c[0][1]
                          for c in mock_show.call_args_list]
            self.assertIn(win32con.SW_SHOWMAXIMIZED, show_flags,
                          "應呼叫 SW_SHOWMAXIMIZED")
            self.assertNotIn(win32con.SW_RESTORE, show_flags,
                             "不應呼叫 SW_RESTORE（視窗未最大化，不需要先 Restore）")

    # ── T4-C ──────────────────────────────────
    def test_T4C_iconic_window_restores_before_maximizing(self):
        """
        T4-C: 視窗最小化（is_iconic=True）且不在目標顯示器。
        → 順序應為 SW_RESTORE → SetWindowPos → SW_SHOWMAXIMIZED。
        """
        call_order = []

        def track_show(hwnd, flag):
            call_order.append(("ShowWindow", flag))

        def track_pos(*args, **kwargs):
            call_order.append(("SetWindowPos",))

        patches = _patch_win32(
            # 初始在 Monitor 0 的範圍（中心 x=640 < mon 1 右界 0 => 不在 mon 1）
            # Monitor 1 = (0,0,1920,1080)，所以 x=640, y=360 在 Monitor 1 內。
            # 讓視窗中心不在 Monitor 1，用一個偏移的 rect：
            win_rect_side_effect=[
                (-1920, 0, 0, 1080),   # 初始：視窗在 Monitor 0（左側，中心 x=-960）
                (-1920, 0, 0, 1080),   # restore 後重新取 rect
                (0, 0, 1920, 1080),    # 驗證用
            ],
            is_zoomed=False,
            is_iconic=True,
        )
        with patches["get_hwnd"], patches["enum_monitors"], patches["get_mon_info"], \
             patches["get_win_rect"], patches["is_zoomed"], patches["is_iconic"], \
             patch("win32gui.ShowWindow", side_effect=track_show), \
             patch("win32gui.SetWindowPos", side_effect=track_pos), \
             patches["set_fg"], patches["send_msg"], patches["is_window"]:

            with patch("time.sleep"):  # 跳過 time.sleep 讓測試更快
                self.capturer.ensure_window_on_monitor(monitor_index=1)

            # 驗證 SW_RESTORE 先於 SetWindowPos
            sw_restore_idx = next(
                (i for i, e in enumerate(call_order) if e == ("ShowWindow", win32con.SW_RESTORE)), None)
            set_pos_idx = next(
                (i for i, e in enumerate(call_order) if e == ("SetWindowPos",)), None)
            sw_max_idx = next(
                (i for i, e in enumerate(call_order) if e == ("ShowWindow", win32con.SW_SHOWMAXIMIZED)), None)

            self.assertIsNotNone(sw_restore_idx, "應呼叫 SW_RESTORE")
            self.assertIsNotNone(set_pos_idx, "應呼叫 SetWindowPos")
            self.assertIsNotNone(sw_max_idx, "應呼叫 SW_SHOWMAXIMIZED")
            self.assertLess(sw_restore_idx, set_pos_idx,
                            "SW_RESTORE 應在 SetWindowPos 之前")
            self.assertLess(set_pos_idx, sw_max_idx,
                            "SetWindowPos 應在 SW_SHOWMAXIMIZED 之前")

    # ── T4-D ──────────────────────────────────
    def test_T4D_invalid_monitor_index_returns_false_immediately(self):
        """
        T4-D: monitor_index=99（超出顯示器數量）→ 立即 return False，不呼叫任何 Win32 API。
        """
        patches = _patch_win32(monitors=[("hmon1", None, None)])  # 只有 1 台顯示器
        with patches["get_hwnd"] as mock_hwnd, patches["enum_monitors"], \
             patches["get_mon_info"] as mock_info, patches["get_win_rect"] as mock_rect, \
             patches["is_zoomed"], patches["is_iconic"], patches["show_win"], \
             patches["set_pos"] as mock_pos, patches["set_fg"], \
             patches["send_msg"], patches["is_window"]:

            result = self.capturer.ensure_window_on_monitor(monitor_index=99)

            self.assertFalse(result, msg="無效 monitor_index 應回傳 False")
            mock_pos.assert_not_called()
            mock_info.assert_not_called()
            mock_rect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
