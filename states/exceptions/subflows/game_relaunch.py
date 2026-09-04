import os
import time
import logging
from states.exceptions.subflows.base import BaseExceptionSubflow
from runtime.incident_journal import record_recovery
from utils.steam_launcher import SteamGameLauncher
from utils.sandbox_manager import SandboxManager
from config import WINDOW_TITLE

from utils.game_process import terminate_game_process

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class GameRelaunchSubflow(BaseExceptionSubflow):
    name: str = 'game_relaunch_subflow'

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        return True

    def execute(self, machine, reason: str = '') -> bool:
        logging.warning(f'🚨 [GameRelaunchSubflow] 啟動嚴重卡死強行終止與重啟自癒閉環 (原因: {reason})...')

        game_title = getattr(machine, 'window_title', None)
        if not game_title and hasattr(machine, 'capturer') and machine.capturer:
            game_title = getattr(machine.capturer, 'window_title', WINDOW_TITLE)
        game_title = game_title or WINDOW_TITLE

        is_sandbox = getattr(machine, 'is_sandbox', None)
        if is_sandbox is None:
            is_sandbox = SandboxManager.is_sandbox_title(game_title)

        incident_details = {
            "trigger_reason_code": reason,
            "game_title": game_title,
            "is_sandbox": is_sandbox,
        }
        record_recovery(machine, "game_relaunch_started", incident_details)

        target_hwnd = None
        if hasattr(machine, 'capturer') and machine.capturer:
            target_hwnd = machine.capturer.get_hwnd()

        terminate_game_process(game_title=game_title, hwnd=target_hwnd)
        time.sleep(2.0)

        logging.info('🚀 [GameRelaunchSubflow] 調用 SteamGameLauncher 發起專屬遊戲直連啟動與視窗定位...')
        launcher = SteamGameLauncher(
            capturer=getattr(machine, 'capturer', None),
            mouse=getattr(machine, 'mouse', None),
            matcher=getattr(machine, 'matcher', None),
            game_title=game_title,
            backend_mode=getattr(machine, 'backend_mode', False),
        )
        if not launcher.ensure_game_ready():
            logging.error('[GameRelaunchSubflow] Game launch failed; preserving failure state for external supervisor recovery.')
            error = RuntimeError("Game relaunch failed; terminating bot for supervisor recovery.")
            record_recovery(
                machine,
                "game_relaunch_failed",
                incident_details | {"exception_type": type(error).__name__, "exception_message": str(error)},
            )
            raise error

        machine.stashed_state = None
        machine.stashed_context = {}
        machine.bread_window_opened = False
        machine.diamond_window_opened = False
        machine.task_complete_phase = 'INIT_BANNER_CHECK'
        if hasattr(machine, 'exception_watchdog'):
            machine.exception_watchdog.consecutive_stuck_count = 0
            machine.exception_watchdog.last_stuck_state = None

        logging.info('🔄 [GameRelaunchSubflow] 重啟完成！轉移狀態至 STATE_UNKNOWN 交由全域掃描與 LoginFlow 接管...')
        machine.transition_to(machine.STATE_UNKNOWN)
        record_recovery(machine, "game_relaunch_succeeded", incident_details)
        return True
