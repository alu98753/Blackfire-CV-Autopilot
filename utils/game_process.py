"""Utility functions for inspecting and managing game process lifecycle."""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import time

from config import WINDOW_TITLE


def is_window_hung(hwnd: int | None) -> bool:
    """Check if the given window handle is hung/unresponsive using Win32 API."""
    if not hwnd:
        return False
    try:
        return bool(ctypes.windll.user32.IsHungAppWindow(hwnd))
    except (AttributeError, OSError) as exc:
        logging.debug("IsHungAppWindow call failed: %s", exc)
        return False


def get_window_pid(hwnd: int | None) -> int | None:
    """Retrieve the process ID associated with a window handle."""
    if not hwnd:
        return None
    try:
        import win32gui
        import win32process

        if win32gui.IsWindow(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return pid if isinstance(pid, int) and pid > 0 else None
    except Exception as exc:
        logging.debug("GetWindowThreadProcessId failed: %s", exc)
    return None


def find_game_window(game_title: str = WINDOW_TITLE) -> int | None:
    """Find game window handle by title, returning None if not found."""
    try:
        import win32gui

        hwnd = win32gui.FindWindow(None, game_title)
        return hwnd if hwnd and win32gui.IsWindow(hwnd) else None
    except Exception as exc:
        logging.debug("FindWindow failed for '%s': %s", game_title, exc)
        return None


def terminate_game_process(
    game_title: str = WINDOW_TITLE,
    hwnd: int | None = None,
    script_pid: int | None = None,
    timeout: float = 5.0,
) -> bool:
    """Safely terminate game process by PID, preventing accidental self-termination."""
    current_script_pid = os.getpid() if script_pid is None else script_pid
    target_hwnd = hwnd if (hwnd and get_window_pid(hwnd) is not None) else find_game_window(game_title)

    if not target_hwnd:
        logging.info("[GameProcess] No game window found for '%s'; already stopped.", game_title)
        return True

    target_pid = get_window_pid(target_hwnd)
    if target_pid is not None:
        if target_pid == current_script_pid:
            logging.error(
                "[GameProcess] Target PID %d matches current script PID %d! Refusing to terminate self.",
                target_pid,
                current_script_pid,
            )
            return False

        logging.info("[GameProcess] Terminating target process PID %d (taskkill /f /pid %d)...", target_pid, target_pid)
        try:
            subprocess.run(f"taskkill /f /pid {target_pid}", shell=True, capture_output=True)
        except Exception as exc:
            logging.error("[GameProcess] Error executing taskkill: %s", exc)

    start_time = time.time()
    while time.time() - start_time < timeout:
        if not find_game_window(game_title):
            logging.info("[GameProcess] Game window '%s' cleanly terminated.", game_title)
            return True
        time.sleep(0.3)

    still_open = find_game_window(game_title) is not None
    if still_open:
        logging.warning("[GameProcess] Game window '%s' still present after %.1fs timeout.", game_title, timeout)
    return not still_open
