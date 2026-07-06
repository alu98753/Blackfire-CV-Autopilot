class BaseStateHandler:
    def __init__(self, machine):
        """
        初始化狀態處理器基類。
        
        :param machine: 狀態機實例 (GameStateMachine)
        """
        self.machine = machine
        self.matcher = machine.matcher
        self.mouse = machine.mouse

    def handle(self, screen_img, rect):
        """
        處理當前步驟。每個子類必須實作此方法。
        
        :param screen_img: 擷取到的遊戲畫面影像 (BGR 格式)
        :param rect: 遊戲視窗座標範圍字典
        """
        raise NotImplementedError
