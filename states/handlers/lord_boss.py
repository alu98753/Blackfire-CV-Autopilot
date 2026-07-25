import os
import time
import logging
from states.handlers.base import BaseStateHandler
from utils.time_parser import format_seconds_to_readable
from utils.cooldown_detector import detect_cooldown_sign_and_time

class LordBossHandler(BaseStateHandler):
    """
    首領領主討伐 (Lord Boss Subflow) 狀態處理器。
    負責大廳領主頁籤比對、點擊前卡片 OCR 冷卻防護、選擇可挑戰 Boss (育母蜘蛛/古代惡靈) 與發起戰鬥。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"
        self.current_target_boss = None

    def reset_state(self):
        """狀態重置與子流程生命週期初始化"""
        self.step_phase = "INIT"
        self.current_target_boss = None

    def _check_card_cooldown_ocr(self, screen_img, pos_b, max_allowed_seconds=7200.0):
        """
        [ Clean Code 重用 utils.cooldown_detector ]
        在點擊卡片前，截取卡片及其周邊區域圖像並呼叫 detect_cooldown_sign_and_time。
        若優先比對到冷卻木牌且解出合法倒數時間，回傳 (parsed_seconds, raw_text)；否則回傳 (None, None)。
        """
        try:
            h, w = screen_img.shape[:2]
            cx, cy = pos_b
            x1 = max(0, cx - 160)
            x2 = min(w, cx + 160)
            y1 = max(0, cy - 100)
            y2 = min(h, cy + 300)

            crop_img = screen_img[y1:y2, x1:x2]
            
            has_cd, rem_secs, raw_text = detect_cooldown_sign_and_time(
                crop_img, 
                self.machine.get_ocr_reader, 
                max_allowed_seconds=max_allowed_seconds, 
                threshold=0.55
            )
            if has_cd:
                return rem_secs, raw_text
        except Exception as e:
            logging.warning(f"⚠️ [首領討伐] 點擊前卡片 OCR 辨識過程異常: {e}")
        return None, None

    def handle(self, screen_img, rect):
        dm = getattr(self.machine, "daily_manager", None)
        avail_bosses = dm.get_available_lord_bosses() if dm else []

        # 若當前沒有可討伐的 Boss，結束首領討伐子流程，標記完成並彈出下一個城鎮任務
        if not avail_bosses:
            logging.info("🎉 [首領討伐] 今日所有 Boss 已滿 5 次或均在冷卻中！結束討伐，彈出下一城鎮任務...")
            if dm and hasattr(dm, "record_subflow_completed"):
                dm.record_subflow_completed("lord_boss")
            self.machine.pop_and_next_town_subflow()
            return True

        # 1. 檢查並使用相對優勢 API 比對領主頁籤是否已開啟
        entry_after = self.machine.config.get("entry_after_btn", "load/Lord_entry_after.png")
        entry_before = self.machine.config.get("entry_btn", "load/Lord_entry.png")
        
        is_opened, _, _, _ = self.match_mutually_exclusive_tabs(screen_img, entry_after, entry_before, margin=0.02, threshold=0.70)

        # 2. 若頁籤尚未開啟，進行大廳入口與頁籤點擊
        if not is_opened:
            # 先檢查是否在城鎮，需要點擊門進入大廳
            pos_door, conf_door = self.matcher.match(screen_img, "common/door.png", threshold=0.85)
            if pos_door:
                logging.info(f"🚪 [首領討伐] 在城鎮畫面，點擊大廳門入口 [{conf_door:.4f}] 進入大廳。")
                self.mouse.click(rect["left"] + pos_door[0], rect["top"] + pos_door[1])
                time.sleep(0.3)
                return True

            # 點擊領主大廳頁籤入口
            if os.path.exists(os.path.join("templates", entry_before)):
                pos_entry, conf_entry = self.matcher.match(screen_img, entry_before, threshold=0.75)
                if pos_entry:
                    logging.info(f"👑 [首領討伐] 點擊首領領主入口 [{conf_entry:.4f}]...")
                    self.mouse.click(rect["left"] + pos_entry[0], rect["top"] + pos_entry[1])
                    time.sleep(0.3)
                    return True

        # 3. 頁籤已開啟 (Lord_entry_after)，依序選擇最高優先權可用 Boss 發起戰鬥
        bosses_config = self.machine.config.get("bosses", {})
        selected_boss = None

        for boss_key in avail_bosses:
            b_cfg = bosses_config.get(boss_key, {})
            temp_path = b_cfg.get("template")
            if temp_path and os.path.exists(os.path.join("templates", temp_path)):
                pos_b, conf_b = self.matcher.match(screen_img, temp_path, threshold=0.75)
                if pos_b:
                    b_name = b_cfg.get("name", boss_key)
                    max_cd = b_cfg.get("cooldown_seconds", 7200.0)
                    logging.info(f"🔍 [首領討伐] 於畫面發現 Boss 卡片 [{b_name}] [{conf_b:.4f}]，檢查是否有冷卻木牌...")
                    
                    # 點擊前防護：先不進行點擊，進行卡片木牌 / OCR 冷卻時間辨識
                    rem_secs, raw_text = self._check_card_cooldown_ocr(screen_img, pos_b, max_allowed_seconds=max_cd)
                    if rem_secs is not None and rem_secs > 0:
                        logging.info(
                            f"⏳ [首領討伐] 偵測到 Boss [{b_name}] 設有冷卻木牌！倒數時間: \"{raw_text}\" "
                            f"({format_seconds_to_readable(rem_secs)})，更新 DailyManager 並跳過點擊。"
                        )
                        if dm and hasattr(dm, "update_boss_cooldown"):
                            dm.update_boss_cooldown(boss_key, rem_secs)
                        continue  # 有木牌冷卻中：跳過點擊，續行比對佇列中下一個 Boss！

                    logging.info(f"🎯 [首領討伐] 確認 Boss [{b_name}] 無冷卻木牌！進行點擊選擇討伐！")
                    self.mouse.click(rect["left"] + pos_b[0], rect["top"] + pos_b[1])
                    self.current_target_boss = boss_key
                    selected_boss = boss_key
                    time.sleep(0.3)
                    break

        # 4. 若成功選取到可點擊 Boss，檢查點擊進入戰鬥按鈕 (stages/start.png)
        start_btn = self.machine.config.get("start_btn", "stages/start.png")
        if os.path.exists(os.path.join("templates", start_btn)):
            pos_start, conf_start = self.matcher.match(screen_img, start_btn, threshold=0.80)
            if pos_start:
                logging.info(f"🚀 [首領討伐] 點擊開始戰鬥按鈕 [{conf_start:.4f}]，轉移至 STATE_BATTLE 發起討伐！")
                self.mouse.click(rect["left"] + pos_start[0], rect["top"] + pos_start[1])
                self.machine.current_lord_boss_key = self.current_target_boss or selected_boss or avail_bosses[0]
                self.machine.transition_to(self.machine.STATE_BATTLE)
                time.sleep(0.3)
                return True

        return False
