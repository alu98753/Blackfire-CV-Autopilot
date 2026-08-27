import os
import time
import logging
from states.handlers.base import BaseStateHandler
from states.domains import get_domain_strategy

class DomainExploreHandler(BaseStateHandler):
    """
    🎯 領地/領域探索狀態處理器 (DomainExploreHandler)。
    負責領地主場景探索迴圈、背包已滿攔截、戰鬥觸發轉移、體力退避與特定領地策略委派。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.strategy = None
        self._init_strategy()

    def _init_strategy(self):
        domain_name = self.machine.config.get("domain") or self.machine.config.get("domain_name") or "golden_empire"
        self.strategy = get_domain_strategy(domain_name, self)

    def reset_state(self):
        """重置處理器內部狀態並重新裝載對應領地策略"""
        self._init_strategy()

    def handle(self, screen_img, rect):
        """
        領域探索主迴圈入口。
        """
        # 0. 確保當前策略與 config 保持一致
        domain_name = self.machine.config.get("domain") or self.machine.config.get("domain_name") or "golden_empire"
        if not self.strategy or getattr(self.strategy, "domain_name", None) != domain_name:
            self._init_strategy()

        # 1. 背包滿全域防護攔截
        if self._check_bag_full(screen_img, rect):
            return

        # 2. 優先檢查是否已經進入戰鬥畫面 (common/auto.png)
        if self._check_battle_entry(screen_img):
            return

        # 3. 檢查體力退避或無麵包狀態
        if self._check_stamina_retreat(screen_img, rect):
            return

        # 4. 委派特定領地策略處理專屬事件 (如黃金古國挖寶事件)
        if self.strategy.handle_custom_events(screen_img, rect):
            return

        # 5. 主場景點擊探索按鈕
        if self.strategy.handle_explore_click(screen_img, rect):
            time.sleep(0.1)
            return

        # 6. 檢查是否處於大廳或領地選擇畫面 (導航路徑特徵)
        nav_path = self.machine.config.get("navigation_path", [])
        for nav_btn in nav_path:
            if os.path.exists(os.path.join("templates", nav_btn)):
                pos, conf = self.matcher.match(screen_img, nav_btn, threshold=0.75, quiet=True)
                if pos:
                    logging.info(f"🧭 [領地探索] 偵測到尋路按鈕 [{nav_btn}] (相似度: {conf:.4f})，判定已在外部選單，轉移至 NAVIGATING 進入古國。")
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    return

        logging.debug("⌛ [領地探索] 等待主場景探索按鈕或事件加載中...")

    def _check_bag_full(self, screen_img, rect) -> bool:
        """檢查背包是否已滿"""
        # 1. 畫面上實際存在背包已滿彈窗 (backpack_full.png)
        if os.path.exists(os.path.join("templates", "backpack_full.png")):
            pos_bf, conf_bf = self.matcher.match(screen_img, "backpack_full.png", threshold=0.80)
            if pos_bf:
                logging.warning(f"🎒 [領地探索] 畫面上出現背包已滿彈窗 (信心度: {conf_bf:.4f})，轉移至 BACKPACK_FULL_SORTING。")
                self.machine.transition_to(self.machine.STATE_BACKPACK_FULL_SORTING)
                return True

        # 2. 若先前已標記 need_bag_cleaning == True (分選完成需回城清理)
        if self.machine.need_bag_cleaning:
            for exit_btn in ["domains/common/exit_to_lobby.png", "goback_town.png", "common/quit.png"]:
                if os.path.exists(os.path.join("templates", exit_btn)):
                    pos_exit, conf_exit = self.matcher.match(screen_img, exit_btn, threshold=0.75, quiet=True)
                    if pos_exit:
                        logging.info(f"🎒 [領地探索] 背包已滿需回城清理，偵測到退場按鈕 [{exit_btn}] (信心度: {conf_exit:.4f})，點擊退出領地...")
                        self.click_and_wait_until_gone(exit_btn, rect["left"] + pos_exit[0], rect["top"] + pos_exit[1], rect)
                        self.machine.transition_to(self.machine.STATE_NAVIGATING)
                        return True

            # 若畫面未找到 exit_to_lobby (可能已在領地選單)，轉移至 NAVIGATING
            logging.info("🎒 [領地探索] 需回城清理背包，轉移至 STATE_NAVIGATING 尋路回城。")
            self.machine.transition_to(self.machine.STATE_NAVIGATING)
            return True

        return False

    def _check_battle_entry(self, screen_img) -> bool:
        """檢查是否觸發戰鬥"""
        if os.path.exists(os.path.join("templates", "common/auto.png")):
            pos_auto, conf_auto = self.matcher.match(screen_img, "common/auto.png", threshold=0.70)
            if pos_auto:
                logging.info(f"⚔️ [領地探索] 偵測到戰鬥開始 (auto 按鈕信心度: {conf_auto:.4f})，重置單場戰敗次數並轉移至 STATE_BATTLE！")
                self.machine.defeat_count = 0
                self.machine.battle_start_time = time.time()
                self.machine.transition_to(self.machine.STATE_BATTLE)
                return True
        return False

    def _check_stamina_retreat(self, screen_img, rect) -> bool:
        """檢查體力/麵包耗盡退避"""
        if self.machine.stamina_retreat_start_time is not None:
            logging.info("🍞 [領地探索] 處於體力退避狀態，切換至 COLLECT_ONLY 待機。")
            self.machine.transition_to(self.machine.STATE_COLLECT_ONLY)
            return True
        return False
