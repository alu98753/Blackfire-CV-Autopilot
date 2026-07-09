import os
import time
import logging
from states.handlers.base import BaseStateHandler

class ExploreHandler(BaseStateHandler):
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
                self.machine.battle_start_time = time.time()
                self.machine.transition_to(self.machine.STATE_BATTLE)
                return

        # 3. 依優先級處理探險事件
        for btn_name in self.machine.config["explore_priorities"]:
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
                    
                    # 動態設定當前地下城的冷卻時間（第一關沒有冷卻，第二關 5 分鐘，第三關 15 分鐘，第四關 25 分鐘）
                    if hasattr(self.machine, "current_dungeon_index") and self.machine.current_dungeon_index is not None:
                        cooldown_map = {
                            0: 0.0,
                            1: 5.0 * 60.0,
                            2: 15.0 * 60.0,
                            3: 20.0 * 60.0
                        }
                        cd_seconds = cooldown_map.get(self.machine.current_dungeon_index, 900.0)
                        self.machine.dungeon_cooldowns[self.machine.current_dungeon_index] = time.time() + cd_seconds
                        logging.info(f"⏳ 貪婪地下城：設定第 {self.machine.current_dungeon_index + 1} 個地下城進入 {int(cd_seconds / 60)} 分鐘冷卻期。")
                        
                    # 通關後回到最外層大廳，轉移至尋路導航狀態重新進副本
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    time.sleep(0.2)
                    

                elif btn_name == "dungeons/Treasure.png":
                    if self.machine.dungeon_floor_transitioning:
                        self._reset_floor_memory_transition()
                    logging.info(f"👉 偵測到寶箱地圖格 [{btn_name}]，信心度: {conf:.4f}，進行點擊並啟動「開啟寶箱」子流程。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.chest_opened_this_floor = True
                    time.sleep(0.5)  # 等待寶箱開啟動畫開始
                    self._run_treasure_subflow(rect)
                    
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
                    self.machine.bless_received_this_floor = True
                    time.sleep(0.5)  # 等待祝福開啟動畫開始
                    self._run_bless_subflow(rect)
                    
                elif btn_name in ["dungeons/gungeon_godown.png", "dungeons/gungeon_godown_confirm.png"]:
                    logging.info(f"🧭 偵測到下樓按鈕 [{btn_name}]，信心度: {conf:.4f}，點擊下樓並開始本層記憶冷卻。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    # 設定下樓點擊時間與過渡狀態，由冷卻時間屆滿後或在新樓層檢測到事件時重設
                    self.machine.last_godown_click_time = time.time()
                    self.machine.dungeon_floor_transitioning = True
                    time.sleep(0.04)
                    
                elif btn_name == "dungeons/dungeon_fight.png":
                    logging.info(f"⚔️ 偵測到【戰鬥房入口】({btn_name})，信心度: {conf:.4f}，點擊進入。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    # 注意：此處不轉移至 STATE_BATTLE，因為進入後需要先選擇祝福 (bless)。
                    # 我們將等待畫面出現 auto.png 後，由本方法最上方的判定自動轉入戰鬥狀態。
                    time.sleep(0.03)
                    
                else:
                    logging.info(f"👉 偵測到探險事件 [{btn_name}]，信心度: {conf:.4f}，點擊處理。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.03) # 點擊後等待短暫動畫
                    
                return # 成功處理一個優先級最高的事項後即結束該步，等待下一次截圖
                
        logging.info("⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...")

    def _run_treasure_subflow(self, rect):
        logging.info("📦 [子流程] 開始執行「開啟寶箱」子流程...")
        start_time = time.time()
        timeout = 10.0  # 最多執行 10 秒
        
        treasure_clicked = False
        confirm_clicked = False
        last_click_time = 0.0
        
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
                pos_c, conf_c = self.matcher.match(screen_img, "dungeons/Get_tresure_comfirm.png", threshold=0.70)
                if pos_c:
                    logging.info(f"📦 [子流程] 偵測到獲得寶物確認按鈕 'dungeons/Get_tresure_comfirm.png'，相似度: {conf_c:.4f}，進行點擊。")
                    self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                    confirm_clicked = True
                    last_click_time = time.time()
                    time.sleep(1.0)
                    continue
                    
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.75)
                if pos_quit:
                    logging.info(f"📦 [子流程] 未看到寶物確認但直接偵測到退出按鈕 'common/quit.png'，相似度: {conf_quit:.4f}，進行點擊並退出。")
                    self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                    time.sleep(0.3)
                    return
            else:
                pos, conf = self.matcher.match(screen_img, "common/quit.png", threshold=0.75)
                if pos:
                    logging.info(f"📦 [子流程] 偵測到退出按鈕 'common/quit.png'，相似度: {conf:.4f}，進行點擊並結束寶箱子流程。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.3)
                    return
                    
            if time.time() - last_click_time > 2.0:
                has_any = False
                for btn, thresh in [("dungeons/Get_tresure.png", 0.70), ("dungeons/Get_tresure_comfirm.png", 0.70), ("common/quit.png", 0.75)]:
                    if os.path.exists(os.path.join("templates", btn)):
                        pos, _ = self.matcher.match(screen_img, btn, threshold=thresh)
                        if pos:
                            has_any = True
                            break
                if not has_any:
                    logging.info("📦 [子流程] 畫面已無寶箱關聯按鈕且無新動作，提前結束子流程。")
                    return
                    
            time.sleep(0.3)
            
        logging.warning("📦 [子流程] 開啟寶箱子流程超時結束。")

    def _run_bless_subflow(self, rect):
        logging.info("🧭 [子流程] 開始執行「領取祝福」子流程...")
        start_time = time.time()
        timeout = 10.0  # 最多執行 10 秒
        
        bless_clicked = False
        ok_clicked = False
        last_click_time = 0.0
        
        while time.time() - start_time < timeout:
            screen_img = self.machine.capturer.capture(rect)
            if screen_img is None:
                time.sleep(0.2)
                continue
                
            if not bless_clicked:
                pos, conf = self.matcher.match(screen_img, "dungeons/choice_bless.png", threshold=0.70)
                if pos:
                    logging.info(f"🧭 [子流程] 偵測到選擇祝福按鈕 'dungeons/choice_bless.png'，相似度: {conf:.4f}，進行點擊。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    bless_clicked = True
                    last_click_time = time.time()
                    time.sleep(1.0)  # 等待動畫
                    continue
            elif not ok_clicked:
                pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.80)
                if pos_ok:
                    logging.info(f"🧭 [子流程] 偵測到 OK 按鈕 'common/ok.png'，相似度: {conf_ok:.4f}，進行點擊。")
                    self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
                    ok_clicked = True
                    last_click_time = time.time()
                    time.sleep(1.0)
                    continue
                    
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.75)
                if pos_quit:
                    logging.info(f"🧭 [子流程] 未看到 OK 但直接偵測到退出按鈕 'common/quit.png'，相似度: {conf_quit:.4f}，進行點擊並退出。")
                    self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                    time.sleep(0.3)
                    return
            else:
                pos, conf = self.matcher.match(screen_img, "common/quit.png", threshold=0.75)
                if pos:
                    logging.info(f"🧭 [子流程] 偵測到退出按鈕 'common/quit.png'，相似度: {conf:.4f}，進行點擊並結束祝福子流程。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.3)
                    return
                    
            if time.time() - last_click_time > 2.0:
                has_any = False
                for btn, thresh in [("dungeons/choice_bless.png", 0.70), ("common/ok.png", 0.80), ("common/quit.png", 0.75)]:
                    if os.path.exists(os.path.join("templates", btn)):
                        pos, _ = self.matcher.match(screen_img, btn, threshold=thresh)
                        if pos:
                            has_any = True
                            break
                if not has_any:
                    logging.info("🧭 [子流程] 畫面已無祝福關聯按鈕且無新動作，提前結束子流程。")
                    return
                    
            time.sleep(0.3)
            
        logging.warning("🧭 [子流程] 領取祝福子流程超時結束。")

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
