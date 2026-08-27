class BaseDomainStrategy:
    """
    領地策略抽象基類 (Domain Strategy Interface)。
    定義各領地（黃金古國、冷誓要塞等）專屬的按鈕路徑與特殊事件處理協定。
    """
    def __init__(self, handler):
        self.handler = handler
        self.machine = handler.machine
        self.matcher = handler.matcher
        self.mouse = handler.mouse

    def get_explore_button(self) -> str:
        """返回該領地專屬的探索按鈕模板相對路徑"""
        raise NotImplementedError

    def handle_custom_events(self, screen_img, rect) -> bool:
        """
        處理該領地特有的隨機事件（如挖寶、祭壇等）。
        若命中並處理事件，返回 True；否則返回 False。
        """
        return False

    def handle_explore_click(self, screen_img, rect) -> bool:
        """
        在主場景中尋找並點擊探索按鈕。
        """
        btn = self.get_explore_button()
        if not btn:
            return False
        import os
        if os.path.exists(os.path.join("templates", btn)):
            pos, conf = self.matcher.match(screen_img, btn, threshold=0.80)
            if pos:
                click_x = rect["left"] + pos[0]
                click_y = rect["top"] + pos[1]
                self.handler.notify_ui_progress()
                self.mouse.click(click_x, click_y)
                return True
        return False
