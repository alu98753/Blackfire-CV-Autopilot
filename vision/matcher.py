import cv2
import os
import logging
import numpy as np

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

    def match(self, screen_img, template_name, threshold=0.8, brightness_threshold=0.0):
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

        # 動態獲取遊戲視窗的 DPI 縮放因子，自適應拉伸/縮小模板圖片
        dpi_factor = 1.0
        try:
            import win32gui
            import ctypes
            hwnd = win32gui.FindWindow(None, "Blackfire Crusade")
            if hwnd:
                dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
                dpi_factor = dpi / 96.0
        except Exception:
            pass
            
        if abs(dpi_factor - 1.0) > 0.01:
            try:
                new_w = int(template_img.shape[1] * dpi_factor)
                new_h = int(template_img.shape[0] * dpi_factor)
                template_img = cv2.resize(template_img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            except Exception as e_resize:
                logging.debug(f"自適應 DPI 縮放模板失敗: {e_resize}")

        screen_h, screen_w = screen_img.shape[:2]
        temp_h, temp_w = template_img.shape[:2]

        # 如果模板比來源畫面大，必無法匹配
        if temp_h > screen_h or temp_w > screen_w:
            logging.warning(f"模板尺寸 ({temp_w}x{temp_h}) 大於來源畫面尺寸 ({screen_w}x{screen_h})。")
            return None, 0.0

        # 使用標準化相關係數配對方法
        res = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
        
        # 1. 找出所有相似度大於等於門檻的候選點
        loc = np.where(res >= threshold)
        candidates = []
        for pt in zip(*loc[::-1]):
            # 進行簡單的聚類抑制，避免重疊框
            too_close = False
            for cx, cy, c_conf in candidates:
                if abs(pt[0] - cx) < 20 and abs(pt[1] - cy) < 20:
                    too_close = True
                    break
            if not too_close:
                conf = res[pt[1], pt[0]]
                candidates.append((pt[0], pt[1], conf))

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
            
            # (b) 局部亮度最大化排序：從合格的候選點中，只選擇亮度比例最高的那一個
            best_selected = max(passed, key=lambda c: c[3])
        else:
            # 若未啟用亮度檢查，直接抓取相似度最高的點
            best_selected = max(evaluated_candidates, key=lambda c: c[2])

        # 4. 回傳最優點的中心座標與相似度
        final_x, final_y, final_conf, final_ratio = best_selected
        center_x = final_x + temp_w // 2
        center_y = final_y + temp_h // 2

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
