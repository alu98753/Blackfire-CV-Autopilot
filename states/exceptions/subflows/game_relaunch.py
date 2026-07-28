import os
import time
import logging
import subprocess
from states.exceptions.subflows.base import BaseExceptionSubflow
from utils.steam_launcher import SteamGameLauncher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class GameRelaunchSubflow(BaseExceptionSubflow):
    """
    遊戲進程終止與直連啟動重啟自癒子流程 (GameRelaunchSubflow)
    
    當且僅當：
    1. UnexpectedPopupRecoveryHandler 重試次數達到上限 (max_retries >= 5)
    2. ExceptionWatchdog 同一狀態連續 2 次卡死逾時未轉移
    
    執行強行終止 (taskkill) ➔ Steam 協定直連啟動 (ensure_game_ready) ➔ 重置暫存與連鎖計數器 ➔ 轉移至 STATE_LOGIN_FLOW。
    """
    name: str = "game_relaunch_subflow"

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        return True

    def execute(self, machine, reason: str = "") -> bool:
        """
        執行殺進程與重啟流程。
        :param machine: GameStateMachine 實例
        :param reason: 重啟觸發原因
        :return: True 代表重啟自癒閉環已發起並轉移至 STATE_LOGIN_FLOW
        """
        logging.warning(f"🚨 [GameRelaunchSubflow] 啟動嚴重卡死強行終止與重啟自癒閉環 (原因: {reason})...")

        # 1. 精確強行終止卡死之遊戲進程 (PID 優先 ➔ EXE 映像名稱，嚴禁使用萬用字元 WINDOWTITLE 避免誤殺腳本 Terminal)
        try:
            game_title = getattr(machine, "window_title", "Blackfire Crusade")
            current_script_pid = os.getpid()
            logging.info(f"💥 [GameRelaunchSubflow] 開始發起強行終止遊戲進程 (目標標題: '{game_title}', 腳本 PID: {current_script_pid})...")

            import win32gui
            import win32process

            # (A) 優先根據 HWND 取得實體 PID 發起精確 taskkill /f /pid <pid> (包含 PID 護欄)
            hwnd = win32gui.FindWindow(None, game_title)
            if hwnd:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid and pid != current_script_pid:
                    logging.info(f"💥 [GameRelaunchSubflow] 偵測到遊戲進程 PID: {pid} (非腳本 PID {current_script_pid})，執行 taskkill /f /pid {pid}...")
                    subprocess.run(f"taskkill /f /pid {pid}", shell=True, capture_output=True)

            # (B) 精確關閉遊戲 EXE 映像 (絕對不使用 WINDOWTITLE 萬用字元，避免匹配到含有 BlackfireCrusade_tool 路徑之 PowerShell 視窗)
            subprocess.run('taskkill /f /im BlackfireCrusade.exe', shell=True, capture_output=True)

            # (C) 輪詢驗證：等待直到 win32gui.FindWindow 確定傳回 0 (視窗與進程徹底銷毀)
            start_k_time = time.time()
            while time.time() - start_k_time < 5.0:
                h_check = win32gui.FindWindow(None, game_title)
                if not h_check:
                    logging.info("✅ [GameRelaunchSubflow] 遊戲視窗與進程已確定完全終止與銷毀！")
                    break
                time.sleep(0.3)
        except Exception as e:
            logging.error(f"❌ 終止遊戲進程時發生異常: {e}")

        # 2. 暫停 2.0 秒確保 OS 資源與 Steam 狀態同步
        time.sleep(2.0)

        # 3. 呼叫 SteamGameLauncher 重新直連啟動與視窗定位
        logging.info("🚀 [GameRelaunchSubflow] 調用 SteamGameLauncher 發起遊戲直連啟動與視窗定位...")
        launcher = SteamGameLauncher(
            capturer=getattr(machine, "capturer", None),
            mouse=getattr(machine, "mouse", None),
            matcher=getattr(machine, "matcher", None)
        )
        launcher.ensure_game_ready()

        # 4. 清空暫存狀態與連鎖卡死計數器
        machine.stashed_state = None
        machine.stashed_context = {}
        if hasattr(machine, "exception_watchdog"):
            machine.exception_watchdog.consecutive_stuck_count = 0
            machine.exception_watchdog.last_stuck_state = None

        # 5. 轉移至 NAVIGATING 狀態，全域 handle_global_login 會自動進行登入與進城
        logging.info("🔄 [GameRelaunchSubflow] 重啟完成！轉移狀態至 STATE_NAVIGATING 交由 LoginFlow 接管...")
        machine.transition_to(machine.STATE_NAVIGATING)
        return True
