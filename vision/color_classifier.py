import cv2
import numpy as np

class GearColorClassifier:
    """
    貴重與普通裝備色彩分類器。
    採用自適應 120x120 環狀遮罩特徵工程與獨立 HSV 閾值設計，回傳結構化的判定字典。
    """
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

        # 建立環狀遮罩：採集 (15, 15) 到 (105, 105) 之間，避開中心打勾 (35, 35) 到 (85, 85)
        mask = np.zeros((120, 120), dtype=np.uint8)
        cv2.rectangle(mask, (15, 15), (105, 105), 255, -1)
        cv2.rectangle(mask, (35, 35), (85, 85), 0, -1)
        
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
                
        is_rare = max_color in ["blue", "purple", "orange_yellow", "red"]
        ratios = {color: count / total_pixels for color, count in counts.items()}
        
        return {
            "main_color": max_color,
            "is_rare": is_rare,
            "counts": counts,
            "ratios": ratios
        }
