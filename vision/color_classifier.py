import cv2
import numpy as np

class GearColorClassifier:
    """
    貴重與普通裝備色彩分類器。
    採用自適應 120x120 環狀遮罩特徵工程與獨立 HSV 閾值設計，回傳結構化的判定字典。
    """
    # 顏色特徵閾值定義 (總像素為 2240 px，門檻 350~400 px 約佔環狀 16%~18%，留有高達 2~3 倍安全裕度並徹底免疫零星雜色)
    COLOR_THRESHOLDS = {
        "red": 350,
        "orange_yellow": 350,
        "green": 400,
        "blue": 400,
        "purple": 350,
    }

    # 藍色邊框門檻：S >= 110, V >= 70 (石框冷灰溝槽 S=55, V=51，具備 S+55, V+19 之巨大安全落差；真實藍邊 S 均值 227)
    BLUE_H_RANGE = (90, 130)
    BLUE_MIN_S = 110
    BLUE_MIN_V = 70

    # 綠色邊框門檻：S >= 100, V >= 60 (真實綠邊 S 均值 222, V 均值 151)
    GREEN_H_RANGE = (35, 85)
    GREEN_MIN_S = 100
    GREEN_MIN_V = 60

    # 紫色邊框門檻：S >= 90, V >= 50 (真實紫邊 S 均值 230, V 均值 138，兼顧暗紫色表現)
    PURPLE_H_RANGE = (131, 164)
    PURPLE_MIN_S = 90
    PURPLE_MIN_V = 50

    # 橙黃色邊框門檻 (排除棕土色/黃褐色背景干擾)：S >= 120, V >= 80
    ORANGE_YELLOW_H_RANGE = (10, 34)
    ORANGE_YELLOW_MIN_S = 120
    ORANGE_YELLOW_MIN_V = 80

    # 紅色邊框門檻 (排除火焰強光溢出)：S >= 120, V >= 80
    RED_MIN_S = 120
    RED_MIN_V = 80

    def __init__(self):
        pass

    def classify(self, crop_img):
        """
        對裝備格子圖像進行稀有度色彩分類。
        
        :param crop_img: 單個物品欄格子的 BGR 圖像 (numpy array)
        :return: 結構化判定字典，包含 main_color, is_rare, counts, ratios
        """
        # 自適應縮放到 120x120，確保採樣遮罩坐標一致
        h, w = crop_img.shape[:2]
        if h != 120 or w != 120:
            crop = cv2.resize(crop_img, (120, 120))
        else:
            crop = crop_img

        # 建立緊貼最外邊緣的超極細環狀遮罩 (寬度僅為 5 像素)，完美避開內部裝備圖案干擾
        mask = np.zeros((120, 120), dtype=np.uint8)
        cv2.rectangle(mask, (2, 2), (118, 118), 255, -1)
        cv2.rectangle(mask, (7, 7), (113, 113), 0, -1)
        
        ring_pixels = crop[mask == 255]
        total_pixels = len(ring_pixels)
        
        counts = {
            "red": 0,
            "orange_yellow": 0,
            "green": 0,
            "blue": 0,
            "purple": 0
        }
        
        if total_pixels == 0:
            return {
                "main_color": "gray_or_empty",
                "is_rare": False,
                "counts": counts,
                "ratios": {col: 0.0 for col in counts}
            }
            
        hsv_pixels = cv2.cvtColor(np.expand_dims(ring_pixels, axis=0), cv2.COLOR_BGR2HSV)[0]
        
        for h_val, s, v in hsv_pixels:
            # 紫色品質 (暗色背景適應)
            if self.PURPLE_H_RANGE[0] <= h_val <= self.PURPLE_H_RANGE[1]:
                if s >= self.PURPLE_MIN_S and v >= self.PURPLE_MIN_V:
                    counts["purple"] += 1
            # 藍色品質 (過濾冷灰色石材 S=55, V=51 雜色干擾)
            elif self.BLUE_H_RANGE[0] <= h_val <= self.BLUE_H_RANGE[1]:
                if s >= self.BLUE_MIN_S and v >= self.BLUE_MIN_V:
                    counts["blue"] += 1
            # 橙黃色品質 (排除棕土色/黃褐色背景干擾)
            elif self.ORANGE_YELLOW_H_RANGE[0] <= h_val <= self.ORANGE_YELLOW_H_RANGE[1]:
                if s >= self.ORANGE_YELLOW_MIN_S and v >= self.ORANGE_YELLOW_MIN_V:
                    counts["orange_yellow"] += 1
            # 紅色品質 (排除火焰強光溢出)
            elif h_val <= 9 or h_val >= 165:
                if s >= self.RED_MIN_S and v >= self.RED_MIN_V:
                    counts["red"] += 1
            # 綠色品質
            elif self.GREEN_H_RANGE[0] <= h_val <= self.GREEN_H_RANGE[1]:
                if s >= self.GREEN_MIN_S and v >= self.GREEN_MIN_V:
                    counts["green"] += 1
                    
        color_thresholds = self.COLOR_THRESHOLDS
        
        max_color = "gray_or_empty"
        max_count = 0
        for color, count in counts.items():
            thresh = color_thresholds[color]
            if count >= thresh and count > max_count:
                max_count = count
                max_color = color
                
        is_rare = max_color in ["blue", "purple", "orange_yellow", "red"]
        ratios = {color: count / total_pixels for color, count in counts.items()}
        
        return {
            "main_color": max_color,
            "is_rare": is_rare,
            "counts": counts,
            "ratios": ratios
        }
