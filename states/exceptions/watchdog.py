import os
import time
import logging
from typing import Dict, Any
from config import GLOBAL_SETTINGS, get_exception_features_config, get_subflow_feature_mapping
from states.exceptions.subflows import safe_match


class ExceptionWatchdog:
    """
    全域例外監控與 Watchdog 管理器 (ExceptionWatchdog)
    
    資源優化與雙重條件觸發原則：
    1. 平時（狀態變動未滿 30s / 戰鬥未滿 90s）：
       僅進行極輕量之時間浮點數相減，完全不上報或執行任何圖像模板匹配比對，將 CPU 佔用率降至最低。
    2. 當且僅當「狀態持續未變動滿 30s / 90s」時：
       觸發圖像特徵掃描，若命中專屬 Subflow 圖案則精確指派；若無專屬圖案則轉由 POPUP_RECOVERY 之優先級 2 通用防卡死兜底點擊。
    """

    def __init__(self, machine):
        self.machine = machine
        self.consecutive_stuck_count = 0
        self.last_stuck_state = None

    def check(self, screen_img) -> bool:
        """
        全域例外檢測入口。於 GameStateMachine.step() 中由主調度器單行調用。
        
        :param screen_img: 擷取到的遊戲畫面影像
        :return: True 代表已觸發例外並完成 stash_current_state()；False 代表畫面正常
        """
        # 1. 意外彈窗處置中豁免 (由 UnexpectedPopupRecoveryHandler 5 次重試控制) 與 手動暫停中豁免
        if self.machine.current_state == self.machine.STATE_POPUP_RECOVERY or getattr(self.machine, "is_paused", False):
            return False

        now_t = time.time()
        cfg = get_exception_features_config()

        last_change = getattr(self.machine, "last_state_change", now_t)
        if last_change <= 0 or (now_t - last_change > 86400 * 30):
            self.machine.last_state_change = now_t
            return False

        state_duration = now_t - last_change

        # 2. 定時領取待機 (COLLECT_ONLY) 專屬智慧動態逾時與視窗崩潰消失護欄
        if self.machine.current_state == self.machine.STATE_COLLECT_ONLY:
            # (A) 視窗崩潰消失檢查 (HWND 不存在)
            if hasattr(self.machine, "capturer") and self.machine.capturer:
                rect = self.machine.capturer.get_window_rect()
                if rect is None:
                    logging.error("❌ [Watchdog] 定時領取待機中 (COLLECT_ONLY) 偵測到遊戲視窗消失崩潰 (HWND 不存在)！發起 GameRelaunchSubflow 重啟...")
                    from states.exceptions.subflows import GameRelaunchSubflow
                    GameRelaunchSubflow().execute(self.machine, reason="collect_only_window_lost")
                    return True

            # (B) 動態 CD 最大逾時時間檢查 (max(diamond_cd, bread_cd) + 60 秒緩衝)。
            # Keep these fallbacks aligned with CollectOnlyHandler / GameStateMachine:
            # daily profiles do not necessarily override the collection cooldowns.
            cfg_dict = getattr(self.machine, "config", {}) or {}
            default_diamond_cd = GLOBAL_SETTINGS.get("default_diamond_cd", 7200.0)
            default_bread_cd = (
                7200.0
                if cfg_dict.get("type") == "collect_only"
                else GLOBAL_SETTINGS.get("default_bread_cd", 1800.0)
            )
            diamond_cd = float(cfg_dict.get("diamond_cd", default_diamond_cd))
            bread_cd = float(cfg_dict.get("bread_cd", default_bread_cd))
            collect_timeout = max(diamond_cd, bread_cd) + 60.0

            if state_duration > collect_timeout:
                logging.error(f"❌ [Watchdog] 定時領取待機狀態 [COLLECT_ONLY] 已卡住逾時 {state_duration:.1f}s (門檻 {collect_timeout}s)！發起 GameRelaunchSubflow 重啟...")
                from states.exceptions.subflows import GameRelaunchSubflow
                GameRelaunchSubflow().execute(self.machine, reason="collect_only_cooldown_timeout_exceeded")
                return True

            return False

        # 門檻判斷：導航、戰鬥、探索、背包整理與長城鎮任務 (導航/抽卡/領懸賞/Boss/獻祭/寶箱/珠寶加工) 給予 90 秒寬鬆門檻；其餘短狀態 30 秒
        long_subflow_states = [
            self.machine.STATE_NAVIGATING,
            self.machine.STATE_BATTLE,
            self.machine.STATE_DUNGEON_EXPLORING,
            self.machine.STATE_LORD_BOSS,
            self.machine.STATE_HERO_DRAW,
            self.machine.STATE_BULLETIN_BOARD,
            self.machine.STATE_BLOOD_ALTAR,
            self.machine.STATE_JEWELRY_WORKSHOP,
            self.machine.STATE_CHEST,
            self.machine.STATE_BAG_CLEANING,
            self.machine.STATE_BACKPACK_FULL_SORTING
        ]
        stuck_timeout = (
            cfg.get("long_subflow_timeout_sec", 90.0)
            if self.machine.current_state in long_subflow_states
            else cfg.get("non_battle_stuck_timeout_sec", 30.0)
        )

        # 1. 資源節省護欄：未滿 30s/90s 時，不進行任何圖像比對，直接放行
        if state_duration < stuck_timeout:
            return False

        # 2. 確定滿 30s/90s 逾時：計算連續卡死次數
        if self.last_stuck_state == self.machine.current_state:
            self.consecutive_stuck_count += 1
        else:
            self.last_stuck_state = self.machine.current_state
            self.consecutive_stuck_count = 1

        # 🚨 硬條件 B：若同一個狀態連續 2 次逾時 (代表第 1 次輕量救援無效) -> 觸發 GameRelaunchSubflow
        if self.consecutive_stuck_count >= 2:
            logging.error(
                f"❌ [Watchdog] 狀態 [{self.machine.current_state}] 連續 {self.consecutive_stuck_count} 次逾時卡死！輕量救援無效，發起 GameRelaunchSubflow 重啟..."
            )
            self.consecutive_stuck_count = 0
            self.last_stuck_state = None
            from states.exceptions.subflows import GameRelaunchSubflow
            GameRelaunchSubflow().execute(self.machine, reason=f"watchdog_consecutive_timeout_{self.machine.current_state}")
            return True

        logging.warning(
            f"⚠️ [Watchdog] (第 1 次逾時) 狀態 [{self.machine.current_state}] 已卡住逾時 {state_duration:.1f}s (門檻 {stuck_timeout}s)，啟動特徵掃描與輕量復原！"
        )

        popup_handler = self.machine.handlers.get(self.machine.STATE_POPUP_RECOVERY)
        mapping = get_subflow_feature_mapping()

        matched_subflow_name = None
        for subflow_name, info in mapping.items():
            if isinstance(info, dict) and "trigger_template" in info:
                tpl = info["trigger_template"]
                if os.path.exists(os.path.join("templates", tpl)):
                    pos, conf = safe_match(self.machine.matcher, screen_img, tpl, threshold=0.75)
                    if pos:
                        logging.warning(
                            f"🎯 [Watchdog] 逾時掃描：於狀態 [{self.machine.current_state}] 命中專屬 Subflow [{subflow_name}] 圖案 [{tpl}] (相似度: {conf:.4f})"
                        )
                        matched_subflow_name = subflow_name
                        break

        # 中央發起暫存與 Subflow 指派
        self.machine.stash_current_state(reason=f"watchdog_timeout_{self.machine.current_state}")
        if popup_handler and hasattr(popup_handler, "subflows_map"):
            if matched_subflow_name:
                popup_handler.active_subflow = popup_handler.subflows_map.get(matched_subflow_name)
            else:
                popup_handler.active_subflow = None  # 將走優先級 2 GenericAntiStuckSubflow

        return True
