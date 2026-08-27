import os
import time
import logging
from states.domains.base_domain import BaseDomainStrategy

class GoldenEmpireStrategy(BaseDomainStrategy):
    """
    🏛️ 黃金古國 (Golden Empire - Domain 1) 專屬探索與事件策略。
    負責：探索按鈕點擊、古國寶藏挖寶事件（第 1 次免費開箱 ➔ 確認 ➔ 離開）。
    """
    EXPLORE_BUTTON = "domains/golden_empire/explore_btn.png"
    TREASURE_FEATURE_TEMPLATES = [
        "domains/find_treasure.png",
        "domains/treasure.png"
    ]
    CONFIRM_TEMPLATES = [
        "common/confirm.png",
        "common/ok.png"
    ]
    QUIT_TEMPLATES = [
        "common/quit.png",
        "domains/common/exit_to_lobby.png"
    ]

    def __init__(self, handler):
        super().__init__(handler)
        self.last_treasure_click_time = 0.0

    def get_explore_button(self) -> str:
        return self.EXPLORE_BUTTON

    def handle_custom_events(self, screen_img, rect) -> bool:
        """
        檢查並處理黃金古國挖寶事件 (Treasure Subflow)。
        """
        # 1. 檢查是否處於挖寶介面
        is_treasure_screen = False
        treasure_pos = None
        for t_temp in self.TREASURE_FEATURE_TEMPLATES:
            if os.path.exists(os.path.join("templates", t_temp)):
                pos, conf = self.matcher.match(screen_img, t_temp, threshold=0.75)
                if pos:
                    is_treasure_screen = True
                    treasure_pos = pos
                    break

        if is_treasure_screen:
            logging.info("🎁 [黃金古國] 偵測到古國寶藏挖寶畫面，執行單次免費開箱流程...")
            self.handler.notify_ui_progress()
            
            # 點擊免費寶箱
            if treasure_pos:
                click_x = rect["left"] + treasure_pos[0]
                click_y = rect["top"] + treasure_pos[1]
                self.mouse.click(click_x, click_y)
                time.sleep(0.3)

            # 檢查並點擊確認按鈕（若有獲得獎勵彈窗）
            for c_temp in self.CONFIRM_TEMPLATES:
                if os.path.exists(os.path.join("templates", c_temp)):
                    pos_c, _ = self.matcher.match(screen_img, c_temp, threshold=0.80)
                    if pos_c:
                        self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                        time.sleep(0.2)
                        break

            # 點擊離開/退出按鈕以返回古國主場景
            for q_temp in self.QUIT_TEMPLATES:
                if os.path.exists(os.path.join("templates", q_temp)):
                    pos_q, _ = self.matcher.match(screen_img, q_temp, threshold=0.75)
                    if pos_q:
                        self.mouse.click(rect["left"] + pos_q[0], rect["top"] + pos_q[1])
                        time.sleep(0.2)
                        break

            return True

        # 2. 獨立檢查畫面上殘留的確認或退出按鈕 (防遮罩殘留)
        for c_temp in self.CONFIRM_TEMPLATES:
            if os.path.exists(os.path.join("templates", c_temp)):
                pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=0.85)
                if pos_c:
                    logging.info(f"👉 [黃金古國] 偵測到獎勵確認按鈕 [{c_temp}] (信心度: {conf_c:.4f})，點擊關閉。")
                    self.handler.notify_ui_progress()
                    self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                    time.sleep(0.2)
                    return True

        return False
