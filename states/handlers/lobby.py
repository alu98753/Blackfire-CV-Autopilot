import time
import logging
from states.handlers.base import BaseStateHandler
import os

class LobbyHandler(BaseStateHandler):
    def __init__(self, machine):
        super().__init__(machine)
        self.start_clicked_time = None
        self.start_retry_interval = 1.0  # 補點間隔 1.0 秒
        self.start_max_timeout = 5.0     # 重試超時安全閥 5.0 秒

    def reset_state(self):
        self.start_clicked_time = None

    def handle(self, screen_img, rect):
        """
        普通關卡大廳狀態下的開始按鈕點擊處理（非阻塞 Tick 狀態機）。
        """
        # 0. 優先判定是否已經進入真實戰鬥中（出現 auto 按鈕或戰鬥特徵，代表點擊後成功載入）
        for feat in ["common/auto.png", "battle/battle_features_1.png", "battle/battle_features_2.png"]:
            if os.path.exists(os.path.join("templates", feat)):
                thresh = 0.65 if feat == "common/auto.png" else 0.70
                pos, conf = self.matcher.match(screen_img, feat, threshold=thresh, quiet=True)
                if pos:
                    logging.info(f"⚔️ 偵測到戰鬥已真正開始（出現特徵 [{feat}]，相似度: {conf:.4f}），進入戰鬥狀態！")
                    self.reset_state()
                    self.machine.battle_start_time = time.time()
                    self.machine.transition_to(self.machine.STATE_BATTLE)
                    return

        # 0.1 全域最高優先防護：若畫面上出現歡迎/確認彈窗，優先點擊關閉以防止遮罩擋住開始按鈕
        for popup_btn in ["common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", popup_btn)):
                pos_popup, conf_popup = self.matcher.match(screen_img, popup_btn, threshold=0.90)
                if pos_popup:
                    logging.info(f"👉 [大廳全域防護] 偵測到可能遮擋的彈窗按鈕 [{popup_btn}] (相似度: {conf_popup:.4f})，優先點擊關閉...")
                    self.reset_state()
                    self.mouse.click(rect["left"] + pos_popup[0], rect["top"] + pos_popup[1])
                    time.sleep(0.5)
                    return

        # 前置模式與子流程分流
        if self._handle_preconditions(screen_img, rect):
            return

        # 開始按鈕非阻塞點擊與確認
        self._handle_start_button(screen_img, rect)

    def _handle_preconditions(self, screen_img, rect) -> bool:
        """處理背包、首領討伐、體力鑽石領取等大廳前置條件分流。"""
        # 如果是背包整理模式，優先轉移至 BAG_CLEANING 狀態
        if self.machine.config.get("type") == "bag_clean":
            logging.info("🎒 大廳：偵測到為背包整理模式，優先轉移至 BAG_CLEANING 狀態。")
            self.reset_state()
            self.machine.transition_to(self.machine.STATE_BAG_CLEANING)
            return True

        # 如果背包滿了，優先轉移至 BAG_CLEANING 狀態進行清理，暫不開啟戰鬥
        if self.machine.need_bag_cleaning:
            logging.info("🎒 大廳：偵測到需要清理背包，優先轉移至 BAG_CLEANING 狀態。")
            self.reset_state()
            self.machine.transition_to(self.machine.STATE_BAG_CLEANING)
            return True

        # 檢查是否處於首領領主討伐 (lord_boss) 模式或城鎮子流程
        is_lord_boss_mode = (
            self.machine.config.get("type") == "lord_boss" or 
            getattr(self.machine, "current_town_subflow", None) == "lord_boss"
        )
        if is_lord_boss_mode:
            dm = getattr(self.machine, "daily_manager", None)
            if dm and self.machine.has_available_selected_lord_boss():
                logging.info("👑 大廳：偵測到首領討伐模式且尚有可用 Boss，切換至 LORD_BOSS 繼續討伐...")
                self.reset_state()
                self.machine.transition_to(self.machine.STATE_LORD_BOSS)
                return True
            else:
                logging.info("🎉 大廳：首領討伐今日已全數完成或均在冷卻中，彈出下一城鎮任務...")
                if dm and hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("lord_boss")
                self.reset_state()
                self.machine.pop_and_next_town_subflow()
                return True

        # 如果需要領鑽石或體力，優先轉移至 NAVIGATING 狀態進行領取 (在非 dev_subflows 單獨測試時)
        if not getattr(self.machine, "dev_subflows", None):
            if self.machine.need_diamond_collection or (self.machine.enable_bread and self.machine.need_bread_collection):
                logging.info("💎/🍞 大廳：偵測到需要領取鑽石或體力，優先轉移至 NAVIGATING 狀態。")
                self.reset_state()
                self.machine.transition_to(self.machine.STATE_NAVIGATING)
                return True

        # 若未啟用普通關卡打怪 (enable_stage_farming == False)，且目前非特定子流程或地下城戰鬥
        if not self.machine.config.get("enable_stage_farming", False) and not getattr(self.machine, "is_in_dungeon", False) and not is_lord_boss_mode:
            logging.info("💤 [大廳] 未啟用普通關卡打怪 (enable_stage_farming=False) ➔ 點擊返回城鎮轉入 COLLECT_ONLY 待機...")
            pos_back, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.75, quiet=True)
            if pos_back:
                self.mouse.click(rect["left"] + pos_back[0], rect["top"] + pos_back[1])
                time.sleep(0.5)
            self.reset_state()
            self.machine.transition_to(self.machine.STATE_COLLECT_ONLY)
            return True

        return False

    def _handle_start_button(self, screen_img, rect):
        """非阻塞式大廳開始按鈕點擊與消失確認邏輯 (Tick-driven verification)。"""
        lobby_btn = self.machine.config.get("lobby_start_btn", "stages/start.png")
        pos, conf = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        now = time.time()

        if pos:
            if self.start_clicked_time is None:
                # 首次點擊按鈕
                logging.info(f"👉 偵測到大廳開始按鈕 [{lobby_btn}] (信心度: {conf:.4f})，進行點擊...")
                self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                self.start_clicked_time = now
                self.notify_ui_progress()
                return
            else:
                # 已經點過但按鈕尚未消失
                elapsed = now - self.start_clicked_time
                if elapsed >= self.start_retry_interval:
                    logging.info(f"🔄 [自動補點] 開始按鈕在 {elapsed:.1f} 秒內未消失，重新發起點擊...")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.start_clicked_time = now
                    self.notify_ui_progress()
                elif elapsed > self.start_max_timeout:
                    logging.warning(f"⚠️ 開始按鈕點擊超過 {self.start_max_timeout} 秒仍未消失，重置點擊狀態供後續重試。")
                    self.reset_state()
                return
        else:
            if self.start_clicked_time is not None:
                # ✅ 關鍵：先前點擊過，且現在按鈕已確認消失！
                logging.info("🚀 大廳開始按鈕已成功消失 (UI 已響應)，轉移至 LOADING 狀態！")
                self.reset_state()
                self.machine.last_lobby_start_click_time = now
                self.machine.run_count += 1
                self.machine.dungeon_defeat_count = 0
                self.machine.transition_to(self.machine.STATE_LOADING)
                return
            else:
                # 原本就不在大廳（例如城鎮外圍）
                logging.info("🧭 大廳：未偵測到開始按鈕，判定處於城鎮外圍，轉移至對應模式。")
                next_state = self.machine.STATE_COLLECT_ONLY if self.machine.is_in_collect_only_mode() else self.machine.STATE_NAVIGATING
                self.machine.transition_to(next_state)
