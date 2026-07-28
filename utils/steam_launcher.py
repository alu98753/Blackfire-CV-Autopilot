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
from states.debug import DebugVisualizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class LauncherPhase(Enum):
    SEARCH_WINDOWS = auto()           # 階段 1: 尋找並點擊 Windows 搜尋
    LAUNCH_STEAM = auto()             # 階段 2: 點擊 Steam 圖示並等待 Steam 視窗開啟
    START_OR_UNSTUCK_GAME = auto()    # 階段 3: 檢查 Steam 介面並進行解卡或觸發開始遊戲
    WAIT_GAME_WINDOW = auto()         # 階段 4: 等待遊戲視窗開啟並定位
    COMPLETED = auto()                # 階段 5: 第一階段流程完成
    FAILED = auto()                   # 流程失敗/超時


class SteamGameLauncher:
    """
    從 Windows 桌面/工作列自動開啟 Steam 並啟動/解卡遊戲的 Phase 狀態機類別 (Steam Game Launcher Subflow)。
    """

    TPL_SEARCH = "reload_game/search.png"
    TPL_STEAM = "reload_game/steam.png"
    TPL_START_GAME = "reload_game/start_game.png"
    TPL_STOP_GAME = "reload_game/stop_game.png"

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
        self.phase = LauncherPhase.SEARCH_WINDOWS

    def _safe_match(self, screen_img, template_name: str, threshold: float = 0.75) -> Tuple[Optional[Tuple[int, int]], float]:
        """
        安全呼叫 TemplateMatcher.match()，防範模板尺寸大於畫面尺寸之異常。
        """
        if screen_img is None or not hasattr(screen_img, "shape"):
            return None, 0.0

        tpl_path = os.path.join("templates", template_name)
        if os.path.exists(tpl_path):
            tpl_img = cv2.imread(tpl_path)
            if tpl_img is not None and hasattr(tpl_img, "shape"):
                sh, sw = screen_img.shape[:2]
                th, tw = tpl_img.shape[:2]
                if th > sh or tw > sw:
                    return None, 0.0

        if matcher_func := getattr(self.matcher, "match", None):
            try:
                res = matcher_func(screen_img, template_name, threshold=threshold)
                if isinstance(res, (tuple, list)) and len(res) >= 2 and res[0]:
                    pos = res[0]
                    conf = float(res[1]) if res[1] is not None else 0.0
                    return pos, conf
            except Exception as e:
                logging.debug(f"_safe_match 比對異常: {e}")
        return None, 0.0

    def _visualize_and_click(
        self,
        screen_img: np.ndarray,
        template_name: str,
        pos_in_img: Tuple[int, int],
        confidence: float,
        abs_click_pos: Optional[Tuple[int, int]] = None,
        filename: str = "debug_click.png"
    ):
        """
        調用 DebugVisualizer 統一將點擊座標與匹配 Bounding Box 寫入 debug_click.png，並執行點擊。
        """
        bw, bh = 60, 60
        tpl_path = os.path.join("templates", template_name)
        if os.path.exists(tpl_path):
            img_tpl = cv2.imread(tpl_path)
            if img_tpl is not None and len(img_tpl.shape) >= 2:
                bh, bw = img_tpl.shape[:2]

        box_x, box_y = pos_in_img
        matched_bbox = (max(0, box_x - bw // 2), max(0, box_y - bh // 2), bw, bh)

        # 計算特定螢幕在 Windows 虛擬座標系中的絕對點擊位置 (加上 monitor left/top 偏移)
        if abs_click_pos is not None:
            target_x, target_y = abs_click_pos
        else:
            mon = getattr(self.capturer, "last_monitor", None)
            mon_left = mon.get("left", 0) if isinstance(mon, dict) else 0
            mon_top = mon.get("top", 0) if isinstance(mon, dict) else 0
            target_x = mon_left + pos_in_img[0]
            target_y = mon_top + pos_in_img[1]

        try:
            DebugVisualizer.draw_detection(
                screen_img=screen_img,
                click_pos=pos_in_img,
                matched_bbox=matched_bbox,
                labels={"match": f"{template_name} ({confidence:.2f})", "click": f"Click {template_name}"},
                filename=filename
            )
        except Exception as e:
            logging.debug(f"DebugVisualizer 繪圖失敗: {e}")

        self.mouse.click(target_x, target_y)

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

    def wait_and_handle_login(self, timeout: float = 45.0, poll_interval: float = 1.0) -> bool:
        """
        在「遊戲視窗畫面」(非全螢幕) 中輪詢搜尋登入畫面 [login/login.png]，
        一旦偵測到登入畫面，便寫入 debug_click.png 並執行登入點擊。
        """
        logging.info("[SteamGameLauncher] 正在「遊戲視窗」(非全螢幕) 中搜尋登入畫面 [login/login.png]...")
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

            # 1. 檢查 common/door.png 是否已在城鎮 (若已經在城鎮中則免登入)
            door_pos, _ = self._safe_match(screen_img, "common/door.png", threshold=0.75)
            if door_pos:
                logging.info("🏰 [SteamGameLauncher] 遊戲已直接處於城鎮大門畫面 (door.png 可見)，無需登入。")
                return True

            # 2. 檢查登入主畫面 login/login.png
            login_pos, conf = self._safe_match(screen_img, "login/login.png", threshold=0.75)
            if login_pos:
                logging.info(f"🔑 [SteamGameLauncher] 在遊戲視窗內偵測到登入畫面 [login/login.png] (相似度: {conf:.2f})！開始執行登入流程...")

                confirm_pos, conf_confirm = self._safe_match(screen_img, "login/login_confirm.png", threshold=0.75)
                if confirm_pos:
                    abs_x = rect["left"] + confirm_pos[0]
                    abs_y = rect["top"] + confirm_pos[1]
                    logging.info(f"👉 [SteamGameLauncher] 定位「開始冒險」 [login_confirm.png] (相似度: {conf_confirm:.2f})，寫入 debug_click.png 並點擊...")
                    self._visualize_and_click(
                        screen_img, "login/login_confirm.png", confirm_pos, conf_confirm, abs_click_pos=(abs_x, abs_y)
                    )
                else:
                    abs_x = rect["left"] + login_pos[0] - 3
                    abs_y = rect["top"] + login_pos[1] + 253
                    logging.info(f"👉 [SteamGameLauncher] 採用相對 login.png 垂直偏移點擊 ({abs_x}, {abs_y})...")
                    self._visualize_and_click(
                        screen_img, "login/login.png", login_pos, conf, abs_click_pos=(abs_x, abs_y)
                    )
                return True

            time.sleep(poll_interval)

        logging.warning("⚠️ [SteamGameLauncher] 超時未在遊戲視窗內偵測到登入畫面或城鎮。")
        return False

    def ensure_game_ready(self) -> bool:
        """
        全流程開關與登入檢測入口：
        1. 判斷 is_game_open()
        2. 若未開啟，跑 run_launch_subflow() 啟動遊戲
        3. 遊戲開啟後，在「遊戲視窗」(非全螢幕) 中等待登入畫面並執行登入
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

    def run_launch_subflow(self, timeout: float = 60.0, poll_interval: float = 0.5) -> bool:
        logging.info("==================================================")
        logging.info(" 🚀 [SteamGameLauncher] 開始執行 Steam 啟動遊戲 狀態機 Subflow")
        logging.info("==================================================")

        self.phase = LauncherPhase.SEARCH_WINDOWS
        start_time = time.time()
        last_action_time = 0.0

        while time.time() - start_time < timeout:
            if self.phase == LauncherPhase.COMPLETED:
                logging.info("✅ [SteamGameLauncher] 第一階段 Steam 啟動遊戲 Subflow 成功執行完成！")
                return True

            if self.phase == LauncherPhase.FAILED:
                logging.error("❌ [SteamGameLauncher] 狀態機轉移至 FAILED 狀態，終止 Subflow。")
                return False

            now = time.time()

            # 階段 4：等待遊戲視窗開啟 (不需要全圖截圖)
            if self.phase == LauncherPhase.WAIT_GAME_WINDOW:
                rect = self.capturer.get_window_rect()
                if rect is not None:
                    logging.info(f"🎉 [SteamGameLauncher] 遊戲視窗成功開啟與定位: {rect}")
                    self.transition_to(LauncherPhase.COMPLETED, "已偵測到遊戲視窗")
                    continue
                time.sleep(poll_interval)
                continue

            # 擷取全螢幕畫面供 Phase 1~3 使用
            img = self.capturer.capture(full_screen=True)
            if img is None:
                time.sleep(poll_interval)
                continue

            # ----------------------------------------------------
            # 階段 1: SEARCH_WINDOWS
            # ----------------------------------------------------
            if self.phase == LauncherPhase.SEARCH_WINDOWS:
                start_pos, _ = self._safe_match(img, self.TPL_START_GAME)
                stop_pos, _ = self._safe_match(img, self.TPL_STOP_GAME)
                if start_pos or stop_pos:
                    self.transition_to(LauncherPhase.START_OR_UNSTUCK_GAME, "偵測到 Steam 遊戲介面已開啟")
                    continue

                steam_pos, _ = self._safe_match(img, self.TPL_STEAM)
                if steam_pos:
                    self.transition_to(LauncherPhase.LAUNCH_STEAM, "偵測到 Steam 圖示已呈現")
                    continue

                pos, conf = self._safe_match(img, self.TPL_SEARCH)
                if not pos:
                    # 雙螢幕備用：若指定顯示器未找到 search.png，自動掃描主顯示器工作列
                    try:
                        primary_mon = next((m for m in self.capturer.sct.monitors[1:] if m.get("is_primary")), None)
                        if primary_mon:
                            pri_shot = self.capturer.sct.grab(primary_mon)
                            pri_img = cv2.cvtColor(np.array(pri_shot), cv2.COLOR_BGRA2BGR)
                            pri_pos, pri_conf = self._safe_match(pri_img, self.TPL_SEARCH)
                            if pri_pos and (now - last_action_time >= self.action_cooldown):
                                abs_x = primary_mon["left"] + pri_pos[0]
                                abs_y = primary_mon["top"] + pri_pos[1]
                                logging.info(f"🔍 [SteamGameLauncher] 在主顯示器找到搜尋圖示 (座標: ({abs_x}, {abs_y}), 置信度: {pri_conf:.2f})，寫入 debug_click.png 並點擊...")
                                self._visualize_and_click(pri_img, self.TPL_SEARCH, pri_pos, pri_conf, abs_click_pos=(abs_x, abs_y))
                                try:
                                    import pyautogui
                                    pyautogui.write("steam", interval=0.05)
                                except Exception:
                                    pass
                                last_action_time = now
                                self.transition_to(LauncherPhase.LAUNCH_STEAM, "已點擊主顯示器 Windows 搜尋並輸入 steam")
                                continue
                    except Exception as e_pri:
                        logging.debug(f"主顯示器搜尋備用掃描異常: {e_pri}")

                if pos and (now - last_action_time >= self.action_cooldown):
                    logging.info(f"🔍 [SteamGameLauncher] 找到搜尋圖示 (座標: {pos}, 置信度: {conf:.2f})，寫入 debug_click.png 並點擊...")
                    self._visualize_and_click(img, self.TPL_SEARCH, pos, conf)
                    # 輸入 "steam" 關鍵字搜尋
                    try:
                        import pyautogui
                        pyautogui.write("steam", interval=0.05)
                    except Exception:
                        pass
                    last_action_time = now
                    self.transition_to(LauncherPhase.LAUNCH_STEAM, "已點擊 Windows 搜尋並輸入 steam")

            # ----------------------------------------------------
            # 階段 2: LAUNCH_STEAM (Click until Steam opened)
            # ----------------------------------------------------
            elif self.phase == LauncherPhase.LAUNCH_STEAM:
                start_pos, _ = self._safe_match(img, self.TPL_START_GAME)
                stop_pos, _ = self._safe_match(img, self.TPL_STOP_GAME)
                if start_pos or stop_pos:
                    self.transition_to(LauncherPhase.START_OR_UNSTUCK_GAME, "Steam 遊戲介面按鈕已呈現")
                    continue

                steam_pos, conf = self._safe_match(img, self.TPL_STEAM)
                if steam_pos and (now - last_action_time >= self.action_cooldown):
                    logging.info(f"🚀 [SteamGameLauncher] 找到 Steam 圖示 (座標: {steam_pos}, 置信度: {conf:.2f})，寫入 debug_click.png 並點擊...")
                    self._visualize_and_click(img, self.TPL_STEAM, steam_pos, conf)
                    last_action_time = now

            # ----------------------------------------------------
            # 階段 3: START_OR_UNSTUCK_GAME (解卡與啟動)
            # ----------------------------------------------------
            elif self.phase == LauncherPhase.START_OR_UNSTUCK_GAME:
                stop_pos, stop_conf = self._safe_match(img, self.TPL_STOP_GAME)
                start_pos, start_conf = self._safe_match(img, self.TPL_START_GAME)

                if stop_pos and (now - last_action_time >= self.action_cooldown):
                    logging.info(f"🛑 [SteamGameLauncher] 偵測到遊戲卡死 (stop_game.png, 座標: {stop_pos})，寫入 debug_click.png 並點擊解卡...")
                    self._visualize_and_click(img, self.TPL_STOP_GAME, stop_pos, stop_conf)
                    last_action_time = now
                    continue

                if start_pos and not stop_pos and (now - last_action_time >= self.action_cooldown):
                    logging.info(f"▶️ [SteamGameLauncher] 點擊「開始遊戲」 (start_game.png, 座標: {start_pos})，寫入 debug_click.png 並點擊...")
                    self._visualize_and_click(img, self.TPL_START_GAME, start_pos, start_conf)
                    last_action_time = now
                    self.transition_to(LauncherPhase.WAIT_GAME_WINDOW, "已點擊開始遊戲")

            time.sleep(poll_interval)

        logging.warning(f"⚠️ [SteamGameLauncher] 超時未在 {timeout}s 內完成 Steam 啟動 Subflow。")
        self.transition_to(LauncherPhase.FAILED, "逾時")
        return False
