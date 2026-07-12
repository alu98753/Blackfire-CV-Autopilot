import time
import logging
from states.handlers.base import BaseStateHandler
import os

class LobbyHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        普通關卡大廳狀態下的開始按鈕點擊處理。
        """
        # 0. 優先判定是否已經進入真實戰鬥中（出現 auto 按鈕或戰鬥特徵，代表點擊後成功載入）
        for feat in ["common/auto.png", "battle/battle_features_1.png", "battle/battle_features_2.png"]:
            if os.path.exists(os.path.join("templates", feat)):
                thresh = 0.65 if feat == "common/auto.png" else 0.70
                pos, conf = self.matcher.match(screen_img, feat, threshold=thresh)
                if pos:
                    logging.info(f"⚔️ 偵測到戰鬥已真正開始（出現特徵 [{feat}]，相似度: {conf:.4f}），進入戰鬥狀態！")
                    self.machine.battle_start_time = time.time()
                    self.machine.transition_to(self.machine.STATE_BATTLE)
                    return

        # 如果是背包整理模式，優先轉移至 BAG_CLEANING 狀態
        if self.machine.config["type"] == "bag_clean":
            logging.info("🎒 大廳：偵測到為背包整理模式，優先轉移至 BAG_CLEANING 狀態。")
            self.machine.transition_to(self.machine.STATE_BAG_CLEANING)
            return

        # 如果背包滿了，優先轉移至 BAG_CLEANING 狀態進行清理，暫不開啟戰鬥
        if self.machine.need_bag_cleaning:
            logging.info("🎒 大廳：偵測到需要清理背包，優先轉移至 BAG_CLEANING 狀態。")
            self.machine.transition_to(self.machine.STATE_BAG_CLEANING)
            return

        # 如果需要領鑽石或體力，優先轉移至 NAVIGATING 狀態進行領取
        if self.machine.need_diamond_collection or (self.machine.enable_bread and self.machine.need_bread_collection):
            logging.info("💎/🍞 大廳：偵測到需要領取鑽石或體力，優先轉移至 NAVIGATING 狀態。")
            self.machine.transition_to(self.machine.STATE_NAVIGATING)
            return

        lobby_btn = self.machine.config["lobby_start_btn"]
        pos, conf = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        if pos:
            now = time.time()
            if now - getattr(self.machine, "last_lobby_start_click_time", 0.0) < 4.0:
                logging.info("⌛ 剛點擊過開始按鈕，正在等待戰鬥載入...")
                return
            logging.info(f"👉 偵測到大廳開始按鈕 [{lobby_btn}] (信心度: {conf:.4f})，進行點擊。")
            self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
            self.machine.last_lobby_start_click_time = now
            self.machine.run_count += 1
            logging.info(f"🚀 點擊大廳開始按鈕，進入加載等待... (累計啟動次數: {self.machine.run_count})")
            time.sleep(0.3)
        else:
            logging.info("🧭 大廳：未偵測到開始按鈕，判定處於城鎮外圍，轉移至 NAVIGATING 進行尋路跳轉。")
            self.machine.transition_to(self.machine.STATE_NAVIGATING)
