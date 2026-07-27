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
                pos, conf = self.matcher.match(screen_img, feat, threshold=thresh, quiet=True)
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

        # 檢查是否處於首領領主討伐 (lord_boss) 模式或城鎮子流程
        is_lord_boss_mode = (
            self.machine.config.get("type") == "lord_boss" or 
            getattr(self.machine, "current_town_subflow", None) == "lord_boss"
        )
        if is_lord_boss_mode:
            dm = getattr(self.machine, "daily_manager", None)
            if dm and dm.has_available_lord_boss():
                logging.info("👑 大廳：偵測到首領討伐模式且尚有可用 Boss，切換至 LORD_BOSS 繼續討伐...")
                self.machine.transition_to(self.machine.STATE_LORD_BOSS)
                return
            else:
                logging.info("🎉 大廳：首領討伐今日已全數完成或均在冷卻中，彈出下一城鎮任務...")
                if dm and hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("lord_boss")
                self.machine.pop_and_next_town_subflow()
                return

        # 如果需要領鑽石或體力，優先轉移至 NAVIGATING 狀態進行領取 (在非 dev_subflows 單獨測試時)
        if not getattr(self.machine, "dev_subflows", None):
            if self.machine.need_diamond_collection or (self.machine.enable_bread and self.machine.need_bread_collection):
                logging.info("💎/🍞 大廳：偵測到需要領取鑽石或體力，優先轉移至 NAVIGATING 狀態。")
                self.machine.transition_to(self.machine.STATE_NAVIGATING)
                return

        lobby_btn = self.machine.config.get("lobby_start_btn", "stages/start.png")
        pos, conf = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        if pos:
            logging.info(f"👉 偵測到大廳開始按鈕 [{lobby_btn}] (信心度: {conf:.4f})，進行點擊。")
            self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
            self.machine.last_lobby_start_click_time = time.time()
            self.machine.run_count += 1
            logging.info(f"🚀 點擊大廳開始按鈕，進入加載等待... (累計啟動次數: {self.machine.run_count})")
            self.machine.transition_to(self.machine.STATE_LOADING)
            self.machine.dungeon_defeat_count = 0
            time.sleep(0.3)
        else:
            logging.info("🧭 大廳：未偵測到開始按鈕，判定處於城鎮外圍，轉移至對應模式。")
            next_state = self.machine.STATE_COLLECT_ONLY if self.machine.is_in_collect_only_mode() else self.machine.STATE_NAVIGATING
            self.machine.transition_to(next_state)
