import os
import time
import logging
import subprocess
from states.exceptions.subflows.base import BaseExceptionSubflow
from utils.steam_launcher import SteamGameLauncher
from utils.sandbox_manager import SandboxManager
from config import WINDOW_TITLE

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

        current_script_pid = os.getpid()
        logging.info(f'💥 [GameRelaunchSubflow] 發起目標實例終止 (標題: {game_title}, 沙盒: {is_sandbox}, 腳本 PID: {current_script_pid})...')

        try:
            import win32gui
            import win32process

            target_hwnd = None
            if hasattr(machine, 'capturer') and machine.capturer:
                target_hwnd = machine.capturer.get_hwnd()
            if not target_hwnd or not win32gui.IsWindow(target_hwnd):
                target_hwnd = win32gui.FindWindow(None, game_title)

            if target_hwnd and win32gui.IsWindow(target_hwnd):
                _, pid = win32process.GetWindowThreadProcessId(target_hwnd)
                if pid and pid != current_script_pid:
                    logging.info(f'💥 [GameRelaunchSubflow] 偵測到目標進程 PID: {pid}，執行精確 taskkill /f /pid {pid}...')
                    subprocess.run(f'taskkill /f /pid {pid}', shell=True, capture_output=True)

            start_k_time = time.time()
            while time.time() - start_k_time < 5.0:
                h_check = win32gui.FindWindow(None, game_title)
                if not h_check:
                    logging.info('✅ [GameRelaunchSubflow] 目標遊戲視窗與進程已確定完全終止！')
                    break
                time.sleep(0.3)
        except Exception as e:
            logging.error(f'❌ 終止遊戲進程時發生異常: {e}')

        time.sleep(2.0)

        logging.info('🚀 [GameRelaunchSubflow] 調用 SteamGameLauncher 發起專屬遊戲直連啟動與視窗定位...')
        launcher = SteamGameLauncher(
            capturer=getattr(machine, 'capturer', None),
            mouse=getattr(machine, 'mouse', None),
            matcher=getattr(machine, 'matcher', None),
            game_title=game_title,
            backend_mode=getattr(machine, 'backend_mode', False),
        )
        launcher.ensure_game_ready()

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
        return True
