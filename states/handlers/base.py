import cv2
import numpy as np

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

    def classify_slot_color(self, crop):
        """
        [共用特徵工程] 辨識裝備格子的稀有度顏色。
        採用精確環帶過濾，避開外側選取發光邊框與中心點打勾標誌，提取純淨的品質底色。
        
        :param crop: 裁剪的格子圖像 (BGR 格式，尺寸應為 120x120 左右，自適應縮放)
        :return: 識別品質 "gray_or_empty", "green", "blue", "purple", "orange_yellow", "red"
        """
        # 自適應縮放到 120x120，確保採樣遮罩坐標一致
        h, w = crop.shape[:2]
        if h != 120 or w != 120:
            crop = cv2.resize(crop, (120, 120))

        # 建立環狀遮罩：採集 (15, 15) 到 (105, 105) 之間，避開中心打勾 (35, 35) 到 (85, 85)
        mask = np.zeros((120, 120), dtype=np.uint8)
        cv2.rectangle(mask, (15, 15), (105, 105), 255, -1)
        cv2.rectangle(mask, (35, 35), (85, 85), 0, -1)
        
        ring_pixels = crop[mask == 255]
        if len(ring_pixels) == 0:
            return "gray_or_empty"
            
        hsv_pixels = cv2.cvtColor(np.expand_dims(ring_pixels, axis=0), cv2.COLOR_BGR2HSV)[0]
        
        counts = {
            "red": 0,
            "orange_yellow": 0,
            "green": 0,
            "blue": 0,
            "purple": 0
        }
        
        for h_val, s, v in hsv_pixels:
            # 紫色品質 (暗色背景適應)：飽和度 >= 50，亮度 >= 12
            if 130 < h_val < 165:
                if s >= 50 and v >= 12:
                    counts["purple"] += 1
            # 藍色品質：飽和度 >= 55，亮度 >= 20
            elif 90 <= h_val <= 130:
                if s >= 55 and v >= 20:
                    counts["blue"] += 1
            # 橙黃色品質 (高亮高飽和，排除大石棒的咖啡灰)：飽和度 >= 100，亮度 >= 60
            elif 10 <= h_val <= 34:
                if s >= 100 and v >= 60:
                    counts["orange_yellow"] += 1
            # 紅色品質 (高亮高飽和)：飽和度 >= 100，亮度 >= 60
            elif h_val <= 9 or h_val >= 165:
                if s >= 100 and v >= 60:
                    counts["red"] += 1
            # 綠色品質：飽和度 >= 50，亮度 >= 20
            elif 35 <= h_val <= 85:
                if s >= 50 and v >= 20:
                    counts["green"] += 1
                    
        max_color = "gray_or_empty"
        max_count = 300 # 品質判斷的點數閾值
        for color, count in counts.items():
            if count > max_count:
                max_count = count
                max_color = color
        return max_color
