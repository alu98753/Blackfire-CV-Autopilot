import time
import os
import logging
from states.handlers.base import BaseStateHandler

class BattleHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        戰鬥狀態處理：啟用自動戰鬥與監控戰鬥結算。
        """
        # 0. 檢查戰鬥結算是否因為背包已滿而彈出提示 (common/bagfull_quit.png)
        if os.path.exists(os.path.join("templates", "common/bagfull_quit.png")):
            pos_bag, conf_bag = self.matcher.match(screen_img, "common/bagfull_quit.png", threshold=0.8)
            if pos_bag:
                logging.warning(f"🧭 戰鬥中/結算時偵測到「背包已滿」！出現 'common/bagfull_quit.png'，點擊退出結算。")
                self.mouse.click(rect["left"] + pos_bag[0], rect["top"] + pos_bag[1])
                self.machine.need_bag_cleaning = True
                time.sleep(0.5)
                
                if self.machine.config["type"] == "dungeon":
                    self.machine.transition_to(self.machine.STATE_DUNGEON_EXPLORING)
                else:
                    self.machine.transition_to(self.machine.STATE_RESULT)
                return

        # A. 檢查是否需要啟動自動戰鬥 (common/auto.png)
        if os.path.exists(os.path.join("templates", "common/auto.png")) and (time.time() - self.machine.last_auto_click_time > 3.0):
            pos_auto, conf_auto = self.matcher.match(screen_img, "common/auto.png", threshold=0.7)
            logging.info(f"🔍 檢查自動戰鬥按鈕... 最大相似度: {conf_auto:.4f} (閥值: 0.7)")
            if pos_auto:
                logging.info(f"👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！")
                self.mouse.click(rect["left"] + pos_auto[0], rect["top"] + pos_auto[1])
                self.machine.last_auto_click_time = time.time()
                time.sleep(0.3)

        # B. 監控戰鬥結算
        if self.machine.config["type"] == "stage":
            # 關卡模式：檢查 retry.png 與所有 continue*.png
            found_result_trigger = False
            for btn in self.machine.config["result_buttons"]:
                pos, _ = self.matcher.match(screen_img, btn, threshold=0.8)
                if pos:
                    logging.info(f"🏆 偵測到結算按鈕 [{btn}]，戰鬥結束！")
                    found_result_trigger = True
                    break
            if found_result_trigger:
                self.machine.transition_to(self.machine.STATE_RESULT)
            else:
                self.log_battle_duration()
                time.sleep(0.5)
                
        elif self.machine.config["type"] == "dungeon":
            # 地下城模式：檢查 dungeon_battle_results 結算按鈕 (排除 continue3.png)
            best_match_pos = None
            best_match_conf = 0.8
            best_match_temp = None
            
            for btn in self.machine.config["dungeon_battle_results"]:
                pos, conf = self.matcher.match(screen_img, btn, threshold=best_match_conf)
                if pos and conf > best_match_conf:
                    best_match_conf = conf
                    best_match_pos = pos
                    best_match_temp = btn
                    
            if best_match_pos:
                logging.info(f"🏆 戰鬥結束！點擊相似度最高的地下城結算按鈕 [{best_match_temp}]，信心度: {best_match_conf:.4f}")
                self.mouse.click(rect["left"] + best_match_pos[0], rect["top"] + best_match_pos[1])
                # 點擊完結算後，會回到地下城層與層之間，轉移回探索狀態
                self.machine.transition_to(self.machine.STATE_DUNGEON_EXPLORING)
                time.sleep(0.6)
            else:
                self.log_battle_duration()
                time.sleep(0.5)

    def log_battle_duration(self):
        if self.machine.battle_start_time:
            duration = time.time() - self.machine.battle_start_time
            logging.info(f"⚔️ 戰鬥進行中... 已持續 {int(duration)} 秒")
        else:
            logging.info(f"⚔️ 戰鬥進行中...")
