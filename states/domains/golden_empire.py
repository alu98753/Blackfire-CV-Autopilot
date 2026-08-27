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
    OPEN_BUTTON = "domains/golden_empire/open.png"
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
        1. 偵測並點擊【打開 (open.png)】按鈕 (免費開箱，閉環輪詢直到消失)。
        2. 點擊【確認】彈窗。
        3. 點擊【離開】按鈕安全返回古國主場景。
        """
        # 1. 檢查並點擊【打開】按鈕 (open.png)
        if os.path.exists(os.path.join("templates", self.OPEN_BUTTON)):
            pos_open, conf_o = self.matcher.match(screen_img, self.OPEN_BUTTON, threshold=0.75)
            if pos_open:
                logging.info(f"🎁 [黃金古國] 偵測到挖寶【打開】按鈕 (信心度: {conf_o:.4f})，發起單次免費開箱流程...")
                click_x = rect["left"] + pos_open[0]
                click_y = rect["top"] + pos_open[1]
                self.handler.click_and_wait_until_gone(
                    self.OPEN_BUTTON, click_x, click_y, rect,
                    timeout=4.0, threshold=0.75, post_delay=0.4
                )

                # 2. 檢查並點擊確認按鈕（若有獲得獎勵彈窗），閉環等待確認按鈕消失
                for c_temp in self.CONFIRM_TEMPLATES:
                    if os.path.exists(os.path.join("templates", c_temp)):
                        pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=0.80)
                        if pos_c:
                            logging.info(f"👉 [黃金古國] 偵測到獎勵確認按鈕 [{c_temp}] (信心度: {conf_c:.4f})，點擊確認領取...")
                            self.handler.click_and_wait_until_gone(
                                c_temp, rect["left"] + pos_c[0], rect["top"] + pos_c[1], rect,
                                timeout=4.0, threshold=0.80, post_delay=0.4
                            )
                            break

                # 3. 點擊離開/退出按鈕以返回古國主場景，閉環等待直到退出
                for q_temp in self.QUIT_TEMPLATES:
                    if os.path.exists(os.path.join("templates", q_temp)):
                        pos_q, conf_q = self.matcher.match(screen_img, q_temp, threshold=0.75)
                        if pos_q:
                            logging.info(f"👉 [黃金古國] 點擊退出按鈕 [{q_temp}] (信心度: {conf_q:.4f}) 返回主場景...")
                            self.handler.click_and_wait_until_gone(
                                q_temp, rect["left"] + pos_q[0], rect["top"] + pos_q[1], rect,
                                timeout=4.0, threshold=0.75, post_delay=0.4
                            )
                            break

                return True

        # 2. 獨立檢查畫面上殘留的確認或退出按鈕 (防遮罩殘留)
        for c_temp in self.CONFIRM_TEMPLATES:
            if os.path.exists(os.path.join("templates", c_temp)):
                pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=0.85)
                if pos_c:
                    logging.info(f"👉 [黃金古國] 偵測到殘留確認按鈕 [{c_temp}] (信心度: {conf_c:.4f})，點擊關閉。")
                    self.handler.click_and_wait_until_gone(
                        c_temp, rect["left"] + pos_c[0], rect["top"] + pos_c[1], rect,
                        timeout=4.0, threshold=0.85, post_delay=0.3
                    )
                    return True

        return False
