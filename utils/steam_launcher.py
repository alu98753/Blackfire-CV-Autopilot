import time
import logging
from enum import Enum, auto
from typing import Optional, Tuple
from capture.screen import ScreenCapturer
from vision.matcher import TemplateMatcher
from actions.mouse import MouseController

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
        action_cooldown: float = 1.0
    ):
        self.capturer = capturer or ScreenCapturer(window_title=game_title)
        self.mouse = mouse or MouseController(window_title=game_title)
        self.matcher = matcher or TemplateMatcher()
        self.game_title = game_title
        self.action_cooldown = action_cooldown
        self.phase = LauncherPhase.SEARCH_WINDOWS

    def _safe_match(self, screen_img, template_name: str, threshold: float = 0.75) -> Tuple[Optional[Tuple[int, int]], float]:
        """
        安全呼叫 TemplateMatcher.match()，傳回 (中心座標 (x,y), 相似度)。
        """
        if matcher_func := getattr(self.matcher, "match", None):
            res = matcher_func(screen_img, template_name, threshold=threshold)
            if isinstance(res, (tuple, list)) and len(res) >= 2:
                pos = res[0]
                conf = float(res[1]) if res[1] is not None else 0.0
                return pos, conf
        return None, 0.0

    def transition_to(self, next_phase: LauncherPhase, reason: str = ""):
        """
        顯式狀態轉移方法。
        """
        logging.info(f"🔄 [SteamGameLauncher] 狀態轉移: {self.phase.name} ➔ {next_phase.name} ({reason})")
        self.phase = next_phase

    def run_launch_subflow(self, timeout: float = 60.0, poll_interval: float = 0.5) -> bool:
        """
        以 Phase 狀態機驅動的控制迴圈 (State Machine While Loop)。
        每個 Phase 均有嚴格的轉移條件與防呆，一個階段未完絕不進入下一個階段。
        """
        logging.info("==================================================")
        logging.info(" 🚀 [SteamGameLauncher] 開始執行 Steam 啟動遊戲 狀態機 Subflow")
        logging.info("==================================================")

        self.phase = LauncherPhase.SEARCH_WINDOWS
        start_time = time.time()
        last_action_time = 0.0

        while time.time() - start_time < timeout:
            if self.phase == LauncherPhase.COMPLETED:
                logging.info("✅ [SteamGameLauncher] 第一階段 Steam 啟動遊戲 Subflow 成功執行完成！")
                # TODO: 步驟 5: 遊戲載入與關閉更新/登入彈窗處置
                # TODO: 步驟 6: 進入城鎮主畫面之狀態同步
                return True

            if self.phase == LauncherPhase.FAILED:
                logging.error("❌ [SteamGameLauncher] 狀態機轉移至 FAILED 狀態，終止 Subflow。")
                return False

            now = time.time()

            # 階段 4：等待遊戲視窗開啟 (不需要全圖截圖，直接檢查視窗 controls)
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
                # 判斷是否已經看到 Steam 或開始/停止按鈕 (跳轉備援)
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
                if pos and (now - last_action_time >= self.action_cooldown):
                    logging.info(f"🔍 [SteamGameLauncher] 找到搜尋圖示 (座標: {pos}, 置信度: {conf:.2f})，執行點擊...")
                    self.mouse.click(pos[0], pos[1])
                    last_action_time = now
                    self.transition_to(LauncherPhase.LAUNCH_STEAM, "已點擊 Windows 搜尋")

            # ----------------------------------------------------
            # 階段 2: LAUNCH_STEAM (Click until Steam opened)
            # ----------------------------------------------------
            elif self.phase == LauncherPhase.LAUNCH_STEAM:
                # 轉移條件：若偵測到 start_game.png 或 stop_game.png，代表 Steam 已開啟
                start_pos, _ = self._safe_match(img, self.TPL_START_GAME)
                stop_pos, _ = self._safe_match(img, self.TPL_STOP_GAME)
                if start_pos or stop_pos:
                    self.transition_to(LauncherPhase.START_OR_UNSTUCK_GAME, "Steam 遊戲介面按鈕已呈現")
                    continue

                # 尋找並點擊 Steam 圖示 (click until)
                steam_pos, conf = self._safe_match(img, self.TPL_STEAM)
                if steam_pos and (now - last_action_time >= self.action_cooldown):
                    logging.info(f"🚀 [SteamGameLauncher] 點擊 Steam 圖示 (座標: {steam_pos}, 置信度: {conf:.2f})...")
                    self.mouse.click(steam_pos[0], steam_pos[1])
                    last_action_time = now

            # ----------------------------------------------------
            # 階段 3: START_OR_UNSTUCK_GAME (解卡與啟動)
            # ----------------------------------------------------
            elif self.phase == LauncherPhase.START_OR_UNSTUCK_GAME:
                stop_pos, stop_conf = self._safe_match(img, self.TPL_STOP_GAME)
                start_pos, start_conf = self._safe_match(img, self.TPL_START_GAME)

                # 情況 A：若遊戲卡死/執行中 (顯示 stop_game.png)，優先點擊解卡
                if stop_pos and (now - last_action_time >= self.action_cooldown):
                    logging.info(f"🛑 [SteamGameLauncher] 偵測到遊戲卡死 (stop_game.png, 座標: {stop_pos}, 信心度: {stop_conf:.2f})，點擊解卡停止...")
                    self.mouse.click(stop_pos[0], stop_pos[1])
                    last_action_time = now
                    # 保持在本 phase，直到 stop_game 消失且 start_game 出現
                    continue

                # 情況 B：當且僅當 start_game.png 出現，且 stop_game.png 不存在時
                if start_pos and not stop_pos and (now - last_action_time >= self.action_cooldown):
                    logging.info(f"▶️ [SteamGameLauncher] 點擊「開始遊戲」按鈕 (start_game.png, 座標: {start_pos}, 信心度: {start_conf:.2f})...")
                    self.mouse.click(start_pos[0], start_pos[1])
                    last_action_time = now
                    self.transition_to(LauncherPhase.WAIT_GAME_WINDOW, "已點擊開始遊戲")

            time.sleep(poll_interval)

        logging.warning(f"⚠️ [SteamGameLauncher] 超時未在 {timeout}s 內完成 Steam 啟動 Subflow。")
        self.transition_to(LauncherPhase.FAILED, "逾時")
        return False
