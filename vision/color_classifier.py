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
            # 紫色品質 (暗色背景適應)：飽和度 >= 50，亮度 >= 12
            if 130 < h_val < 165:
                if s >= 50 and v >= 12:
                    counts["purple"] += 1
            # 藍色品質：飽和度 >= 55，亮度 >= 20
            elif 90 <= h_val <= 130:
                if s >= 55 and v >= 20:
                    counts["blue"] += 1
            # 橙黃色品質 (排除棕土色/黃褐色背景干擾)：飽和度 >= 130，亮度 >= 90
            elif 10 <= h_val <= 34:
                if s >= 130 and v >= 90:
                    counts["orange_yellow"] += 1
            # 紅色品質 (排除火焰強光溢出)：飽和度 >= 130，亮度 >= 90
            elif h_val <= 9 or h_val >= 165:
                if s >= 130 and v >= 90:
                    counts["red"] += 1
            # 綠色品質：飽和度 >= 50，亮度 >= 20
            elif 35 <= h_val <= 85:
                if s >= 50 and v >= 20:
                    counts["green"] += 1
                    
        # 分顏色計數門檻，防禦內圍雜色與背景溢出 (橙色200，紅色200，其餘400)
        color_thresholds = {
            "red": 200,
            "orange_yellow": 200,
            "green": 400,
            "blue": 400,
            "purple": 400
        }
        
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
