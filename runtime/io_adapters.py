"""Composition-root selection for runtime capture and input adapters."""

from capture.screen import ScreenCapturer
from actions.mouse import MouseController, SAFE_AREA_CLIENT_POS
import logging
import numpy as np
import cv2
import random
import time
import pyautogui
import win32gui
import win32api
import win32con


class BackendScreenCapturer(ScreenCapturer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def capture(self, rect=None, full_screen=False):
        if self._resume_event is not None:
            self._resume_event.wait()
        if full_screen:
            return None
        hwnd = self.get_hwnd()
        if not isinstance(hwnd, int) or hwnd <= 0:
            return None
        return self._capture_backend(hwnd)


class ForegroundScreenCapturer(ScreenCapturer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def capture(self, rect=None, full_screen=False):
        if self._resume_event is not None:
            self._resume_event.wait()
        if full_screen:
            rect = None
        if rect is None and not full_screen:
            rect = self.get_window_rect()
        if self.sct is None:
            return None
        try:
            monitor = self.sct.monitors[1] if rect is None or full_screen else {
                "left": rect["left"], "top": rect["top"],
                "width": rect["width"], "height": rect["height"]}
            self.last_monitor = monitor
            return cv2.cvtColor(np.array(self.sct.grab(monitor)), cv2.COLOR_BGRA2BGR)
        except Exception as exc:
            logging.warning("MSS capture failed; trying PIL fallback: %s", exc)
            try:
                from PIL import ImageGrab
                image = ImageGrab.grab() if rect is None else ImageGrab.grab(
                    bbox=(rect["left"], rect["top"], rect["left"] + rect["width"],
                          rect["top"] + rect["height"]))
                return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            except Exception:
                return None


class BackendMouseController(MouseController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def click(self, x, y, offset_range=(-3, 3), move_duration=(0.03, 0.07)):
        self._wait_if_paused()
        if self.check_user_intervention(): return False
        hwnd = self.get_hwnd()
        if not hwnd: return False
        try:
            cx, cy = self._screen_to_client(hwnd, x, y)
            cx += random.randint(*offset_range); cy += random.randint(*offset_range)
            self._draw_debug_click(hwnd, cx, cy)
            lp = win32api.MAKELONG(int(cx), int(cy))
            win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lp); time.sleep(.01)
            win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp); time.sleep(.04)
            win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp); time.sleep(.04)
            return self._finalize_action(move_safe=True)
        except Exception as exc:
            logging.error("Backend click failed: %s", exc); return False

    def scroll(self, clicks, x=None, y=None):
        self._wait_if_paused()
        if self.check_user_intervention(): return False
        hwnd = self.get_hwnd()
        if not hwnd: return False
        try:
            rect = win32gui.GetClientRect(hwnd)
            cx, cy = ((self._screen_to_client(hwnd, x, y) if x is not None and y is not None
                       else (rect[2] // 2, rect[3] // 2)))
            win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, win32api.MAKELONG(int(cx), int(cy)))
            time.sleep(.05)
            pt = win32gui.ClientToScreen(hwnd, (int(cx), int(cy)))
            win32gui.PostMessage(hwnd, win32con.WM_MOUSEWHEEL, win32api.MAKELONG(0, clicks * 120),
                                 win32api.MAKELONG(pt[0], pt[1]))
            return self._finalize_action(cooldown=.3, move_safe=False)
        except Exception as exc:
            logging.error("Backend scroll failed: %s", exc); return False

    def drag(self, start_x, start_y, end_x, end_y, duration=.5, inertia=True):
        self._wait_if_paused()
        if self.check_user_intervention(): return False
        hwnd = self.get_hwnd()
        if not hwnd: return False
        try:
            sx, sy = self._screen_to_client(hwnd, start_x, start_y)
            ex, ey = self._screen_to_client(hwnd, end_x, end_y)
            win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, 0, win32api.MAKELONG(int(sx), int(sy)))
            time.sleep(.03); win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, win32api.MAKELONG(int(sx), int(sy)))
            time.sleep(.05)
            steps = max(5, int(duration / .02)); step_sleep = duration / steps
            for i in range(1, steps + 1):
                px = int(sx + (ex - sx) * i / steps); py = int(sy + (ey - sy) * i / steps)
                win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, win32api.MAKELONG(px, py)); time.sleep(step_sleep)
            time.sleep(.15 if not inertia else .02)
            end_lp = win32api.MAKELONG(int(ex), int(ey))
            win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, end_lp); time.sleep(.02)
            win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, end_lp)
            return self._finalize_action(cooldown=.3, move_safe=True)
        except Exception as exc:
            logging.error("Backend drag failed: %s", exc); return False

    def move_to_safe_area(self):
        hwnd = self.get_hwnd()
        if hwnd:
            win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0,
                                 win32api.MAKELONG(SAFE_AREA_CLIENT_POS[0], SAFE_AREA_CLIENT_POS[1]))


class ForegroundMouseController(MouseController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def click(self, x, y, offset_range=(-3, 3), move_duration=(.03, .07)):
        self._wait_if_paused()
        if self.check_user_intervention(): return False
        try:
            dx, dy = random.randint(*offset_range), random.randint(*offset_range)
            hwnd = self.get_hwnd()
            if hwnd:
                cx, cy = self._screen_to_client(hwnd, x, y); target = win32gui.ClientToScreen(hwnd, (int(cx + dx), int(cy + dy)))
            else: target = (int(x) + dx, int(y) + dy)
            if self.human_like:
                pyautogui.moveTo(*target, duration=random.uniform(*move_duration), tween=pyautogui.easeOutQuad)
                time.sleep(random.uniform(.01, .02))
            else: pyautogui.moveTo(*target)
            pyautogui.mouseDown(); time.sleep(.04); pyautogui.mouseUp(); time.sleep(.04)
            return self._finalize_action(target_pos=target, move_safe=True)
        except pyautogui.FailSafeException: raise
        except Exception as exc: logging.error("Foreground click failed: %s", exc); return False

    def scroll(self, clicks, x=None, y=None):
        self._wait_if_paused()
        if self.check_user_intervention(): return False
        try:
            pos = None
            if x is not None and y is not None: pyautogui.moveTo(x, y); pos = (x, y)
            pyautogui.scroll(clicks); return self._finalize_action(target_pos=pos, cooldown=.3, move_safe=False)
        except Exception as exc: logging.error("Foreground scroll failed: %s", exc); return False

    def drag(self, start_x, start_y, end_x, end_y, duration=.5, inertia=True):
        self._wait_if_paused()
        if self.check_user_intervention(): return False
        try:
            hwnd = self.get_hwnd()
            if hwnd:
                sx, sy = win32gui.ClientToScreen(hwnd, self._screen_to_client(hwnd, start_x, start_y)); ex, ey = win32gui.ClientToScreen(hwnd, self._screen_to_client(hwnd, end_x, end_y))
            else: sx, sy, ex, ey = int(start_x), int(start_y), int(end_x), int(end_y)
            pyautogui.moveTo(sx, sy)
            if inertia: pyautogui.dragTo(ex, ey, duration=duration, button='left')
            else: pyautogui.mouseDown(button='left'); pyautogui.moveTo(ex, ey, duration=duration); time.sleep(.1); pyautogui.mouseUp(button='left')
            return self._finalize_action(target_pos=(end_x, end_y), cooldown=.3, move_safe=True)
        except Exception as exc: logging.error("Foreground drag failed: %s", exc); return False

    def move_to_safe_area(self):
        hwnd = self.get_hwnd()
        if hwnd:
            try: pyautogui.moveTo(*win32gui.ClientToScreen(hwnd, SAFE_AREA_CLIENT_POS))
            except Exception: pass


def compose_io(*, foreground, window_title, hwnd=None, monitor_index=1,
               human_like=False, resume_event=None):
    capturer_type = ForegroundScreenCapturer if foreground else BackendScreenCapturer
    mouse_type = ForegroundMouseController if foreground else BackendMouseController
    capturer = capturer_type(window_title=window_title, hwnd=hwnd,
                             monitor_index=monitor_index)
    mouse = mouse_type(human_like=human_like, window_title=window_title,
                       capturer=capturer, hwnd=hwnd, resume_event=resume_event)
    return capturer, mouse


def compose_capture(*, foreground, window_title, hwnd=None, monitor_index=1):
    capturer_type = ForegroundScreenCapturer if foreground else BackendScreenCapturer
    return capturer_type(window_title=window_title, hwnd=hwnd,
                         monitor_index=monitor_index)
