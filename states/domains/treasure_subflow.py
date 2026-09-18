import os
import time
import logging

class DomainTreasureSubflow:
    """
    🎁 領地通用隨機挖寶事件處理器 (Domain Treasure Subflow)。
    負責：偵測挖寶畫面、單次免費開箱 (open.png)、確認獎勵、點擊退出返回領地主場景。
    通用於所有領地（黃金古國、淵獸之巢、冷誓要塞等）。

    Treasure evidence 契約：
    - open.png: 直接 actionable evidence，觸發開箱與退出流程。
    - find_treasure.png / treasure.png: treasure-scene evidence，標識處於挖寶畫面。
      若只有場景特徵而缺少 open.png，嚴格遵守 "Unknown never guesses"，不發出盲點並保留事件邊界。
    """
    OPEN_BUTTON = "domains/common/open.png"
    FIND_TREASURE_TEMPLATE = "domains/common/find_treasure.png"
    TREASURE_CARD_TEMPLATE = "domains/common/treasure.png"
    CONFIRM_TEMPLATES = [
        "common/confirm.png",
        "common/ok.png"
    ]
    QUIT_TEMPLATES = [
        "common/quit.png",
        "domains/common/exit_to_lobby.png"
    ]

    def __init__(self, handler):
        self.handler = handler
        self.machine = handler.machine
        self.matcher = handler.matcher
        self.mouse = handler.mouse

    def handle(self, screen_img, rect) -> bool:
        """
        檢查並處理領地挖寶事件。
        1. 偵測並點擊【打開 (open.png)】按鈕 (免費開箱，閉環輪詢直到消失)。
        2. 若無 open.png 但出現 find_treasure.png / treasure.png，識別為挖寶場景證據，不盲點並等待下一輪。
        3. 處理殘留之確認彈窗。
        """
        # 1. 檢查並點擊【打開】按鈕 (open.png) - 直接 actionable evidence
        if os.path.exists(os.path.join("templates", self.OPEN_BUTTON)):
            pos_open, conf_o = self.matcher.match(screen_img, self.OPEN_BUTTON, threshold=0.75)
            if pos_open:
                logging.info(f"🎁 [領地挖寶] 偵測到挖寶【打開】按鈕 [{self.OPEN_BUTTON}] (信心度: {conf_o:.4f})，發起單次免費開箱流程...")
                click_x = rect["left"] + pos_open[0]
                click_y = rect["top"] + pos_open[1]
                # 精確點擊【打開】按鈕並閉環等待直到按鈕消失
                self.handler.click_and_wait_until_gone(
                    self.OPEN_BUTTON, click_x, click_y, rect,
                    timeout=4.0, threshold=0.75, post_delay=0.4
                )

                # 開箱後等待 3 秒讓獎勵畫面定格，方便確認獲得道具
                logging.info("⏳ [領地挖寶 Debug] 開箱完成，等待 3 秒定格觀察獲得之獎勵物品...")
                time.sleep(3.0)

                # 2. 檢查並點擊確認按鈕（若有獲得獎勵彈窗），閉環等待確認按鈕消失
                cap_img = self.machine.capturer.capture(rect) if self.machine.capturer else screen_img
                current_img = cap_img if cap_img is not None else screen_img
                for c_temp in self.CONFIRM_TEMPLATES:
                    if os.path.exists(os.path.join("templates", c_temp)):
                        pos_c, conf_c = self.matcher.match(current_img, c_temp, threshold=0.80)
                        if pos_c:
                            logging.info(f"👉 [領地挖寶] 偵測到獎勵確認按鈕 [{c_temp}] (信心度: {conf_c:.4f})，點擊確認領取...")
                            self.handler.click_and_wait_until_gone(
                                c_temp, rect["left"] + pos_c[0], rect["top"] + pos_c[1], rect,
                                timeout=4.0, threshold=0.80, post_delay=0.4
                            )
                            break

                # 3. 點擊離開/退出按鈕以返回領地主場景，閉環等待直到退出
                cap_img_q = self.machine.capturer.capture(rect) if self.machine.capturer else current_img
                current_img_q = cap_img_q if cap_img_q is not None else current_img
                for q_temp in self.QUIT_TEMPLATES:
                    if os.path.exists(os.path.join("templates", q_temp)):
                        pos_q, conf_q = self.matcher.match(current_img_q, q_temp, threshold=0.75)
                        if pos_q:
                            logging.info(f"👉 [領地挖寶] 點擊退出按鈕 [{q_temp}] (信心度: {conf_q:.4f}) 返回主場景...")
                            self.handler.click_and_wait_until_gone(
                                q_temp, rect["left"] + pos_q[0], rect["top"] + pos_q[1], rect,
                                timeout=4.0, threshold=0.75, post_delay=0.4
                            )
                            break

                return True

        # 2. 檢查挖寶場景特徵 (find_treasure.png / treasure.png) - treasure-scene evidence
        for scene_tpl in (self.FIND_TREASURE_TEMPLATE, self.TREASURE_CARD_TEMPLATE):
            if os.path.exists(os.path.join("templates", scene_tpl)):
                pos_sc, conf_sc = self.matcher.match(screen_img, scene_tpl, threshold=0.75, quiet=True)
                if pos_sc:
                    logging.info(
                        f"🎁 [領地挖寶] 偵測到挖寶場景特徵 [{scene_tpl}] (信心度: {conf_sc:.4f})，但未見免費打開按鈕 ({self.OPEN_BUTTON})。"
                    )
                    # 依據 "Unknown never guesses"：嚴禁在缺少 open.png 時盲點未知寶箱座標。
                    # 本 frame 判定為已命中挖寶事件場景，不發出未知點擊，等待下一輪觀察。
                    return True

        # 3. 獨立檢查畫面上殘留的確認按鈕 (先排除食物不足彈窗 no_bread2.png)
        if os.path.exists(os.path.join("templates", "no_bread/no_bread2.png")):
            pos_nb2, _ = self.matcher.match(screen_img, "no_bread/no_bread2.png", threshold=0.85)
            if pos_nb2:
                # 由全域 stamina_flow 統一處理食物不足退避，此處不執行盲點
                return False

        for c_temp in self.CONFIRM_TEMPLATES:
            if os.path.exists(os.path.join("templates", c_temp)):
                pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=0.85)
                if pos_c:
                    logging.info(f"👉 [領地挖寶] 偵測到殘留確認按鈕 [{c_temp}] (信心度: {conf_c:.4f})，點擊關閉。")
                    self.handler.click_and_wait_until_gone(
                        c_temp, rect["left"] + pos_c[0], rect["top"] + pos_c[1], rect,
                        timeout=4.0, threshold=0.85, post_delay=0.3
                    )
                    return True

        return False
