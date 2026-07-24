from vision.color_classifier import GearColorClassifier

class BaseStateHandler:
    def __init__(self, machine):
        """
        初始化狀態處理器基類。
        
        :param machine: 狀態機實例 (GameStateMachine)
        """
        self.machine = machine
        self.capturer = machine.capturer
        self.matcher = machine.matcher
        self.mouse = machine.mouse
        self.color_classifier = GearColorClassifier()

    def handle(self, screen_img, rect):
        """
        處理當前步驟。每個子類必須實作此方法。
        
        :param screen_img: 擷取到的遊戲畫面影像 (BGR 格式)
        :param rect: 遊戲視窗座標範圍字典
        """
        raise NotImplementedError

    def classify_slot_color(self, crop):
        """
        [共用特徵工程轉接] 辨識裝備格子的稀有度顏色。
        現已模組化委託給 GearColorClassifier，以符合單一職責原則。
        
        :param crop: 裁剪的格子圖像 (BGR 格式)
        :return: 識別品質字串
        """
        res = self.color_classifier.classify(crop)
        return res["main_color"]

    def match_mutually_exclusive_tabs(self, screen_img, template_a, template_b, margin=0.02, threshold=0.70):
        """
        [專案標準門面 API] 互斥 UI 頁籤相對優勢比對。
        只有當 c_a >= threshold 且 c_a 高出 c_b 達 margin 以上時才判定頁籤 A 為啟用狀態。
        """
        return self.matcher.match_mutually_exclusive_tabs(
            screen_img, template_a, template_b, margin=margin, threshold=threshold
        )
