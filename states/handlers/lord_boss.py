import cv2
import os
import time
import logging
from states.handlers.base import BaseStateHandler
from utils.time_parser import format_seconds_to_readable
from utils.cooldown_detector import detect_cooldown_sign_and_time
from utils.card_navigator import CardListNavigator

class LordBossHandler(BaseStateHandler):
    """
    首領領主討伐 (Lord Boss Subflow) 狀態處理器。
    負責大廳領主頁籤比對、點擊前卡片 OCR 冷卻防護、選擇可挑戰 Boss (育母蜘蛛/古代惡靈) 與發起戰鬥。
    整合 CardListNavigator 實現選關前先復位拉至最左側起點與跨頁滑動搜尋能力。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"
        self.current_target_boss = None
        self.last_card_click_time = 0.0
        self.has_reset_to_left = False
        self.last_lord_scroll_time = 0.0

    def reset_state(self):
        """狀態重置與子流程生命週期初始化"""
        self.step_phase = "INIT"
        self.current_target_boss = None
        self.last_card_click_time = 0.0
        self.has_reset_to_left = False
        self.reset_swipe_count = 0
        self.last_lord_scroll_time = 0.0

    def _check_card_cooldown_ocr(self, screen_img, pos_b, temp_path, max_allowed_seconds=7200.0):
        """
        [ Clean Code 專比單張卡片 + Scale 自適應 ]
        依據匹配出的 Boss 單張卡片範本尺寸，在螢幕截圖中精確切出該「單張卡片區域」，
        並傳遞當前 scale 供 detect_cooldown_sign_and_time 進行等比例木牌比對。
        """
        try:
            full_path = os.path.join("templates", temp_path) if temp_path else None
            if not full_path or not os.path.exists(full_path):
                return None, None

            t_img = self.matcher._load_template(temp_path) if hasattr(self, "matcher") and self.matcher else cv2.imread(full_path)
            if t_img is None:
                return None, None
            t_h, t_w = t_img.shape[:2]

            h, w = screen_img.shape[:2]
            cx, cy = pos_b

            x1 = max(0, cx - t_w // 2)
            x2 = min(w, cx + t_w // 2)
            y1 = max(0, cy - t_h // 2)
            y2 = min(h, cy + t_h // 2)

            single_card_img = screen_img[y1:y2, x1:x2]
            scale = getattr(self.matcher, "template_scale", 1.0) if hasattr(self, "matcher") else 1.0
            
            has_cd, rem_secs, raw_text = detect_cooldown_sign_and_time(
                single_card_img, 
                self.machine.get_ocr_reader, 
                max_allowed_seconds=max_allowed_seconds, 
                threshold=0.58,
                scale=scale
            )
            if has_cd:
                return rem_secs, raw_text
        except Exception as e:
            logging.warning(f"⚠️ [首領討伐] 點擊前單張卡片 OCR 辨識過程異常: {e}")
        return None, None

    def handle(self, screen_img, rect):
        now = time.time()
        dm = getattr(self.machine, "daily_manager", None)
        avail_bosses = dm.get_available_lord_bosses() if dm else []

        # 若當前沒有可討伐的 Boss，結束首領討伐子流程，動態計算最快解鎖秒數並彈出下一個城鎮任務
        if not avail_bosses:
            logging.info("🎉 [首領討伐] 今日所有 Boss 已滿 5 次或均在冷卻中！結束討伐，動態設定冷卻緩衝並彈出下一城鎮任務...")
            if dm:
                if hasattr(dm, "set_lord_boss_cooldown"):
                    dm.set_lord_boss_cooldown()
                if hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("lord_boss")
            self.machine.pop_and_next_town_subflow()
            return True

        # 1. 檢查並使用相對優勢 API 比對領主頁籤是否已開啟
        entry_after = self.machine.config.get("entry_after_btn", "load/Lord_entry_after.png")
        entry_before = self.machine.config.get("entry_btn", "load/Lord_entry.png")
        
        is_opened, _, _, _ = self.match_mutually_exclusive_tabs(screen_img, entry_after, entry_before, margin=0.02, threshold=0.70)

        # 2. 若頁籤尚未開啟，進行大廳入口與頁籤點擊
        if not is_opened:
            self.has_reset_to_left = False  # 頁籤未開啟前重置拉左旗標
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

        # 3. 檢查「開始戰鬥」按鈕 (stages/start.png)，僅於已選取 Boss 時優先點擊並進行驗證
        start_btn = self.machine.config.get("start_btn", "stages/start.png")
        if self.current_target_boss and os.path.exists(os.path.join("templates", start_btn)):
            pos_start, conf_start = self.matcher.match(screen_img, start_btn, threshold=0.80)
            if pos_start:
                boss_key = self.current_target_boss
                b_name = self.machine.config.get("bosses", {}).get(boss_key, {}).get("name", boss_key)
                logging.info(f"🚀 [首領討伐] 點擊開始戰鬥按鈕 [{conf_start:.4f}]，啟動 2.5 秒戰鬥進場驗證 [{b_name}]...")
                self.mouse.click(rect["left"] + pos_start[0], rect["top"] + pos_start[1])

                battle_entered = False
                start_verify_t = time.time()
                battle_features = [
                    "battle/battle_features_1.png",
                    "battle/battle_features_2.png",
                    "common/auto.png"
                ]

                while time.time() - start_verify_t < 2.5:
                    time.sleep(0.3)
                    if self.capturer and rect:
                        fresh_img = self.capturer.capture(rect)
                        if fresh_img is not None:
                            for feat in battle_features:
                                if os.path.exists(os.path.join("templates", feat)):
                                    p_f, _ = self.matcher.match(fresh_img, feat, threshold=0.75, quiet=True)
                                    if p_f:
                                        battle_entered = True
                                        break
                    if battle_entered:
                        break

                if battle_entered:
                    logging.info(f"⚔️ [首領討伐] 成功比對到戰鬥特徵，確認進入戰鬥！轉移至 STATE_BATTLE 發起討伐 [{boss_key}]...")
                    self.machine.current_lord_boss_key = boss_key
                    self.machine.transition_to(self.machine.STATE_BATTLE)
                    return True
                else:
                    latest_img = self.capturer.capture(rect) if (self.capturer and rect) else None
                    still_start = False
                    if latest_img is not None and os.path.exists(os.path.join("templates", start_btn)):
                        p_still, _ = self.matcher.match(latest_img, start_btn, threshold=0.75, quiet=True)
                        if p_still:
                            still_start = True

                    if still_start or latest_img is None:
                        logging.warning(f"⚠️ [首領討伐] 點擊開始戰鬥 2.5 秒後未偵測到戰鬥特徵，且按鈕 [{start_btn}] 依然存在！判定 Boss [{b_name}] 次數已滿或無法挑戰。")
                        quit_template = "common/quit.png"
                        if latest_img is not None and os.path.exists(os.path.join("templates", quit_template)):
                            p_quit, _ = self.matcher.match(latest_img, quit_template, threshold=0.75)
                            if p_quit:
                                logging.info(f"🚪 [首領討伐] 點擊卡片關閉按鈕 [{quit_template}] 退回大廳...")
                                self.click_and_wait_until_gone(quit_template, rect["left"] + p_quit[0], rect["top"] + p_quit[1], rect, threshold=0.75)

                        if dm and hasattr(dm, "mark_boss_completed"):
                            dm.mark_boss_completed(boss_key)

                        self.reset_state()
                        self.machine.pop_and_next_town_subflow()
                        return True

        # 4. 若最近 1.5 秒內剛點擊過 Boss 卡片，冷卻等待進入戰鬥頁面，避免重複或連續點擊不同 Boss
        if now - self.last_card_click_time < 1.5:
            return True

        # 5. 特化邏輯：每次進入選關介面 (Lord_entry_after) 時，持續向右滑動拉回，直到看見「第一個 Boss (起點)」
        if is_opened and not self.has_reset_to_left and not self.current_target_boss:
            bosses_config = self.machine.config.get("bosses", {})
            first_boss_key = list(bosses_config.keys())[0] if bosses_config else None
            first_template = bosses_config.get(first_boss_key, {}).get("template") if first_boss_key else None
            
            # 檢查第一個 Boss (起點) 是否已經在畫面上
            is_start_visible = False
            conf_first = 0.0
            if first_template:
                is_start_visible, _, conf_first = CardListNavigator.is_first_card_visible(screen_img, self.matcher, first_template, threshold=0.78)
            
            if is_start_visible:
                logging.info(f"🎯 [首領討伐] 偵測到第一個 Boss (起點) [{first_boss_key}] (信心度: {conf_first:.4f})，已確立回歸最左側起點！")
                self.has_reset_to_left = True
                self.reset_swipe_count = 0
            else:
                reset_count = getattr(self, "reset_swipe_count", 0)
                if reset_count < 4:
                    logging.info(f"🧭 [首領討伐] 未見第一個 Boss [{first_boss_key}] (起點)，執行向右滑動拖曳拉回第 {reset_count + 1}/4 次...")
                    CardListNavigator.reset_to_left(self.mouse, rect)
                    self.reset_swipe_count = reset_count + 1
                    self.last_lord_scroll_time = now
                    time.sleep(1.2)
                    return True
                else:
                    logging.warning("⚠️ [首領討伐] 已連續向右拉動 4 次仍未見第一個 Boss，預設已達極限，停止拉回。")
                    self.has_reset_to_left = True
                    self.reset_swipe_count = 0

        # 滑動冷卻保護：若剛執行過滾動滑動，等待動畫完全靜止
        if now - self.last_lord_scroll_time < 1.2:
            return True

        # 6. 頁籤已開啟 (Lord_entry_after)，依序選擇可用 Boss 發起戰鬥
        bosses_config = self.machine.config.get("bosses", {})
        boss_matched = False

        for boss_key in avail_bosses:
            b_cfg = bosses_config.get(boss_key, {})
            temp_path = b_cfg.get("template")
            if temp_path and os.path.exists(os.path.join("templates", temp_path)):
                pos_b, conf_b = self.matcher.match(screen_img, temp_path, threshold=0.78)
                if pos_b:
                    boss_matched = True
                    b_name = b_cfg.get("name", boss_key)
                    max_cd = b_cfg.get("cooldown_seconds", 7200.0)
                    
                    # 過濾動畫尚未穩定的模糊卡片 (信心度需 >= 0.82)
                    if conf_b < 0.82:
                        logging.info(f"⌛ [首領討伐] 發現 Boss 卡片 [{b_name}] (信心度 {conf_b:.4f} < 0.82)，等待過場動畫穩定...")
                        time.sleep(1)
                        return True

                    logging.info(f"🔍 [首領討伐] 於畫面發現 Boss 卡片 [{b_name}] [{conf_b:.4f}]，檢查是否有冷卻木牌...")
                    
                    # 點擊前防護：專比單張卡片範本圖畫區，進行卡片木牌 / OCR 冷卻時間辨識
                    rem_secs, raw_text = self._check_card_cooldown_ocr(screen_img, pos_b, temp_path, max_allowed_seconds=max_cd)
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
                    self.last_card_click_time = now

                    # 若畫面上已存在「開始戰鬥」按鈕 (stages/start.png)，點擊並啟動 2.5 秒戰鬥進場驗證閉環
                    if os.path.exists(os.path.join("templates", start_btn)):
                        pos_start, conf_start = self.matcher.match(screen_img, start_btn, threshold=0.80)
                        if pos_start:
                            logging.info(f"🚀 [首領討伐] 點擊開始戰鬥按鈕 [{conf_start:.4f}]，啟動 2.5 秒戰鬥進場驗證...")
                            self.mouse.click(rect["left"] + pos_start[0], rect["top"] + pos_start[1])

                            battle_entered = False
                            start_verify_t = time.time()
                            battle_features = [
                                "battle/battle_features_1.png",
                                "battle/battle_features_2.png",
                                "common/auto.png"
                            ]

                            while time.time() - start_verify_t < 2.5:
                                time.sleep(0.3)
                                if self.capturer and rect:
                                    fresh_img = self.capturer.capture(rect)
                                    if fresh_img is not None:
                                        for feat in battle_features:
                                            if os.path.exists(os.path.join("templates", feat)):
                                                p_f, _ = self.matcher.match(fresh_img, feat, threshold=0.75, quiet=True)
                                                if p_f:
                                                    battle_entered = True
                                                    break
                                if battle_entered:
                                    break

                            if battle_entered:
                                logging.info(f"⚔️ [首領討伐] 成功比對到戰鬥特徵，確認進入戰鬥！轉移至 STATE_BATTLE 發起討伐 [{boss_key}]...")
                                self.machine.current_lord_boss_key = boss_key
                                self.machine.transition_to(self.machine.STATE_BATTLE)
                                return True
                            else:
                                latest_img = self.capturer.capture(rect) if (self.capturer and rect) else None
                                still_start = False
                                if latest_img is not None and os.path.exists(os.path.join("templates", start_btn)):
                                    p_still, _ = self.matcher.match(latest_img, start_btn, threshold=0.75, quiet=True)
                                    if p_still:
                                        still_start = True

                                if still_start or latest_img is None:
                                    logging.warning(f"⚠️ [首領討伐] 點擊開始戰鬥 2.5 秒後未偵測到戰鬥特徵，且按鈕 [{start_btn}] 依然存在！判定 Boss [{b_name}] 次數已滿或無法挑戰。")
                                    quit_template = "common/quit.png"
                                    if latest_img is not None and os.path.exists(os.path.join("templates", quit_template)):
                                        p_quit, _ = self.matcher.match(latest_img, quit_template, threshold=0.75)
                                        if p_quit:
                                            logging.info(f"🚪 [首領討伐] 點擊卡片關閉按鈕 [{quit_template}] 退回大廳...")
                                            self.click_and_wait_until_gone(quit_template, rect["left"] + p_quit[0], rect["top"] + p_quit[1], rect, threshold=0.75)

                                    if dm and hasattr(dm, "mark_boss_completed"):
                                        dm.mark_boss_completed(boss_key)

                                    self.reset_state()
                                    self.machine.pop_and_next_town_subflow()
                                    return True
                    break

        # 7. 若在畫面上未能匹配到當前欲尋找的 Boss 卡片，發動向左滑動翻頁
        if is_opened and not boss_matched and not self.current_target_boss:
            logging.info("🧭 [首領討伐] 當前畫面未發現可用 Boss 卡片，執行向左滑動翻頁搜尋...")
            CardListNavigator.swipe_left_page(self.mouse, rect, duration=0.8, inertia=False)
            self.last_lord_scroll_time = now
            time.sleep(1.2)

        return False
