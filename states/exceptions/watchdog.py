import os
import time
import logging
from typing import Dict, Any
from config import get_exception_features_config, get_subflow_feature_mapping
from states.exceptions.subflows import safe_match


class ExceptionWatchdog:
    """
    全域例外監控與 Watchdog 管理器 (ExceptionWatchdog)
    
    職責：
    1. 規則 2 (Global Stuck Watchdog)：
       - 非戰鬥狀態 (LOBBY/NAVIGATING/EXPLORING 等)：狀態無變化逾時 30 秒觸發。
       - 戰鬥中狀態 (BATTLE)：狀態無變化逾時 90 秒 (1.5 分鐘) 觸發。
    2. 規則 1 (State vs Vision Mismatch)：
       - 每 30 秒執行一次低頻率極輕量檢查。
       - 讀取 config/exception_features.json 的 subflow_feature_mapping 對照表。
       - 確定有 Exception 時，中央發起 stash_current_state() 暫存，並指派觸發對應 Subflow。
    """

    def __init__(self, machine):
        self.machine = machine
        self.last_mismatch_check_time = time.time()


    def check(self, screen_img) -> bool:
        """
        全域例外檢測入口。於 GameStateMachine.step() 中由主調度器單行調用。
        
        :param screen_img: 擷取到的遊戲畫面影像
        :return: True 代表已觸發例外並完成 stash_current_state()；False 代表畫面正常
        """
        if self.machine.current_state == self.machine.STATE_POPUP_RECOVERY:
            return False

        # 1. 全域卡住逾時監控 (30s 非戰鬥 / 90s 戰鬥)
        if self._check_stuck_timeout():
            return True

        # 2. 30 秒低頻特徵與遮罩衝突攔截 (Mismatch Guard)
        if self._check_vision_mismatch(screen_img):
            return True

        return False

    def _check_stuck_timeout(self) -> bool:
        now_t = time.time()
        cfg = get_exception_features_config()

        last_change = getattr(self.machine, "last_state_change", now_t)
        if last_change <= 0 or (now_t - last_change > 86400 * 30):
            self.machine.last_state_change = now_t
            return False

        state_duration = now_t - last_change
        stuck_timeout = (
            cfg.get("battle_stuck_timeout_sec", 90.0)
            if self.machine.current_state == self.machine.STATE_BATTLE
            else cfg.get("non_battle_stuck_timeout_sec", 30.0)
        )

        if state_duration >= stuck_timeout:
            logging.warning(
                f"⚠️ [Watchdog] 狀態 [{self.machine.current_state}] 已卡住逾時 {state_duration:.1f}s (門檻 {stuck_timeout}s)，發起暫存與復原！"
            )
            self.machine.stash_current_state(reason=f"global_stuck_timeout_{self.machine.current_state}")
            return True

        return False


    def _check_vision_mismatch(self, screen_img) -> bool:
        now_t = time.time()
        cfg = get_exception_features_config()
        mismatch_interval = cfg.get("mismatch_scan_interval_sec", 30.0)

        if now_t - self.last_mismatch_check_time >= mismatch_interval:
            self.last_mismatch_check_time = now_t

            # A. 讀取 JSON 中的 subflow_feature_mapping 映射對照
            mapping = get_subflow_feature_mapping()
            popup_handler = self.machine.handlers.get(self.machine.STATE_POPUP_RECOVERY)

            for subflow_name, info in mapping.items():
                if isinstance(info, dict) and "trigger_template" in info:
                    tpl = info["trigger_template"]
                    if os.path.exists(os.path.join("templates", tpl)):
                        pos, conf = safe_match(self.machine.matcher, screen_img, tpl, threshold=0.75)
                        if pos:
                            logging.warning(
                                f"⚠️ [MismatchGuard] 於狀態 [{self.machine.current_state}] 依對照表檢測到 [{subflow_name}] 觸發圖案 [{tpl}] (相似度: {conf:.4f})"
                            )
                            # 中央發起 1. 暫存狀態 -> 2. 指派對應 Subflow -> 3. 切換至 Recovery
                            self.machine.stash_current_state(reason=f"mismatch_{subflow_name}_{tpl}")
                            if popup_handler and hasattr(popup_handler, "subflows_map"):
                                target_subflow = popup_handler.subflows_map.get(subflow_name)
                                if target_subflow:
                                    popup_handler.active_subflow = target_subflow
                            return True

            # B. 檢測暗色遮罩 is_dimmed (僅在非戰鬥、非探索過渡狀態下生效，避免戰鬥畫面固有暗色背景與特效誤判)
            if self.machine.current_state not in [self.machine.STATE_BATTLE, self.machine.STATE_DUNGEON_EXPLORING]:

                if popup_handler and hasattr(popup_handler, "analyze_dimming_overlay"):
                    dim_info = popup_handler.analyze_dimming_overlay(screen_img)
                    if dim_info.get("is_dimmed", False):
                        logging.warning(
                            f"⚠️ [MismatchGuard] 於狀態 [{self.machine.current_state}] 檢測到顯著暗色遮罩 (is_dimmed=True)，發起暫存與復原！"
                        )
                        self.machine.stash_current_state(reason="mismatch_dimming_overlay")
                        return True


        return False
