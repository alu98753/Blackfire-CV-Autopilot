import cv2
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class TemplateMatcher:
    def __init__(self, templates_dir="templates"):
        self.templates_dir = templates_dir
        self._cached_templates = {}

    def _load_template(self, template_name):
        """
        延遲載入並快取模板圖片。
        """
        if template_name in self._cached_templates:
            return self._cached_templates[template_name]

        # 支援直接傳入檔名或完整路徑
        if os.path.isabs(template_name) or template_name.startswith("."):
            path = template_name
        else:
            path = os.path.join(self.templates_dir, template_name)

        if not os.path.exists(path):
            logging.error(f"找不到模板圖片檔案: {path}")
            return None

        # 讀取圖片，預設讀取彩色 BGR 影像
        template_img = cv2.imread(path)
        if template_img is None:
            logging.error(f"無法解析/讀取圖片: {path}")
            return None

        self._cached_templates[template_name] = template_img
        return template_img

    def match(self, screen_img, template_name, threshold=0.8, check_brightness=False):
        """
        在 screen_img 中尋找與 template_name 匹配度最高的位置。
        
        :param screen_img: 來源畫面 (numpy array)
        :param template_name: 模板檔名或路徑
        :param threshold: 信心度閥值 (0.0 ~ 1.0)
        :param check_brightness: 是否檢查匹配區域與模板的亮度比例，避免誤判背景調暗按鈕
        :return: (center_x, center_y), confidence. 若未達閥值，回傳 None, confidence
        """
        template_img = self._load_template(template_name)
        if template_img is None or screen_img is None:
            return None, 0.0

        screen_h, screen_w = screen_img.shape[:2]
        temp_h, temp_w = template_img.shape[:2]

        # 如果模板比來源畫面大，必無法匹配
        if temp_h > screen_h or temp_w > screen_w:
            logging.warning(f"模板尺寸 ({temp_w}x{temp_h}) 大於來源畫面尺寸 ({screen_w}x{screen_h})。")
            return None, 0.0

        # 使用標準化相關係數配對方法
        res = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        # 取得匹配最高點的左上角座標
        top_left = max_loc
        # 計算中心點
        center_x = top_left[0] + temp_w // 2
        center_y = top_left[1] + temp_h // 2

        if max_val >= threshold:
            if check_brightness:
                import numpy as np
                # 取得匹配區域切片
                crop = screen_img[top_left[1]:top_left[1]+temp_h, top_left[0]:top_left[0]+temp_w]
                
                # 計算灰階平均亮度
                temp_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
                crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                
                mean_temp = np.mean(temp_gray)
                mean_crop = np.mean(crop_gray)
                
                # 亮度比例 (crop / temp)
                brightness_ratio = mean_crop / max(1.0, mean_temp)
                
                # 若亮度比例低於 0.8，代表該按鈕已被黑色遮罩調暗，是不可互動的背景按鈕
                if brightness_ratio < 0.8:
                    # 動態導入工具模組下的公用保存函數，實現關注點分離
                    try:
                        from tools.analyze_template_brightness import save_diagnostic_images
                        save_diagnostic_images(screen_img, template_img, top_left, temp_w, temp_h, max_val, brightness_ratio, template_name)
                    except Exception as e:
                        logging.error(f"無法調用 tools/save_diagnostic_images: {e}")
                    
                    base = os.path.splitext(os.path.basename(template_name))[0]
                    logging.warning(
                        f"⚠️ 模板 '{template_name}' 匹配相似度達標 [{max_val:.4f}]，"
                        f"但亮度比例偏低 ({brightness_ratio:.2f} < 0.8)，判定為背景暗區按鈕，予以過濾！"
                        f"已自動保存診斷圖片至 debug_{base}_dim_full.png 和 debug_{base}_dim_crop.png"
                    )
                    return None, max_val

            logging.info(f"成功匹配模板 '{template_name}'！信心度: {max_val:.4f}，中心座標: ({center_x}, {center_y})")
            return (center_x, center_y), max_val
        else:
            logging.debug(f"模板 '{template_name}' 匹配信心度未達閥值 (目前: {max_val:.4f} < {threshold})")
            return None, max_val

if __name__ == "__main__":
    # 簡單單體測試
    import numpy as np
    # 建立一個測試用的純黑畫面，中間畫一個白色方塊
    test_screen = np.zeros((600, 800, 3), dtype=np.uint8)
    cv2.rectangle(test_screen, (200, 200), (300, 300), (255, 255, 255), -1)

    # 建立一個與白色方塊大小相同的模板
    test_template = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(test_template, (0, 0), (100, 100), (255, 255, 255), -1)
    
    os.makedirs("templates", exist_ok=True)
    cv2.imwrite("templates/test_rect.png", test_template)
    
    matcher = TemplateMatcher()
    pos, conf = matcher.match(test_screen, "test_rect.png", threshold=0.9)
    print(f"匹配結果 - 座標: {pos}, 信心度: {conf}")
    # 預期應在 (250, 250) 位置
