import time
import logging
import os
import cv2
import numpy as np
from enum import Enum, auto
from typing import Optional, Tuple
from capture.screen import ScreenCapturer
from vision.matcher import TemplateMatcher
from actions.mouse import MouseController

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class LauncherPhase(Enum):
    LAUNCHING = auto()               # 階段 1: 發起直連啟動並輪詢視窗
    COMPLETED = auto()                # 階段 2: 遊戲視窗建立與傳送最大化完成
    FAILED = auto()                   # 流程失敗/超時


class SteamGameLauncher:
    """
    從 Windows 原生協定 (steam://rungameid/1765770) 自動發起直連啟動並管理遊戲視窗的 Phase 狀態機類別。
    畫面載入 login/login.png 後，自動將視窗傳送至指定 Monitor (預設 1 號筆電螢幕) 並最大化全螢幕。
    """

    def __init__(
        self,
        capturer: Optional[ScreenCapturer] = None,
        mouse: Optional[MouseController] = None,
        matcher: Optional[TemplateMatcher] = None,
        game_title: str = "Blackfire Crusade",
        backend_mode: bool = False,
        monitor_index: Optional[int] = 1,
        action_cooldown: float = 1.0
    ):
        self.game_title = game_title
        self.backend_mode = backend_mode
        self.monitor_index = monitor_index
        self.capturer = capturer or ScreenCapturer(window_title=game_title, backend_mode=backend_mode, monitor_index=monitor_index)
        self.mouse = mouse or MouseController(window_title=game_title, backend_mode=backend_mode)
        self.matcher = matcher or TemplateMatcher()
        self.action_cooldown = action_cooldown
        self.phase = LauncherPhase.LAUNCHING

    def _safe_match(
        self,
        screen_img: np.ndarray,
        template_name: str,
        threshold: float = 0.65
    ) -> Tuple[Optional[Tuple[int, int]], float]:
        """
        安全呼叫 TemplateMatcher.match()，支援 Mock 單元測試與標準模板比對。
        """
        if screen_img is None or not hasattr(screen_img, "shape"):
            return None, 0.0

        if matcher_func := getattr(self.matcher, "match", None):
            try:
                res = matcher_func(screen_img, template_name, threshold=threshold)
                if isinstance(res, (tuple, list)) and len(res) >= 2:
                    pos = res[0]
                    conf = float(res[1]) if res[1] is not None else 0.0
                    if pos is not None and conf >= threshold:
                        logging.info(f"🎯 [Match Success] 模板 '{template_name}' 匹配成功！座標: {pos}, 相似度: {conf:.4f} (門檻: {threshold})")
                        return pos, conf
                    return None, conf
            except Exception as e:
                logging.debug(f"_safe_match 比對異常: {e}")

        return None, 0.0

    def is_game_open(self) -> bool:
        """
        檢查遊戲視窗是否已經在 Windows 中開啟 (無論是否被遮擋或最小化)。
        """
        try:
            import win32gui
            hwnd = win32gui.FindWindow(None, self.game_title)
            return hwnd != 0 and bool(win32gui.IsWindow(hwnd))
        except Exception as e:
            logging.debug(f"is_game_open 檢查失敗: {e}")
            return False

    def wait_and_handle_login(self, timeout: float = 60.0, poll_interval: float = 0.5) -> bool:
        """
        在「遊戲視窗」中搜尋登入畫面 [login/login.png]。
        畫面渲染成功後觸發傳送至 1 號筆電螢幕並最大化全螢幕，隨後將登入點擊交由主狀態機 LoginFlow 處理。
        """
        logging.info("[SteamGameLauncher] 正在「遊戲視窗」中搜尋登入畫面 [login/login.png]...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            rect = self.capturer.get_window_rect()
            if not rect:
                time.sleep(poll_interval)
                continue

            screen_img = self.capturer.capture(rect)
            if screen_img is None:
                time.sleep(poll_interval)
                continue

            # 專心比對登入主畫面 login/login.png
            login_pos, conf = self._safe_match(screen_img, "login/login.png", threshold=0.65)
            if login_pos:
                logging.info(f"🔑 [SteamGameLauncher] 遊戲畫面載入完成，偵測到登入畫面 [login/login.png] (相似度: {conf:.2f})！開始視窗移動與最大化全螢幕...")
                
                # 確定畫面完全載入渲染後，觸發傳送與最大化全螢幕
                if hasattr(self.capturer, "ensure_window_on_monitor"):
                    self.capturer.ensure_window_on_monitor()

                logging.info("✅ [SteamGameLauncher] 遊戲視窗已定位至 1 號筆電螢幕並最大化，準備交由主狀態機 LoginFlow 執行登入！")
                return True

            time.sleep(poll_interval)

        logging.warning("⚠️ [SteamGameLauncher] 超時未在遊戲視窗內偵測到登入畫面。")
        return False

    def ensure_game_ready(self) -> bool:
        """
        全流程開關與登入檢測入口：
        1. 判斷 is_game_open()
        2. 若未開啟，跑 run_launch_subflow() 啟動遊戲
        3. 在遊戲視窗中等待畫面完全載入 (login.png) 後，自動移動至 1 號筆電螢幕並最大化全螢幕
        """
        logging.info("[SteamGameLauncher] 開始執行 ensure_game_ready 檢查與啟動流程...")

        if not self.is_game_open():
            logging.info("🌐 偵測到遊戲未開啟，發起 Steam 啟動 Subflow...")
            if not self.run_launch_subflow():
                logging.error("❌ Steam 啟動遊戲失敗！")
                return False
        else:
            logging.info("✅ 偵測到遊戲已開啟，跳過 Steam 啟動流程。")

        return self.wait_and_handle_login()

    def transition_to(self, next_phase: LauncherPhase, reason: str = ""):
        logging.info(f"🔄 [SteamGameLauncher] 狀態轉移: {self.phase.name} ➔ {next_phase.name} ({reason})")
        self.phase = next_phase

    def run_launch_subflow(self, timeout: float = 90.0, poll_interval: float = 1.0) -> bool:
        logging.info("==================================================")
        logging.info(" 🚀 [SteamGameLauncher] 開始執行原生協定直連啟動與輪詢重試流程 (Retry 間隔: 30 秒)")
        logging.info("==================================================")

        start_time = time.time()
        retry_count = 0

        while time.time() - start_time < timeout:
            retry_count += 1
            logging.info(f"🚀 [SteamGameLauncher] (第 {retry_count} 次) 呼叫 Windows 原生 steam://rungameid/1765770 發起啟動...")
            try:
                import subprocess
                subprocess.Popen(["cmd", "/c", "start", "steam://rungameid/1765770"], shell=True)
            except Exception as e:
                logging.warning(f"發起 steam:// 協定失敗: {e}")

            # 每輪輪詢 30 秒檢測遊戲視窗 HWND 是否建立
            max_ticks = max(1, int(30.0 / poll_interval)) if poll_interval > 0 else 30
            for _ in range(max_ticks):
                rect = self.capturer.get_window_rect(quiet=True)
                if rect is not None:
                    logging.info(f"🎉 [SteamGameLauncher] 遊戲視窗 HWND 已成功建立: {rect}")
                    self.transition_to(LauncherPhase.COMPLETED, "已偵測到遊戲視窗")
                    logging.info("✅ [SteamGameLauncher] 第一階段 Steam 啟動遊戲 Subflow 成功執行完畢！")
                    return True
                time.sleep(poll_interval)

            logging.warning("⚠️ [SteamGameLauncher] 等待 30 秒遊戲視窗尚未開啟，準備進行 Retry...")

        logging.error(f"❌ [SteamGameLauncher] 超時 {timeout} 秒未成功開啟遊戲。")
        self.transition_to(LauncherPhase.FAILED, "超時")
        return False
