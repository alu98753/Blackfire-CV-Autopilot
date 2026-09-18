"""Composition-root selection for runtime capture and input adapters."""

from capture.screen import ScreenCapturer
from actions.mouse import MouseController
import logging
import numpy as np
import cv2


class BackendScreenCapturer(ScreenCapturer):
    def __init__(self, *args, **kwargs):
        kwargs.pop("backend_mode", None)
        super().__init__(*args, backend_mode=True, **kwargs)

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
        kwargs.pop("backend_mode", None)
        super().__init__(*args, backend_mode=False, **kwargs)

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
        kwargs.pop("backend_mode", None)
        super().__init__(*args, backend_mode=True, **kwargs)


class ForegroundMouseController(MouseController):
    def __init__(self, *args, **kwargs):
        kwargs.pop("backend_mode", None)
        super().__init__(*args, backend_mode=False, **kwargs)


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
