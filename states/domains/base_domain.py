import os
from states.domains.treasure_subflow import DomainTreasureSubflow

class BaseDomainStrategy:
    """
    領地策略基類 (Base Domain Strategy)。
    定義領域主場景探索按鈕與通用隨機事件處理協定。
    預設使用通用探索按鈕 (domains/common/explore_btn.png) 與通用隨機挖寶事件 (DomainTreasureSubflow)。
    各特定領地（黃金古國、冷誓要塞等）可繼承並擴充其專屬邏輯。
    """
    EXPLORE_BUTTON = "domains/common/explore_btn.png"

    def __init__(self, handler):
        self.handler = handler
        self.machine = handler.machine
        self.matcher = handler.matcher
        self.mouse = handler.mouse
        self.treasure_subflow = DomainTreasureSubflow(handler)

    def get_explore_button(self) -> str:
        """返回領地探索按鈕模板相對路徑，預設為通用探索按鈕"""
        return self.EXPLORE_BUTTON

    def handle_custom_events(self, screen_img, rect) -> bool:
        """
        處理領地隨機事件。
        預設執行通用挖寶事件處理器；子類若有專屬隨機事件可先處理，未命中則委派基類。
        """
        if self.treasure_subflow and self.treasure_subflow.handle(screen_img, rect):
            return True
        return False

    def handle_explore_click(self, screen_img, rect) -> bool:
        """
        在主場景中尋找並點擊探索按鈕。
        """
        btn = self.get_explore_button()
        if not btn:
            return False
        if os.path.exists(os.path.join("templates", btn)):
            pos, conf = self.matcher.match(screen_img, btn, threshold=0.80)
            if pos:
                click_x = rect["left"] + pos[0]
                click_y = rect["top"] + pos[1]
                self.handler.notify_ui_progress()
                self.mouse.click(click_x, click_y)
                return True
        return False
