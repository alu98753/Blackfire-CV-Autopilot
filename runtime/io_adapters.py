"""Composition-root selection for runtime capture and input adapters."""

from capture.screen import ScreenCapturer
from actions.mouse import MouseController


class BackendScreenCapturer(ScreenCapturer):
    def __init__(self, *args, **kwargs):
        kwargs.pop("backend_mode", None)
        super().__init__(*args, backend_mode=True, **kwargs)


class ForegroundScreenCapturer(ScreenCapturer):
    def __init__(self, *args, **kwargs):
        kwargs.pop("backend_mode", None)
        super().__init__(*args, backend_mode=False, **kwargs)


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
