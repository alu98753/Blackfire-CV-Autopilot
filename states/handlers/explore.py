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
        if self.machine.last_godown_click_time and (time.time() - self.machine.last_godown_click_time > 6.0):
            logging.info("⏳ 下樓冷卻結束，已進入地下城新樓層，重設探索記憶。")
            self.machine.chest_opened_this_floor = False
            self.machine.skill_selected_this_floor = False
            self.machine.bless_received_this_floor = False
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
                
            pos, conf = self.matcher.match(screen_img, btn_name, threshold=0.8)
            if pos:
                if btn_name == "dungeons/dungeons_complete.png":
                    logging.info(f"🎉 偵測到【地下城通關結束】({btn_name})，信心度: {conf:.4f}，點擊退出。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.run_count += 1
                    logging.info(f"📊 已完成第 {self.machine.run_count} 次地下城通關！")
                    # 通關後回到最外層大廳，轉移至尋路導航狀態重新進副本
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    time.sleep(2.0)
                    
                elif btn_name == "common/bagfull_quit.png":
                    logging.warning(f"🧭 偵測到【背包已滿】({btn_name})，信心度: {conf:.4f}，點擊退出彈窗並標記清理背包。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.need_bag_cleaning = True
                    time.sleep(1.2)
                    
                elif btn_name == "dungeons/Get_tresure.png" or btn_name == "dungeons/Get_tresure_comfirm.png":
                    logging.info(f"👉 偵測到獲得寶物 [{btn_name}]，信心度: {conf:.4f}，點擊並標記本層寶箱已開。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.chest_opened_this_floor = True
                    time.sleep(1.0)
                    
                elif btn_name == "dungeons/choose.png":
                    logging.info(f"👉 偵測到選擇技能 [{btn_name}]，信心度: {conf:.4f}，點擊並標記本層技能已選。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.skill_selected_this_floor = True
                    time.sleep(1.0)
                    
                elif btn_name == "dungeons/choice_bless.png":
                    logging.info(f"👉 偵測到選擇祝福 [{btn_name}]，信心度: {conf:.4f}，點擊並標記本層祝福已領。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.bless_received_this_floor = True
                    time.sleep(1.0)

                elif btn_name == "dungeons/Treasure.png":
                    logging.info(f"👉 偵測到寶箱地圖格 [{btn_name}]，信心度: {conf:.4f}，點擊並標記本層寶箱已開。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.chest_opened_this_floor = True
                    time.sleep(1.2)
                    
                elif btn_name == "dungeons/skill_event.png":
                    logging.info(f"👉 偵測到技能事件圖示 [{btn_name}]，信心度: {conf:.4f}，點擊並標記本層技能已選。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.skill_selected_this_floor = True
                    time.sleep(1.2)
                    
                elif btn_name == "dungeons/dungeon_bless.png":
                    logging.info(f"👉 偵測到接受祝福圖示 [{btn_name}]，信心度: {conf:.4f}，點擊並標記本層祝福已領。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.machine.bless_received_this_floor = True
                    time.sleep(1.2)
                    
                elif btn_name in ["dungeons/gungeon_godown.png", "dungeons/gungeon_godown_confirm.png"]:
                    logging.info(f"🧭 偵測到下樓按鈕 [{btn_name}]，信心度: {conf:.4f}，點擊下樓並開始本層記憶冷卻。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    # 僅設定下樓點擊時間，由冷卻時間屆滿後在 handle() 起始處重設，防止切換期重複點擊舊圖示
                    self.machine.last_godown_click_time = time.time()
                    time.sleep(1.5)
                    
                elif btn_name == "dungeons/dungeon_fight.png":
                    logging.info(f"⚔️ 偵測到【戰鬥房入口】({btn_name})，信心度: {conf:.4f}，點擊進入。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    # 注意：此處不轉移至 STATE_BATTLE，因為進入後需要先選擇祝福 (bless)。
                    # 我們將等待畫面出現 auto.png 後，由本方法最上方的判定自動轉入戰鬥狀態。
                    time.sleep(1.0)
                    
                else:
                    logging.info(f"👉 偵測到探險事件 [{btn_name}]，信心度: {conf:.4f}，點擊處理。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.8) # 點擊後等待短暫動畫
                    
                return # 成功處理一個優先級最高的事項後即結束該步，等待下一次截圖
                
        logging.info("⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...")
        time.sleep(0.5)
