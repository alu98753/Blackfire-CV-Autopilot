import cv2
import os
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class TemplateMatcher:
    def __init__(self, templates_dir="templates", template_scale=1.0):
        self.templates_dir = templates_dir
        self.template_scale = template_scale
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

        # 如果設定了縮放比例且不為 1.0，動態對模板進行縮放
        if self.template_scale != 1.0:
            h, w = template_img.shape[:2]
            nw = int(w * self.template_scale)
            nh = int(h * self.template_scale)
            if nw > 0 and nh > 0:
                template_img = cv2.resize(
                    template_img, 
                    (nw, nh), 
                    interpolation=cv2.INTER_AREA if self.template_scale < 1.0 else cv2.INTER_CUBIC
                )

        self._cached_templates[template_name] = template_img
        return template_img

    def match(self, screen_img, template_name, threshold=0.8, brightness_threshold=0.0, quiet=False):
        """
        在 screen_img 中尋找與 template_name 匹配度最高的位置。
        
        :param screen_img: 來源畫面 (numpy array)
        :param template_name: 模板檔名或路徑
        :param threshold: 信心度閥值 (0.0 ~ 1.0)
        :param brightness_threshold: 亮度比例門檻 (0.0代表不啟用，大於0代表低於此比例則過濾，並進行最亮點選擇)
        :return: (center_x, center_y), confidence. 若未達閥值，回傳 None, confidence
        """
        template_img = self._load_template(template_name)
        if template_img is None or screen_img is None:
            return None, 0.0

        screen_h, screen_w = screen_img.shape[:2]
        temp_h, temp_w = template_img.shape[:2]
        
        # logging.info(f"[除錯-比對大小] 模板 '{template_name}' 大小: {temp_w}x{temp_h}, 來源畫面大小: {screen_w}x{screen_h}")

        # 如果模板比來源畫面大，必無法匹配，直接回傳 None 以免 OpenCV 崩潰
        if temp_h > screen_h or temp_w > screen_w:
            if not quiet:
                logging.warning(f"模板尺寸 ({temp_w}x{temp_h}) 大於來源畫面尺寸 ({screen_w}x{screen_h})。")
            return None, 0.0

        # 1. 快速金字塔下採樣初步檢測 (Image Pyramids Acceleration)
        # 對於大尺寸畫面 (>= 720p)，先以 1/2 縮放圖進行極速預檢
        # 若 1/2 縮放圖最高相似度小於 (threshold - 0.05)，可 100% 判定無匹配，直接回傳以節省 75% 以上全圖比對時間
        if screen_h >= 720 and temp_h >= 30 and temp_w >= 30:
            small_screen = cv2.resize(screen_img, (screen_w // 2, screen_h // 2), interpolation=cv2.INTER_AREA)
            small_temp = cv2.resize(template_img, (max(1, temp_w // 2), max(1, temp_h // 2)), interpolation=cv2.INTER_AREA)
            res_small = cv2.matchTemplate(small_screen, small_temp, cv2.TM_CCOEFF_NORMED)
            _, max_val_small, _, _ = cv2.minMaxLoc(res_small)
            if max_val_small < threshold - 0.05:
                return None, max_val_small

        # 使用標準化相關係數配對方法
        res = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
        
        # 2. 找出所有相似度大於等於門檻的候選點，並按相似度從大到小排序進行 Non-Maximum Suppression (NMS)
        loc = np.where(res >= threshold)
        pts = list(zip(*loc[::-1]))
        raw_candidates = [(pt[0], pt[1], res[pt[1], pt[0]]) for pt in pts]
        raw_candidates.sort(key=lambda x: x[2], reverse=True)

        candidates = []
        for x, y, conf in raw_candidates:
            # 進行簡單的聚類抑制，避免重疊框
            too_close = False
            for cx, cy, c_conf in candidates:
                if abs(x - cx) < 20 and abs(y - cy) < 20:
                    too_close = True
                    break
            if not too_close:
                candidates.append((x, y, conf))

        if not candidates:
            # 若無任何達標點，回傳最大相似度
            _, max_val, _, _ = cv2.minMaxLoc(res)
            return None, max_val

        # 2. 計算每個候選點的亮度比例
        temp_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        mean_temp = np.mean(temp_gray)
        screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)

        evaluated_candidates = []
        for x, y, conf in candidates:
            crop = screen_gray[y:y+temp_h, x:x+temp_w]
            mean_crop = np.mean(crop)
            ratio = mean_crop / max(1.0, mean_temp)
            evaluated_candidates.append((x, y, conf, ratio))

        # 3. 執行自適應亮度過濾與最亮排序選擇
        if brightness_threshold > 0.0:
            # (a) 基本亮度底線過濾
            passed = [c for c in evaluated_candidates if c[3] >= brightness_threshold]
            
            if not passed:
                # 若全部都小於及格門檻，說明全是背景被調暗的按鈕，予以過濾
                best_raw = max(evaluated_candidates, key=lambda c: c[2])
                try:
                    from tools.analyze_template_brightness import save_diagnostic_images
                    save_diagnostic_images(screen_img, template_img, (best_raw[0], best_raw[1]), temp_w, temp_h, best_raw[2], best_raw[3], template_name)
                except Exception as e:
                    logging.error(f"無法調用 tools/save_diagnostic_images: {e}")
                
                base = os.path.splitext(os.path.basename(template_name))[0]
                logging.warning(
                    f"⚠️ 模板 '{template_name}' 匹配到 {len(candidates)} 個候選點，"
                    f"但所有點的亮度比例均低於門檻 {brightness_threshold:.2f}，判定為背景暗區按鈕，予以過濾！"
                )
                return None, best_raw[2]
            
            # (b) 相似度最大化排序：在亮度合格的候選點中，選擇相似度最高的那一個
            best_selected = max(passed, key=lambda c: c[2])
        else:
            # 若未啟用亮度檢查，直接抓取相似度最高的點
            best_selected = max(evaluated_candidates, key=lambda c: c[2])

        # 4. 回傳最優點的中心座標與相似度
        final_x, final_y, final_conf, final_ratio = best_selected
        center_x = final_x + temp_w // 2
        center_y = final_y + temp_h // 2

        if not quiet:
            logging.info(f"成功匹配模板 '{template_name}'！相似度: {final_conf:.4f}，相對亮度比: {final_ratio:.2f}，座標: ({center_x}, {center_y})")
        return (center_x, center_y), final_conf

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
