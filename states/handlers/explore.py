import os
import time
import logging
import numpy as np
from states.handlers.base import BaseStateHandler

class ExploreHandler(BaseStateHandler):
    TREASURE_TERMINAL_ANCHORS = (
        "dungeons/gungeon_godown.png",
        "dungeons/dungeons_complete.png",
    )
    TREASURE_TERMINAL_THRESHOLD = 0.80

    def handle(self, screen_img, rect):
        """
        [地下城專屬] 依照優先級掃描探險事件。
        """
        # 0. 如果背包滿了，優先轉移至 BAG_CLEANING 狀態進行清理，暫停探索
        if self.machine.need_bag_cleaning:
            logging.info("🎒 地下城：偵測到需要清理背包，優先轉移至 BAG_CLEANING 狀態。")
            self.machine.transition_to(self.machine.STATE_BAG_CLEANING)
            return

        # 1. 檢查是否已過下樓冷卻時間，若是，則重設本層探索記憶
        if self.machine.dungeon_floor_transitioning and self.machine.last_godown_click_time:
            if time.time() - self.machine.last_godown_click_time > 4.0:
                logging.info("⏳ 下樓冷卻結束，已進入地下城新樓層，重設探索記憶。")
                self.machine.chest_opened_this_floor = False
                self.machine.skill_selected_this_floor = False
                self.machine.bless_received_this_floor = False
                self.machine.dungeon_floor_transitioning = False
                self.machine.last_godown_click_time = None

        # 2. 優先判定是否已經進入真實戰鬥中 (看見 common/auto.png)
        if os.path.exists(os.path.join("templates", "common/auto.png")):
            pos_auto, conf_auto = self.matcher.match(screen_img, "common/auto.png", threshold=0.7)
            if pos_auto:
                logging.info(f"⚔️ 偵測到戰鬥已真正開始（出現 auto 按鈕，相似度: {conf_auto:.4f}），進入戰鬥狀態！")
                self.machine.transition_to(self.machine.STATE_BATTLE)
                return

        # 3. 依優先級處理探險事件
        explore_priorities = (self.machine.config or {}).get("explore_priorities")
        if not isinstance(explore_priorities, list):
            logging.error(
                "[ExploreHandler] missing explore_priorities after EXPLORING transition; returning to UNKNOWN for recovery."
            )
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return

        for btn_name in explore_priorities:
            # 檢查模板檔案是否存在
            if not os.path.exists(os.path.join("templates", btn_name)):
                continue

            # 根據本層探索記憶，跳過已完成的重複地圖事件點選
            if btn_name == "dungeons/Treasure.png" and self.machine.chest_opened_this_floor:
                continue
            if btn_name == "dungeons/skill_event.png" and self.machine.skill_selected_this_floor:
                continue
            if btn_name == "dungeons/dungeon_bless.png" and self.machine.bless_received_this_floor:
                continue
                
            # 依不同探險按鈕特性設定自訂閥值，文字按鈕預設調低以提升匹配率，預設為 0.80
            thresholds = {
                "dungeons/Get_tresure.png": 0.70,
                "dungeons/Get_tresure_comfirm.png": 0.70,
                "common/confirm.png": 0.80,
                "common/ok.png": 0.80,
                "dungeons/choose.png": 0.70,
                "dungeons/choice_bless.png": 0.70,
                "common/quit.png": 0.75,
                "common/continue_gray.png": 0.88,
                "common/continue.png": 0.80,
            }
            thresh = thresholds.get(btn_name, 0.80)
            
            pos, conf = self.matcher.match(screen_img, btn_name, threshold=thresh)
            if pos:
                if btn_name == "dungeons/dungeons_complete.png":
                    logging.info(f"🎉 偵測到【地下城通關結束】({btn_name})，信心度: {conf:.4f}，點擊退出。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.run_count += 1
                    logging.info(f"📊 已完成第 {self.machine.run_count} 次地下城通關！")
                    
                    # 動態設定當前地下城的冷卻時間（從 config 配置中動態獲取）
                    if hasattr(self.machine, "current_dungeon_index") and self.machine.current_dungeon_index is not None:
                        cooldown_map = self.machine.config.get("cooldown_map", {})
                        cd_seconds = cooldown_map.get(self.machine.current_dungeon_index, 900.0)
                        self.machine.dungeon_cooldowns[self.machine.current_dungeon_index] = time.time() + cd_seconds
                        logging.info(f"⏳ 貪婪地下城：設定第 {self.machine.current_dungeon_index + 1} 個地下城進入 {int(cd_seconds / 60)} 分鐘冷卻期。")
                        if self.machine.config.get("type") == "mix":
                            status_str, avail_names = self.machine.get_dungeon_cooldown_status()
                            avail_str = ", ".join(avail_names) if avail_names else "無"
                            if not avail_names:
                                logging.info(f"⏳ [混合模式] 地下城全冷卻！各副本冷卻情形: {status_str} ➔ 無可用地下城，將退守切換至普通關卡 (Stage)。")
                            else:
                                logging.info(f"⏳ [混合模式] 地下城通關！各副本冷卻情形: {status_str} ➔ 剩餘可挑戰地下城: [{avail_str}]。")
                        
                    # 通關後回到最外層大廳，轉移至尋路導航狀態重新進副本
                    self.machine.is_in_dungeon = False
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    time.sleep(0.2)
                    

                elif btn_name == "dungeons/Treasure.png":
                    if self.machine.dungeon_floor_transitioning:
                        self._reset_floor_memory_transition()
                    logging.info(f"👉 偵測到寶箱地圖格 [{btn_name}]，信心度: {conf:.4f}，進行點擊並啟動「開啟寶箱」子流程。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.5)  # 等待寶箱開啟動畫開始
                    self.machine.chest_opened_this_floor = self._run_treasure_subflow(rect)
                    if not self.machine.chest_opened_this_floor:
                        logging.warning(
                            "[Treasure subflow] Completion was not verified; "
                            "keeping the floor treasure eligible for retry."
                        )
                    
                elif btn_name == "dungeons/skill_event.png":
                    if self.machine.dungeon_floor_transitioning:
                        self._reset_floor_memory_transition()
                    logging.info(f"👉 偵測到技能事件圖示 [{btn_name}]，信心度: {conf:.4f}，進行點擊並啟動「技能選擇」子流程。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.skill_selected_this_floor = True
                    time.sleep(0.5)  # 等待技能選擇對話框開啟動畫
                    self._run_skill_subflow(rect)
                    
                elif btn_name == "dungeons/dungeon_bless.png":
                    if self.machine.dungeon_floor_transitioning:
                        self._reset_floor_memory_transition()
                    logging.info(f"👉 偵測到接受祝福圖示 [{btn_name}]，信心度: {conf:.4f}，進行點擊並啟動「領取祝福」子流程。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.5)  # 等待祝福開啟動畫開始
                    bless_ok = self._run_bless_subflow(rect)
                    if bless_ok:
                        self.machine.bless_received_this_floor = True
                        self.machine.last_bless_claim_time = time.time()
                        logging.info("✅ 領取祝福子流程回傳成功，將本層祝福狀態標記為 True 並記錄時間。")
                    else:
                        self.machine.bless_received_this_floor = False
                        logging.warning("⚠️ 領取祝福子流程回傳失敗，保持 bless_received_this_floor = False 以備重新領取。")

                    
                elif btn_name in ["dungeons/gungeon_godown.png", "dungeons/gungeon_godown_confirm.png"]:
                    logging.info(f"🧭 偵測到下樓按鈕 [{btn_name}]，信心度: {conf:.4f}，點擊下樓並開始本層記憶冷卻。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    # 設定下樓點擊時間與過渡狀態，由冷卻時間屆滿後或在新樓層檢測到事件時重設
                    self.machine.last_godown_click_time = time.time()
                    self.machine.dungeon_floor_transitioning = True
                    self.machine.dungeon_defeat_count = 0
                    time.sleep(0.04)
                    
                elif btn_name == "dungeons/dungeon_fight.png":
                    logging.info(f"⚔️ 偵測到【戰鬥房入口】({btn_name})，信心度: {conf:.4f}，點擊進入。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    # 注意：此處不轉移至 STATE_BATTLE，因為進入後需要先選擇祝福 (bless)。
                    # 我們將等待畫面出現 auto.png 後，由本方法最上方的判定自動轉入戰鬥狀態。
                    time.sleep(0.03)
                    
                elif btn_name == "dungeons/leave.png":
                    self.machine.is_in_dungeon = True
                    if getattr(self.machine, "dungeon_floor_transitioning", False):
                        self._reset_floor_memory_transition()
                    logging.info(f"🏰 偵測到地下城樓層起點/錨點 [{btn_name}] (信心度: {conf:.4f})，維護地下城探索狀態。")
                    
                else:
                    logging.info(f"👉 偵測到探險事件 [{btn_name}]，信心度: {conf:.4f}，點擊處理。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                self.no_explore_match_count = 0
                return # 成功處理一個優先級最高的事項後即結束該步，等待下一次截圖

        # 🛡️ 後置驗證保險：若標記為已領取祝福，但在等待超過 3.5 秒後畫面上仍未出現下樓按鈕 (gungeon_godown.png)

        if getattr(self.machine, "bless_received_this_floor", False):
            last_bless_time = getattr(self.machine, "last_bless_claim_time", 0.0)
            if time.time() - last_bless_time > 3.5:
                has_godown = False
                for godown_btn in ["dungeons/gungeon_godown.png", "dungeons/gungeon_godown_confirm.png"]:
                    if os.path.exists(os.path.join("templates", godown_btn)):
                        pos_g, _ = self.matcher.match(screen_img, godown_btn, threshold=0.75, quiet=True)
                        if pos_g:
                            has_godown = True
                            break
                if not has_godown:
                    logging.warning("⚠️ [後置防衛] 已標記領取祝福超過 3.5 秒，但畫面上始終未出現下樓按鈕 (gungeon_godown.png)，判定先前領取未成功，自動重置標記以供重新點擊領取！")
                    self.machine.bless_received_this_floor = False


        # 防卡死救援：若連續多幀沒有比對到任何地下城探險事件，檢查是否根本已經回到普通關卡/大廳/城鎮介面

        self.no_explore_match_count = getattr(self, "no_explore_match_count", 0) + 1
        if self.no_explore_match_count >= 6:
            self.no_explore_match_count = 0
            for fallback_btn in ["stages/start.png", "common/select_stage.png", "goback_town.png", "common/door.png"]:
                if os.path.exists(os.path.join("templates", fallback_btn)):
                    pos_fb, conf_fb = self.matcher.match(screen_img, fallback_btn, threshold=0.8)
                    if pos_fb:
                        logging.warning(f"⚠️ 地下城探索中未匹配到事件，但偵測到大廳/關卡介面 [{fallback_btn}] (信心度: {conf_fb:.4f})，判定已非地下城狀態，自動轉移至 NAVIGATING。")
                        self.machine.is_in_dungeon = False
                        next_state = self.machine.STATE_COLLECT_ONLY if self.machine.is_in_collect_only_mode() else self.machine.STATE_NAVIGATING
                        self.machine.transition_to(next_state)
                        return

        logging.info("⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...")

    def _run_treasure_subflow(self, rect) -> bool:
        logging.info("📦 [子流程] 開始執行「開啟寶箱」子流程...")
        start_time = time.time()
        timeout = 10.0  # 最多執行 10 秒
        
        treasure_clicked = False
        confirm_clicked = False
        last_click_time = start_time
        
        while time.time() - start_time < timeout:
            screen_img = self.machine.capturer.capture(rect)
            if screen_img is None:
                time.sleep(0.2)
                continue
                
            if not treasure_clicked:
                pos, conf = self.matcher.match(screen_img, "dungeons/Get_tresure.png", threshold=0.70)
                if pos:
                    logging.info(f"📦 [子流程] 偵測到獲得寶物按鈕 'dungeons/Get_tresure.png'，相似度: {conf:.4f}，進行點擊。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    treasure_clicked = True
                    last_click_time = time.time()
                    time.sleep(1.0)
                    continue
            elif not confirm_clicked:
                confirm_template = "dungeons/Get_tresure_comfirm.png"
                pos_c, conf_c = self.matcher.match(screen_img, confirm_template, threshold=0.70)
                if pos_c:
                    logging.info(
                        "📦 [子流程] 偵測到獲得寶物確認按鈕 '%s'，"
                        "相似度: %.4f，開始閉環點擊直到按鈕消失。",
                        confirm_template,
                        conf_c,
                    )
                    remaining_timeout = max(
                        0.1,
                        timeout - (time.time() - start_time),
                    )
                    confirm_clicked = self.click_and_wait_until_gone(
                        confirm_template,
                        rect["left"] + pos_c[0],
                        rect["top"] + pos_c[1],
                        rect,
                        timeout=remaining_timeout,
                        threshold=0.70,
                        check_interval=0.25,
                        post_delay=0.3,
                        retry_interval=0.75,
                    )
                    last_click_time = time.time()
                    if not confirm_clicked:
                        logging.warning(
                            "📦 [子流程] 獲得寶物確認按鈕在時限內未消失，"
                            "保留本層寶箱重試資格。"
                        )
                        return False
                    continue
                    
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.75)
                if pos_quit:
                    logging.info(f"📦 [子流程] 未看到寶物確認但直接偵測到退出按鈕 'common/quit.png'，相似度: {conf_quit:.4f}，進行點擊並退出。")
                    self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                    time.sleep(0.3)
                    return self._wait_for_treasure_terminal(rect, timeout)
            else:
                pos, conf = self.matcher.match(screen_img, "common/quit.png", threshold=0.75)
                if pos:
                    logging.info(f"📦 [子流程] 偵測到退出按鈕 'common/quit.png'，相似度: {conf:.4f}，進行點擊並結束寶箱子流程。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.3)
                    return self._wait_for_treasure_terminal(rect, timeout)
                    
            if time.time() - last_click_time > 2.0:
                has_any = False
                for btn, thresh in [("dungeons/Get_tresure.png", 0.70), ("dungeons/Get_tresure_comfirm.png", 0.70), ("common/quit.png", 0.75)]:
                    if os.path.exists(os.path.join("templates", btn)):
                        pos, _ = self.matcher.match(screen_img, btn, threshold=thresh)
                        if pos:
                            has_any = True
                            break
                if not has_any:
                    terminal = self._match_treasure_terminal(screen_img)
                    if terminal is not None:
                        anchor, confidence = terminal
                        logging.info(
                            "[Treasure subflow] Completion verified by [%s] "
                            "(confidence: %.4f).",
                            anchor,
                            confidence,
                        )
                        return True
                    logging.info(
                        "📦 [子流程] 寶箱按鈕已消失，"
                        "正在等待下樓或通關畫面作為完成確認。"
                    )
                    last_click_time = time.time()
                    time.sleep(0.3)
                    continue

            time.sleep(0.3)
            
        logging.warning("📦 [子流程] 開啟寶箱子流程超時結束。")

        return False

    def _wait_for_treasure_terminal(self, rect, timeout) -> bool:
        terminal_wait_start = time.time()
        while time.time() - terminal_wait_start < timeout:
            screen_img = self.machine.capturer.capture(rect)
            if screen_img is None:
                time.sleep(0.2)
                continue

            terminal = self._match_treasure_terminal(screen_img)
            if terminal is not None:
                anchor, confidence = terminal
                logging.info(
                    "[Treasure subflow] Completion verified by [%s] "
                    "(confidence: %.4f).",
                    anchor,
                    confidence,
                )
                return True
            time.sleep(0.3)

        logging.warning(
            "[Treasure subflow] Close was clicked, but no floor completion "
            "anchor appeared before timeout."
        )
        return False

    def _match_treasure_terminal(self, screen_img):
        """Return the terminal anchor visible after a treasure interaction."""
        for anchor in self.TREASURE_TERMINAL_ANCHORS:
            pos, confidence = self.matcher.match(
                screen_img,
                anchor,
                threshold=self.TREASURE_TERMINAL_THRESHOLD,
            )
            if pos:
                return anchor, confidence
        return None

    def _run_bless_subflow(self, rect) -> bool:
        """
        [子流程] 領取祝福 (dungeon bless) 階段式狀態機。
        回傳 True 代表祝福已成功選擇並領取完畢；False 代表失敗/超時關閉。
        """
        logging.info("🧭 [子流程] 開始執行「領取祝福」階段式子流程...")
        start_time = time.time()
        timeout = 15.0  # 最多執行 15 秒

        phase = "PHASE_SELECT_CARD"  # PHASE_SELECT_CARD -> PHASE_CONFIRM -> PHASE_EXIT
        bless_mode = self.machine.config.get("bless_mode", "combat")
        bless_templates = {
            "combat": "dungeons/bless_combat.png",
            "life": "dungeons/bless_life.png",
            "exp": "dungeons/bless_exp.png"
        }
        target_tpl = bless_templates.get(bless_mode, "dungeons/bless_combat.png")
        tpl_path = os.path.join(self.matcher.templates_dir, target_tpl)

        select_click_time = 0.0
        bless_success = False

        while time.time() - start_time < timeout:
            screen_img = self.machine.capturer.capture(rect)
            if screen_img is None:
                time.sleep(0.2)
                continue

            if phase == "PHASE_SELECT_CARD":
                # 0. 優先檢查是否已領取 (若存在 already_get 標籤則直接完成並退出)
                for already_tpl in ["dungeons/already_get.png", "already_get.png"]:
                    if os.path.exists(os.path.join(self.matcher.templates_dir, already_tpl)):
                        pos_already, conf_already = self.matcher.match(screen_img, already_tpl, threshold=0.75, quiet=True)
                        if pos_already:
                            logging.info(f"✨ [子流程-選卡] 偵測到祝福已領取標籤 [{already_tpl}] ({conf_already:.4f})，判定該層祝福早已領過，切換至 PHASE_EXIT 關閉視窗。")
                            bless_success = True
                            phase = "PHASE_EXIT"
                            break
                if phase == "PHASE_EXIT":
                    continue

                # 1. 嘗試尋找偏好祝福卡片與 choice_bless.png
                pos_tpl = None
                if os.path.exists(tpl_path):
                    pos_tpl, conf_tpl = self.matcher.match(screen_img, target_tpl, threshold=0.70, quiet=True)

                pos_choice = None
                actual_x, actual_y = 0, 0

                if pos_tpl:
                    bx = pos_tpl[0]
                    choice_tpl = self.matcher._load_template("dungeons/choice_bless.png")
                    choice_w = choice_tpl.shape[1] if isinstance(choice_tpl, np.ndarray) else 391

                    crop_w = max(450, choice_w + 60)
                    half_w = crop_w // 2

                    screen_w = screen_img.shape[1]
                    x_min = max(0, bx - half_w)
                    x_max = min(screen_w, bx + half_w)

                    cropped_img = screen_img[:, int(x_min):int(x_max)]
                    pos_c, conf_c = self.matcher.match(cropped_img, "dungeons/choice_bless.png", threshold=0.70, quiet=True)
                    if pos_c:
                        pos_choice = pos_c
                        actual_x = rect["left"] + pos_c[0] + int(x_min)
                        actual_y = rect["top"] + pos_c[1]
                        logging.info(f"🧭 [子流程-選卡] 精確對齊！找到目標祝福 [{target_tpl}] ({conf_tpl:.4f}) ➔ 點擊選擇按鈕 ({conf_c:.4f}) 座標: ({actual_x}, {actual_y})")

                # Fallback: 若 1.5 秒內無目標祝福或無模板，選擇畫面上第一個 choice_bless.png
                if not pos_choice and (time.time() - start_time > 1.5 or not os.path.exists(tpl_path)):
                    pos_fallback, conf_fb = self.matcher.match(screen_img, "dungeons/choice_bless.png", threshold=0.70, quiet=True)
                    if pos_fallback:
                        pos_choice = pos_fallback
                        actual_x = rect["left"] + pos_fallback[0]
                        actual_y = rect["top"] + pos_fallback[1]
                        logging.info(f"🧭 [子流程-選卡-Fallback] 點擊畫面第一個選擇按鈕 ({conf_fb:.4f}) 座標: ({actual_x}, {actual_y})")

                if pos_choice:
                    self.mouse.click(actual_x, actual_y)
                    select_click_time = time.time()
                    phase = "PHASE_CONFIRM"
                    time.sleep(0.5)
                    continue

            elif phase == "PHASE_CONFIRM":
                # 2. 確定領取階段：搜尋 common/confirm.png 或 common/ok.png
                pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.75, quiet=True)
                pos_conf, conf_c = self.matcher.match(screen_img, "common/confirm.png", threshold=0.75, quiet=True)

                target_ok = pos_ok or pos_conf
                ok_name = "common/ok.png" if pos_ok else "common/confirm.png"
                ok_conf = conf_ok if pos_ok else conf_c

                if target_ok:
                    ok_x = rect["left"] + target_ok[0]
                    ok_y = rect["top"] + target_ok[1]
                    logging.info(f"🧭 [子流程-確定領取] 偵測到確定按鈕 [{ok_name}] ({ok_conf:.4f})，進行點擊 ({ok_x}, {ok_y})。")
                    self.mouse.click(ok_x, ok_y)
                    bless_success = True
                    phase = "PHASE_EXIT"
                    time.sleep(0.5)
                    continue

                # 若點擊選擇按鈕已超過 1.2 秒，且畫面上選擇按鈕已消失，亦推進至 PHASE_EXIT
                pos_choice_check, _ = self.matcher.match(screen_img, "dungeons/choice_bless.png", threshold=0.70, quiet=True)
                if not pos_choice_check and (time.time() - select_click_time > 1.2):
                    logging.info("🧭 [子流程-確定領取] 選擇按鈕已點擊並消失，判定祝福選取已成立，切換至 PHASE_EXIT。")
                    bless_success = True
                    phase = "PHASE_EXIT"
                    continue

                # 若點擊選擇卡片超過 3.0 秒無回應且 choice_bless 仍存在，退回 PHASE_SELECT_CARD 重新嘗試
                if time.time() - select_click_time > 3.0:
                    logging.warning("⚠️ [子流程-確定領取] 點擊選擇按鈕無回應，重置退回 PHASE_SELECT_CARD 重新選擇...")
                    phase = "PHASE_SELECT_CARD"
                    time.sleep(0.3)
                    continue

            elif phase == "PHASE_EXIT":
                # 3. 退出與關閉彈窗階段：搜尋 common/quit.png 或等視窗關閉
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.75, quiet=True)
                if pos_quit:
                    quit_x = rect["left"] + pos_quit[0]
                    quit_y = rect["top"] + pos_quit[1]
                    logging.info(f"🧭 [子流程-退出] 偵測到退出按鈕 [common/quit.png] ({conf_quit:.4f})，點擊關閉視窗。")
                    self.mouse.click(quit_x, quit_y)
                    time.sleep(0.5)
                    return True
                else:
                    # 退出按鈕已消失，說明彈窗已完全關閉！
                    logging.info("🎉 [子流程] 祝福視窗已成功關閉，領取祝福流程完全成功！")
                    return True

            time.sleep(0.1)

        logging.warning(f"⚠️ [子流程] 領取祝福流程達到 timeout ({timeout}s)，完成狀態: {bless_success}")
        return bless_success


    def _run_skill_subflow(self, rect):
        logging.info("🧭 [子流程] 開始執行「技能選擇」子流程...")
        start_time = time.time()
        timeout = 10.0  # 最多執行 10 秒
        
        choose_clicked = False
        confirm_clicked = False
        last_click_time = 0.0
        
        while time.time() - start_time < timeout:
            screen_img = self.machine.capturer.capture(rect)
            if screen_img is None:
                time.sleep(0.2)
                continue
                
            if not choose_clicked:
                pos, conf = self.matcher.match(screen_img, "dungeons/choose.png", threshold=0.70)
                if pos:
                    logging.info(f"🧭 [子流程] 偵測到選擇技能按鈕 'dungeons/choose.png'，相似度: {conf:.4f}，進行點擊。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    choose_clicked = True
                    last_click_time = time.time()
                    time.sleep(1.0)  # 等待動畫
                    continue
            elif not confirm_clicked:
                pos_c, conf_c = self.matcher.match(screen_img, "common/confirm.png", threshold=0.80)
                if pos_c:
                    logging.info(f"🧭 [子流程] 偵測到確認按鈕 'common/confirm.png'，相似度: {conf_c:.4f}，進行點擊。")
                    self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                    confirm_clicked = True
                    last_click_time = time.time()
                    time.sleep(1.0)
                    continue
                    
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.75)
                if pos_quit:
                    logging.info(f"🧭 [子流程] 未看到確認但直接偵測到退出按鈕 'common/quit.png'，相似度: {conf_quit:.4f}，進行點擊並退出。")
                    self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                    time.sleep(0.3)
                    return
            else:
                pos, conf = self.matcher.match(screen_img, "common/quit.png", threshold=0.75)
                if pos:
                    logging.info(f"🧭 [子流程] 偵測到退出按鈕 'common/quit.png'，相似度: {conf:.4f}，進行點擊並結束技能選擇子流程。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.3)
                    return
                    
            if time.time() - last_click_time > 2.0:
                has_any = False
                for btn, thresh in [("dungeons/choose.png", 0.70), ("common/confirm.png", 0.80), ("common/quit.png", 0.75)]:
                    if os.path.exists(os.path.join("templates", btn)):
                        pos, _ = self.matcher.match(screen_img, btn, threshold=thresh)
                        if pos:
                            has_any = True
                            break
                if not has_any:
                    logging.info("🧭 [子流程] 畫面已無技能選擇關聯按鈕且無新動作，提前結束子流程。")
                    return
                    
            time.sleep(0.3)
            
        logging.warning("🧭 [子流程] 技能選擇子流程超時結束。")

    def _reset_floor_memory_transition(self):
        logging.info("🧭 偵測到新樓層探索事件，提前結束下樓過渡期並重設探索記憶。")
        self.machine.chest_opened_this_floor = False
        self.machine.skill_selected_this_floor = False
        self.machine.bless_received_this_floor = False
        self.machine.dungeon_floor_transitioning = False
        self.machine.last_godown_click_time = None
