import os
import time
import logging
from states.handlers.base import BaseStateHandler

class ResultHandler(BaseStateHandler):
    def __init__(self, machine):
        super().__init__(machine)
        self.no_match_count = 0
        self.continue_click_count = 0
        self.subflow_step = "INIT_DELAY"  # INIT_DELAY -> CONTINUE_LOOP -> FINAL_MATCH

    def reset_state(self):
        self.subflow_step = "INIT_DELAY"
        self.continue_click_count = 0
        self.no_match_count = 0
        self._recorded_kill_for_current_battle = False

    def _check_final_buttons_exist(self, screen_img, should_exit_battle):
        """檢查終局離場或再戰按鈕是否已經出現在畫面上"""
        if should_exit_battle:
            exit_candidates = ["exit_battle.png", "goback_town.png", "domains/common/exit_to_lobby.png", "common/quit.png"]
            for exit_btn in exit_candidates:
                if os.path.exists(os.path.join("templates", exit_btn)):
                    pos, _ = self.matcher.match(screen_img, exit_btn, threshold=0.75, quiet=True)
                    if pos:
                        return True
        else:
            if os.path.exists(os.path.join("templates", "stages/retry.png")):
                pos, _ = self.matcher.match(screen_img, "stages/retry.png", threshold=0.80, quiet=True)
                if pos:
                    return True
        return False

    def handle(self, screen_img, rect):
        matched = self._handle_impl(screen_img, rect)
        if matched:
            self.no_match_count = 0
            return
            
        # 如果走到了這裡，說明本輪沒有匹配到任何東西
        self.no_match_count += 1
        if self.no_match_count >= 5:
            logging.warning("⚠️ 結算畫面連續 5 次未偵測到任何結算按鈕，判定可能已退出或跳轉，重設狀態為 UNKNOWN 進行重新定位。")
            self.reset_state()
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return
            
        logging.info("⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...")

    def _handle_impl(self, screen_img, rect):
        """
        戰鬥結算獨立子流程 (Result Subflow):
        1. 步驟 1 (INIT_DELAY): 剛進入結算時，固定休眠 1.5 秒讓勝利特效與第一層動畫完全繪製與定格。
        2. 步驟 2 (CONTINUE_LOOP): 輪詢 continue.png，每次點擊成功後固定休眠 1.0 秒。若連續沒點到或滿 2 次則轉移至 FINAL_MATCH。
        3. 步驟 3 (FINAL_MATCH): 白名單二分法配對。續戰場次僅點擊 retry (1.0s 休眠)，離場場次僅點擊 exit_battle (1.0s 休眠)。
        """
        # 0. 優先檢查是否已回到準備大廳/關卡選單 (出現 select_stage 或 select_stage_after 代表戰鬥結算已結束)
        lobby_features = [
            "common/select_stage.png",
            "common/select_stage_after.png"
        ]
        for l_temp in lobby_features:
            if os.path.exists(os.path.join("templates", l_temp)):
                match_res = self.matcher.match(screen_img, l_temp, threshold=0.80, brightness_threshold=0.70, quiet=True)
                if isinstance(match_res, (tuple, list)) and len(match_res) >= 2 and match_res[0]:
                    pos_l, conf_l = match_res[0], match_res[1]
                    logging.info(f"👉 結算辨識：偵測到關卡大廳獨有特徵 [{l_temp}] (相似度: {conf_l:.4f})，代表戰鬥結算已結束並已回到大廳，轉移至 NAVIGATING。")
                    self.reset_state()
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    return True

        # 0.1 優先檢查是否已回到領地主場景 (看到 explore_btn 代表戰鬥結算已結束並已回到領地)
        cur_type = self.machine.config.get("type") if self.machine.config else None
        if cur_type == "domain" or (self.machine.config and self.machine.config.get("domain")):
            for d_btn in ["domains/golden_empire/explore_btn.png", "domains/common/exit_to_lobby.png"]:
                if os.path.exists(os.path.join("templates", d_btn)):
                    pos_d, conf_d = self.matcher.match(screen_img, d_btn, threshold=0.75, quiet=True)
                    if pos_d:
                        logging.info(f"👉 結算辨識：偵測到領地主場景特徵 [{d_btn}] (相似度: {conf_d:.4f})，戰鬥結算已結束並已回到領地，轉移至 DOMAIN_EXPLORE。")
                        self.reset_state()
                        self.machine.transition_to(self.machine.STATE_DOMAIN_EXPLORE)
                        return True

        # Lord Boss may return directly to its lobby after the last Continue.
        # Treat that lobby as terminal evidence before the continue loop waits.
        is_lord_boss_result = (
            cur_type == "lord_boss"
            or "lord_boss" in (getattr(self.machine, "dev_subflows", []) or [])
            or getattr(self.machine, "current_lord_boss_key", None) is not None
        )
        if is_lord_boss_result and os.path.exists(
            os.path.join("templates", "load/Lord_entry_after.png")
        ):
            pos_l, conf_l = self.matcher.match(
                screen_img,
                "load/Lord_entry_after.png",
                threshold=0.80,
                brightness_threshold=0.70,
                quiet=True,
            )
            if pos_l:
                logging.info(
                    "Lord Boss result completed: returned to lobby "
                    "[load/Lord_entry_after.png] (confidence: %.4f).",
                    conf_l,
                )
                boss_key = getattr(self.machine, "current_lord_boss_key", None)
                daily_manager = getattr(self.machine, "daily_manager", None)
                if boss_key and daily_manager:
                    daily_manager.record_lord_boss_fight(boss_key)
                self.machine.current_lord_boss_key = None
                self.reset_state()
                self.machine.transition_to(self.machine.STATE_LORD_BOSS)
                return True

        # =========================================================================
        # 步驟 1：結算初登場沉澱 (INIT_DELAY)
        # =========================================================================
        if self.subflow_step == "INIT_DELAY":
            logging.info("⏳ [結算子流程 Step 1] 戰鬥剛結束，執行初次登場沉澱 (休眠 1.5 秒)，等待勝負畫面與第一層彈窗定格...")
            time.sleep(1.5)
            self.subflow_step = "CONTINUE_LOOP"
            # 重新擷取第一層定格後的最新畫面，隨後貫穿向下執行 CONTINUE_LOOP
            if self.machine.capturer:
                cap_fresh = self.machine.capturer.capture(rect)
                if cap_fresh is not None:
                    screen_img = cap_fresh

        # A1. 戰敗防護 (defeat.png)
        if os.path.exists(os.path.join("templates", "defeat.png")):
            pos_defeat, conf_defeat = self.matcher.match(screen_img, "defeat.png", threshold=0.75)
            if pos_defeat:
                logging.info(f"💀 結算處理：確認處於戰敗畫面 [{conf_defeat:.4f}]。")
                
                is_dungeon = (
                    self.machine.config.get("type") == "dungeon" or
                    getattr(self.machine, "is_in_dungeon", False)
                )
                is_domain = (
                    self.machine.config.get("type") == "domain" or
                    bool(self.machine.config.get("domain"))
                )
                if is_dungeon:
                    max_defeat = 2
                elif is_domain:
                    max_defeat = self.machine.config.get("domain_max_defeat", 5)
                else:
                    max_defeat = self.machine.config.get("stage_max_defeat", 2)
                
                if self.machine.defeat_count >= (max_defeat - 1):
                    self.reset_state()
                    return self._run_defeat_giveup_subflow(rect, is_dungeon=is_dungeon)

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
                    click_x = rect["left"] + pos_defeat[0] - 140
                    click_y = rect["top"] + pos_defeat[1] + 250
                    logging.warning(f"⚠️ 未匹配到重新開始按鈕圖，使用防禦性相對座標點擊: ({click_x}, {click_y})")
                    self.mouse.click(click_x, click_y)
                    
                self.machine.defeat_count += 1
                self.reset_state()
                logging.info(f"🚀 已點擊重新開始按鈕，累計戰敗次數: {self.machine.defeat_count}")
                self.machine.last_result_retry_click_time = time.time()
                self.machine.run_count += 1
                time.sleep(1.0)
                logging.info(f"🚀 點擊重新開始按鈕，進入過渡載入等待... (累計啟動次數: {self.machine.run_count})")
                self.machine.transition_to(self.machine.STATE_LOADING)
                return True

        # 勝利過關事件廣播 (每個戰鬥場次僅累加紀錄一次)
        if not getattr(self, "_recorded_kill_for_current_battle", False):
            self._recorded_kill_for_current_battle = True
            if getattr(self.machine, "quest_scheduler", None):
                cfg = getattr(self.machine, "config", {}) or {}
                self.machine.quest_scheduler.record_kill_event(
                    dungeon_index=cfg.get("dungeon_index"),
                    stage_level=cfg.get("stage_level"),
                    sub_stage=cfg.get("sub_stage")
                )

        # 計算是否滿足離場條件 (第 4、8、10 場 / 滿背包 / 體力退避等)
        is_daily = self.machine.is_daily_pipeline_active()
        boss_available = False
        if is_daily and getattr(self.machine, "daily_manager", None):
            dm = self.machine.daily_manager
            boss_available = self.machine.has_available_selected_lord_boss()

        is_in_tier4 = is_daily and self.machine.config.get("is_tier4_fallback", False)
        quest_batch_completed = False
        has_higher_priority_task = False
        if is_daily and getattr(self.machine, "quest_scheduler", None):
            quest_batch_completed = self.machine.quest_scheduler.is_current_task_batch_completed(
                dungeon_cooldowns=self.machine.dungeon_cooldowns,
                current_config=self.machine.config
            )
            if not is_in_tier4:
                has_higher_priority_task = self.machine.quest_scheduler.has_higher_priority_task_ready(
                    current_config=self.machine.config,
                    dungeon_cooldowns=self.machine.dungeon_cooldowns
                )

        daily_quest_ready_to_preempt_tier4 = (
            is_in_tier4 and self.machine.has_ready_daily_quest_preemption()
        )
        if daily_quest_ready_to_preempt_tier4:
            logging.info("📋 [Tier 4 插隊] 偵測到 Daily 懸賞任務冷卻結束；本場結算後離場並切回懸賞任務。")
        elif is_daily and boss_available:
            logging.info("⚔️ [Tier 4 插隊] 偵測到領主 Boss 冷卻結束可挑戰；本場結算後離場並切回 Boss 討伐。")

        should_exit_battle = (
            getattr(self.machine, "pending_daily_reset_exit", False) or
            self.machine.stamina_retreat_start_time is not None or
            self.machine.need_bag_cleaning or 
            self.machine.need_diamond_collection or 
            (self.machine.enable_bread and self.machine.need_bread_collection) or
            (self.machine.config.get("type") == "mix" and self.machine.has_available_dungeon()) or
            (is_daily and boss_available) or
            daily_quest_ready_to_preempt_tier4 or
            (is_daily and quest_batch_completed and not is_in_tier4) or
            (is_daily and has_higher_priority_task and not is_in_tier4)
        )

        # =========================================================================
        # 步驟 2：Continue 推進閉環 (CONTINUE_LOOP)
        # =========================================================================
        if self.subflow_step == "CONTINUE_LOOP":
            # 0. 若非離場場次，優先檢查再戰按鈕是否已經出現，避免無效點擊繼續按鈕導致誤退回大廳
            if not should_exit_battle and os.path.exists(os.path.join("templates", "stages/retry.png")):
                pos_r, conf_r = self.matcher.match(screen_img, "stages/retry.png", threshold=0.80, quiet=True)
                if pos_r:
                    logging.info(f"👉 [結算 Step 2] 續戰場次且偵測到「再戰」按鈕 [stages/retry.png] ({conf_r:.4f})，切換至 FINAL_MATCH！")
                    self.subflow_step = "FINAL_MATCH"

        if self.subflow_step == "CONTINUE_LOOP":
            continue_configs = [
                (self.machine.continue_template, 0.9, 0.70),
                ("common/continue1.png", 0.9, 0.70),
                ("common/continue2.png", 0.9, 0.70),
                ("common/continue_gray.png", 0.88, 0.70)
            ]
            
            # 1. 嘗試配對畫面上現存的 continue 按鈕
            matched_c_temp, pos_c = None, None
            for c_temp, thresh, b_thresh in continue_configs:
                if c_temp and os.path.exists(os.path.join("templates", c_temp)):
                    pos, conf = self.matcher.match(screen_img, c_temp, threshold=thresh, brightness_threshold=b_thresh, quiet=True)
                    if pos:
                        matched_c_temp, pos_c = c_temp, pos
                        break

            if matched_c_temp and pos_c:
                # 🎯 核心真理：發起點擊，並 WHILE 輪詢直到該 continue 按鈕徹底從畫面上消失 (1.0 秒未消失自動補點)！
                click_x = rect["left"] + pos_c[0]
                click_y = rect["top"] + pos_c[1]
                logging.info(f"👉 [結算 Step 2] 偵測到『繼續』按鈕 ({matched_c_temp})，發起點擊並 WHILE 輪詢直到消失...")
                
                self.click_and_wait_until_gone(
                    matched_c_temp, click_x, click_y, rect,
                    timeout=5.0, threshold=0.9, brightness_threshold=0.70, check_interval=0.25, post_delay=0.8, retry_interval=1.0
                )

                return True

            # 2. 若畫面上已無 continue 按鈕，檢查是否有通用 confirm.png
            pos_conf, _ = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8, quiet=True)
            if pos_conf:
                logging.info("👉 [結算 Step 2] 偵測到通用確認按鈕，點擊並 WHILE 輪詢直到消失...")
                self.click_and_wait_until_gone(
                    "common/confirm.png", rect["left"] + pos_conf[0], rect["top"] + pos_conf[1], rect,
                    timeout=5.0, threshold=0.9, check_interval=0.25, post_delay=0.8, retry_interval=1.0
                )
                return True

            # 3. 只有當 continue 與 confirm 均徹底消失，且終局按鈕 (retry/exit) 已顯現時，才轉移至 FINAL_MATCH
            cur_type = self.machine.config.get("type") if self.machine.config else None
            if cur_type == "domain" or (self.machine.config and self.machine.config.get("domain")):
                logging.info("👉 [結算 Step 2] (領地模式) continue 已點擊完畢且消失，戰鬥結算順暢結束，轉移至 DOMAIN_EXPLORE！")
                self.reset_state()
                self.machine.transition_to(self.machine.STATE_DOMAIN_EXPLORE)
                return True

            final_btn_found = self._check_final_buttons_exist(screen_img, should_exit_battle)
            if final_btn_found:
                logging.info("👉 [結算 Step 2] 畫面上已無 continue/confirm，且終局按鈕 (retry/exit) 已顯現，確信 continue 階段結束，切換至 FINAL_MATCH！")
                self.subflow_step = "FINAL_MATCH"
            else:
                logging.info("⌛ [結算 Step 2] continue 按鈕淡出/過場中，等待下一個 continue 或終局按鈕顯現...")
                return False

        # =========================================================================
        # 步驟 3：終局白名單嚴格配對 (FINAL_MATCH)
        # =========================================================================
        if self.subflow_step == "FINAL_MATCH":
            if should_exit_battle:
                # 情況 B：第 4、8、10 場 ➔ 僅能配對離場按鈕
                exit_candidates = ["exit_battle.png", "goback_town.png", "domains/common/exit_to_lobby.png", "common/quit.png"]
                for exit_btn in exit_candidates:
                    if os.path.exists(os.path.join("templates", exit_btn)):
                        pos_exit, conf_exit = self.matcher.match(screen_img, exit_btn, threshold=0.75, quiet=True)
                        if pos_exit:
                            logging.info(f"👉 [結算子流程 Step 3] 離場條件成立 (第 4/8/10 場或需領獎)，發現離場按鈕 [{exit_btn}] ({conf_exit:.4f})，點擊退出戰鬥 (配對確認直到消失)...")
                            self.click_and_wait_until_gone(exit_btn, rect["left"] + pos_exit[0], rect["top"] + pos_exit[1], rect)
                            self.machine.is_in_dungeon = False
                            self.reset_state()

                            if getattr(self.machine, "current_lord_boss_key", None):
                                b_key = self.machine.current_lord_boss_key
                                self.machine.current_lord_boss_key = None
                                if getattr(self.machine, "daily_manager", None):
                                    self.machine.daily_manager.record_lord_boss_fight(b_key)

                            self.machine.pending_daily_reset_exit = False
                            next_state = self.machine.STATE_COLLECT_ONLY if self.machine.is_in_collect_only_mode() else self.machine.STATE_NAVIGATING
                            self.machine.transition_to(next_state)
                            return True
            else:
                # 情況 A：非第 4、8、10 場 ➔ 僅能配對 RETRY 再戰按鈕 (絕不點擊任何離場/大廳按鈕)
                pos_retry, conf_retry = self.matcher.match(screen_img, "stages/retry.png", threshold=0.8, quiet=True)
                if pos_retry:
                    logging.info(f"👉 [結算子流程 Step 3] 非離場場次，偵測到「再戰」按鈕 [{conf_retry:.4f}]，點擊繼續下一場戰鬥 (配對確認直到消失)...")
                    self.click_and_wait_until_gone("stages/retry.png", rect["left"] + pos_retry[0], rect["top"] + pos_retry[1], rect, post_delay=0.8)
                    self.machine.last_result_retry_click_time = time.time()
                    self.machine.run_count += 1
                    self.reset_state()
                    time.sleep(1.0)  # 固定 1.0 秒過渡等待，確保遊戲視窗響應點擊並啟動載入
                    logging.info(f"🚀 點擊再戰按鈕，進入過渡載入等待... (累計啟動次數: {self.machine.run_count})")
                    self.machine.transition_to(self.machine.STATE_LOADING)
                    return True

        # 領地模式 (Domain Mode)：結算完成後切回 DOMAIN_EXPLORE
        if cur_type == "domain" or (self.machine.config and self.machine.config.get("domain")):
            logging.info("👉 結算辨識 (領地模式)：戰鬥結算已結束，轉移回 DOMAIN_EXPLORE 繼續探索。")
            self.reset_state()
            self.machine.transition_to(self.machine.STATE_DOMAIN_EXPLORE)
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
        next_state = self.machine.STATE_COLLECT_ONLY if self.machine.is_in_collect_only_mode() else self.machine.STATE_NAVIGATING
        self.machine.transition_to(next_state)
        time.sleep(0.2)
        return True
