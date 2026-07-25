import os
import time
import logging
from states.handlers.base import BaseStateHandler

class ResultHandler(BaseStateHandler):
    def __init__(self, machine):
        super().__init__(machine)
        self.no_match_count = 0

    def handle(self, screen_img, rect):
        matched = self._handle_impl(screen_img, rect)
        if matched:
            self.no_match_count = 0
            return
            
        # 如果走到了這裡，說明本輪沒有匹配到任何東西
        self.no_match_count += 1
        if self.no_match_count >= 5:
            logging.warning("⚠️ 結算畫面連續 5 次未偵測到任何結算按鈕，判定可能已退出或跳轉，重設狀態為 UNKNOWN 進行重新定位。")
            self.no_match_count = 0
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return
            
        logging.info("⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...")

    def _handle_impl(self, screen_img, rect):
        """
        處理結算點擊。若成功點擊任何按鈕，回傳 True；否則回傳 False。
        """
        # A1. 優先檢查是否戰敗 (defeat.png)
        if os.path.exists(os.path.join("templates", "defeat.png")):
            pos_defeat, conf_defeat = self.matcher.match(screen_img, "defeat.png", threshold=0.75)
            if pos_defeat:
                logging.info(f"💀 結算處理：確認處於戰敗畫面 [{conf_defeat:.4f}]。")
                
                is_dungeon = (
                    self.machine.config.get("type") == "dungeon" or
                    getattr(self.machine, "is_in_dungeon", False)
                )
                max_defeat = 2 if is_dungeon else self.machine.config.get("stage_max_defeat", 2)
                
                if self.machine.defeat_count >= (max_defeat - 1):
                    return self._run_defeat_giveup_subflow(rect, is_dungeon=is_dungeon)

                # 優先嘗試比對戰敗重新開始按鈕 (defeat_retry.png) 或通用再戰按鈕 (stages/retry.png)
                pos_retry = None
                conf_retry = 0.0
                matched_btn = None
                
                for btn_name in ["defeat_retry.png", "stages/retry.png"]:
                    if os.path.exists(os.path.join("templates", btn_name)):
                        pos, conf = self.matcher.match(screen_img, btn_name, threshold=0.75)
                        if pos:
                            pos_retry = pos
                            conf_retry = conf
                            matched_btn = btn_name
                            break
                            
                if pos_retry:
                    logging.info(f"👉 偵測到重新開始按鈕 [{matched_btn}] (信心度: {conf_retry:.4f})，進行點擊重新開始。")
                    self.mouse.click(rect["left"] + pos_retry[0], rect["top"] + pos_retry[1])
                else:
                    # 作為防禦性 Backup，使用戰敗大圖中心點向左下角相對偏移點擊
                    # 戰敗大圖寬高為 546x691，中心點向左偏 140 像素，向下偏 250 像素，大約為重新開始按鈕
                    click_x = rect["left"] + pos_defeat[0] - 140
                    click_y = rect["top"] + pos_defeat[1] + 250
                    logging.warning(f"⚠️ 未匹配到重新開始按鈕圖，使用防禦性相對座標點擊: ({click_x}, {click_y})")
                    self.mouse.click(click_x, click_y)
                    
                self.machine.defeat_count += 1
                logging.info(f"🚀 已點擊重新開始按鈕，累計戰敗次數: {self.machine.defeat_count}")
                self.machine.last_result_retry_click_time = time.time()
                self.machine.run_count += 1
                logging.info(f"🚀 點擊重新開始按鈕，進入過渡載入等待... (累計啟動次數: {self.machine.run_count})")
                self.machine.transition_to(self.machine.STATE_LOADING)
                time.sleep(0.1)
                return True


        is_daily = self.machine.is_daily_pipeline_active()
        boss_available = False
        if is_daily and getattr(self.machine, "daily_manager", None):
            dm = self.machine.daily_manager
            if hasattr(dm, "is_subflow_completed") and not dm.is_subflow_completed("lord_boss"):
                boss_available = dm.has_available_lord_boss()

        quest_batch_completed = False
        if is_daily and getattr(self.machine, "quest_scheduler", None):
            quest_batch_completed = self.machine.quest_scheduler.is_current_task_batch_completed(dungeon_cooldowns=self.machine.dungeon_cooldowns)

        should_exit_battle = (
            self.machine.stamina_retreat_start_time is not None or
            self.machine.need_bag_cleaning or 
            self.machine.need_diamond_collection or 
            (self.machine.enable_bread and self.machine.need_bread_collection) or
            (self.machine.config.get("type") == "mix" and self.machine.has_available_dungeon()) or
            (is_daily and boss_available) or
            (is_daily and quest_batch_completed)
        )


        # 1. 第一順位：若判定應離場，優先比對與點擊「離開/返回」按鈕
        if should_exit_battle:
            exit_candidates = ["exit_battle.png", "goback_town.png", "common/quit.png"]
            for exit_btn in exit_candidates:
                if os.path.exists(os.path.join("templates", exit_btn)):
                    pos_exit, conf_exit = self.matcher.match(screen_img, exit_btn, threshold=0.75, quiet=True)
                    if pos_exit:
                        if self.machine.config.get("type") == "mix" and self.machine.has_available_dungeon():
                            status_str, avail_names = self.machine.get_dungeon_cooldown_status()
                            avail_str = ", ".join(avail_names) if avail_names else "無"
                            logging.info(f"⏳ [混合模式] 結算時偵測到可用地下城！各副本冷卻情形: {status_str} | 判定可挑戰: [{avail_str}]")
                        logging.info(f"👉 偵測到離場條件成立，發現離開/返回按鈕 [{exit_btn}] ({conf_exit:.4f})，點擊退出結算。")
                        self.mouse.click(rect["left"] + pos_exit[0], rect["top"] + pos_exit[1])
                        self.machine.is_in_dungeon = False
                        
                        if getattr(self.machine, "current_lord_boss_key", None):
                            b_key = self.machine.current_lord_boss_key
                            self.machine.current_lord_boss_key = None
                            if getattr(self.machine, "daily_manager", None):
                                self.machine.daily_manager.record_lord_boss_fight(b_key)
                                
                        next_state = self.machine.STATE_COLLECT_ONLY if self.machine.stamina_retreat_start_time is not None else self.machine.STATE_NAVIGATING
                        self.machine.transition_to(next_state)
                        time.sleep(0.5)
                        return True

        # 2. 第二順位：比對「繼續」過渡按鈕 (推進結算流程，使離場按鈕或下一次畫面顯現)
        continue_configs = [
            (self.machine.continue_template, 0.80, 0.0),
            ("common/continue1.png", 0.80, 0.0),
            ("common/continue2.png", 0.80, 0.0),
            ("common/continue_gray.png", 0.88, 0.70)
        ]
        for c_temp, thresh, b_thresh in continue_configs:
            if c_temp and os.path.exists(os.path.join("templates", c_temp)):
                pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=thresh, brightness_threshold=b_thresh, quiet=True)
                if pos_c:
                    logging.info(f"👉 偵測到「繼續」按鈕 ({c_temp}) (信心度: {conf_c:.4f})，進行點擊推進結算過渡。")
                    self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])

                    if getattr(self.machine, "current_lord_boss_key", None):
                        b_key = self.machine.current_lord_boss_key
                        self.machine.current_lord_boss_key = None
                        dm = getattr(self.machine, "daily_manager", None)
                        if dm:
                            dm.record_lord_boss_fight(b_key)

                    time.sleep(0.35)
                    return True

        # 3. 第三順位：通用確認彈窗 (common/confirm.png)
        pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8, quiet=True)
        if pos_conf:
            logging.info(f"👉 偵測到結算通用確認按鈕，進行點擊。信心度: {conf_conf:.4f}")
            self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
            time.sleep(0.3)
            return True

        # 4. 第四順位：如果已滿足離場條件 (should_exit_battle == True)，徹底封鎖 retry (再戰)
        if should_exit_battle:
            logging.info("⏳ [離場防護] 已滿足離場條件，等待離場/返回按鈕 (goback_town/exit_battle) 顯現，禁止點擊再戰。")
            return True

        # 5. 第五順位：無離場需求且過渡結束時，點擊「再戰」繼續挑戰下一場
        pos_retry, conf_retry = self.matcher.match(screen_img, "stages/retry.png", threshold=0.8, quiet=True)
        if pos_retry:
            logging.info("👉 點擊「再戰」！")
            self.mouse.click(rect["left"] + pos_retry[0], rect["top"] + pos_retry[1])
            self.machine.last_result_retry_click_time = time.time()
            self.machine.run_count += 1
            logging.info(f"🚀 點擊再戰按鈕，進入過渡載入等待... (累計啟動次數: {self.machine.run_count})")
            self.machine.transition_to(self.machine.STATE_LOADING)
            time.sleep(0.35)
            return True

        # C. 檢查是否已經默默回到準備大廳/頁籤選單 (包含 Lord_entry_after, dungeon_after, goback_town)
        lobby_templates = []
        if self.machine.config.get("lobby_start_btn"):
            lobby_templates.append(self.machine.config.get("lobby_start_btn"))
        lobby_templates.extend(["load/Lord_entry_after.png", "dungeons/dungeon_after.png", "goback_town.png"])

        for l_temp in lobby_templates:
            if l_temp and os.path.exists(os.path.join("templates", l_temp)):
                pos_l, conf_l = self.matcher.match(screen_img, l_temp, threshold=0.80, check_brightness=True, brightness_threshold=0.70, quiet=True)
                if pos_l:
                    logging.info(f"👉 結算辨識：偵測到畫面已切回大廳/頁籤 [{l_temp}] (相似度: {conf_l:.4f})，即時結束結算狀態。")
                    if getattr(self.machine, "current_lord_boss_key", None):
                        b_key = self.machine.current_lord_boss_key
                        self.machine.current_lord_boss_key = None
                        dm = getattr(self.machine, "daily_manager", None)
                        if dm:
                            dm.record_lord_boss_fight(b_key)

                    dev_subs = getattr(self.machine, "dev_subflows", None) or []
                    cur_type = self.machine.config.get("type") if self.machine.config else None
                    if (cur_type == "lord_boss" or "lord_boss" in dev_subs) and l_temp == "load/Lord_entry_after.png":
                        self.machine.transition_to(self.machine.STATE_LORD_BOSS)
                    elif self.machine.stamina_retreat_start_time is not None:
                        self.machine.transition_to(self.machine.STATE_COLLECT_ONLY)
                    else:
                        self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    return True
            
        # D. 檢查是否已經進入戰鬥狀態 (避免人手點擊或自動戰鬥提早開始時卡在結算超時)
        for feat in ["common/auto.png", "battle/battle_features_1.png", "battle/battle_features_2.png"]:
            if os.path.exists(os.path.join("templates", feat)):
                thresh = 0.65 if feat == "common/auto.png" else 0.70
                pos_auto, conf_auto = self.matcher.match(screen_img, feat, threshold=thresh)
                if pos_auto:
                    logging.info(f"⚔️ 結算畫面偵測到戰鬥特徵 [{feat}] (相似度: {conf_auto:.4f})，判定已進入戰鬥，將狀態切換至 BATTLE。")
                    self.machine.battle_start_time = time.time()
                    self.machine.transition_to(self.machine.STATE_BATTLE)
                    return True

        return False

    def _run_defeat_giveup_subflow(self, rect, is_dungeon=True):
        """
        [子流程] 統一戰敗放棄流程（比對 defeat_giveup.png 與 common/confirm.png）
        """
        mode_name = "地下城" if is_dungeon else "普通關卡"
        logging.warning(f"🚨 連續戰敗次數已達 {self.machine.defeat_count + 1} 次！執行「放棄挑戰」流程 (當前模式: {mode_name})...")

        giveup_temp = "defeat_giveup.png"
        if os.path.exists(os.path.join("templates", giveup_temp)):
            cap_img = self.machine.capturer.capture(rect)
            if cap_img is not None:
                pos_g, conf_g = self.matcher.match(cap_img, giveup_temp, threshold=0.75)
                if pos_g:
                    logging.info(f"👉 偵測到放棄挑戰按鈕 [{giveup_temp}] (信心度: {conf_g:.4f})，進行點擊。")
                    self.mouse.click(rect["left"] + pos_g[0], rect["top"] + pos_g[1])

        # 進入確認放棄子流程，等待並點擊 confirm.png
        start_time = time.time()
        while time.time() - start_time < 5.0:
            loop_screen = self.machine.capturer.capture(rect)
            if loop_screen is not None:
                pos_c, conf_c = self.matcher.match(loop_screen, "common/confirm.png", threshold=0.80)
                if pos_c:
                    logging.info(f"👉 偵測到退出確認按鈕 'common/confirm.png' (相似度: {conf_c:.4f})，進行點擊確認。")
                    self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                    break
            time.sleep(0.3)

        if is_dungeon:
            idx = getattr(self.machine, "current_dungeon_index", 0)
            cooldown_map = self.machine.config.get("cooldown_map", {})
            cd_seconds = cooldown_map.get(idx, 900.0)
            self.machine.dungeon_cooldowns[idx] = time.time() + cd_seconds
            logging.info(f"⏳ 貪婪地下城：戰敗放棄！設定地下城 {idx} 進入 {int(cd_seconds / 60)} 分鐘冷卻期。")
        else:
            logging.warning("⚠️ 普通關卡戰敗放棄完成，重置戰敗計數並切換至 NAVIGATING。")

        self.machine.defeat_count = 0
        self.machine.is_in_dungeon = False
        next_state = self.machine.STATE_COLLECT_ONLY if self.machine.stamina_retreat_start_time is not None else self.machine.STATE_NAVIGATING
        self.machine.transition_to(next_state)
        time.sleep(0.2)
        return True
