import cv2
import os
import logging
import numpy as np

BASE_RESOLUTION_WIDTH = 1920.0
MIN_AUTO_SCALE_WIDTH = 1200

# 預設多尺度掃描比例清單：
# - 1.000: 原生 1920x1080 (1080p) 設計基準
# - 0.863: 常見 1656x931 縮放視窗比例 (~1656/1920 ≈ 0.8625)
# - 0.750: 常見 1440x810 縮放視窗比例 (1440/1920 = 0.7500)
DEFAULT_MATCH_SCALES = (1.0, 0.863, 0.75)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class TemplateMatcher:
    def __init__(self, templates_dir="templates", template_scale=1.0, auto_scale=True):
        self.templates_dir = templates_dir
        self.template_scale = template_scale
        self.auto_scale = auto_scale
        self._raw_templates = {}
        self._cached_templates = {}

    def _compute_auto_scale(self, screen_width):
        """依目前畫面寬度計算模板自動縮放比例。"""
        if self.auto_scale and screen_width >= MIN_AUTO_SCALE_WIDTH:
            return screen_width / BASE_RESOLUTION_WIDTH
        return self.template_scale

    def _nms(self, raw_candidates, min_dist_x: int, min_dist_y: int):
        """
        Non-Maximum Suppression：從按信心度由高到低排序的候選點中，
        逐一收錄，跳過與已收錄點距離均在 (min_dist_x, min_dist_y) 以內的重疊候選點。

        :param raw_candidates: [(x, y, conf), ...] 已按 conf 由高到低排序
        :param min_dist_x: X 軸方向最小距離（通常為 temp_w // 2）
        :param min_dist_y: Y 軸方向最小距離（通常為 temp_h // 2）
        :return: 抑制後的代表點清單 [(x, y, conf), ...]
        """
        candidates = []
        for x, y, conf in raw_candidates:
            if not any(abs(x - cx) < min_dist_x and abs(y - cy) < min_dist_y
                       for cx, cy, _ in candidates):
                candidates.append((x, y, conf))
        return candidates

    def _pyramid_precheck(self, screen_img, template_img, threshold):
        """
        快速金字塔下採樣初步篩選（Image Pyramids Acceleration）。
        對大尺寸畫面（>= 720p）且足夠大的模板（>= 50x50），先以 1/2 縮放圖進行極速預檢，
        避免在顯然無法匹配的畫面上執行耗時的全解析度比對。

        :return: (passed: bool, max_val: float)
                 passed=True  → 允許繼續全解析度比對
                 passed=False → 預檢信心度太低，可直接提早回傳
        """
        screen_h, screen_w = screen_img.shape[:2]
        temp_h, temp_w = template_img.shape[:2]

        if screen_h >= 720 and temp_h >= 50 and temp_w >= 50:
            small_screen = cv2.resize(screen_img, (screen_w // 2, screen_h // 2), interpolation=cv2.INTER_AREA)
            small_temp = cv2.resize(template_img, (max(1, temp_w // 2), max(1, temp_h // 2)), interpolation=cv2.INTER_AREA)
            res_small = cv2.matchTemplate(small_screen, small_temp, cv2.TM_CCOEFF_NORMED)
            _, max_val_small, _, _ = cv2.minMaxLoc(res_small)
            if max_val_small < threshold - 0.10:
                return False, max_val_small

        return True, None

    def _apply_brightness_filter(self, candidates, screen_gray, template_gray,
                                 temp_h, temp_w, brightness_threshold, template_name=""):
        """
        計算每個候選點的相對亮度比，並在啟用 brightness_threshold 時過濾暗區候選點。

        :param candidates: [(x, y, conf), ...] 已通過 NMS 的候選點
        :param screen_gray: 灰階畫面
        :param template_gray: 灰階模板
        :param temp_h: 模板高度
        :param temp_w: 模板寬度
        :param brightness_threshold: > 0 時啟用亮度過濾
        :param template_name: 模板名稱（供日誌使用）
        :return: (best_x, best_y, best_conf, best_ratio) 最優候選點，
                 若所有候選點亮度均不足，回傳 None。
        """
        mean_temp = np.mean(template_gray)
        evaluated = []
        for x, y, conf in candidates:
            crop = screen_gray[y:y + temp_h, x:x + temp_w]
            mean_crop = np.mean(crop)
            ratio = mean_crop / max(1.0, mean_temp)
            evaluated.append((x, y, conf, ratio))

        if brightness_threshold > 0.0:
            passed = [c for c in evaluated if c[3] >= brightness_threshold]
            if not passed:
                best_raw = max(evaluated, key=lambda c: c[2])
                try:
                    from scripts.analyze_template_brightness import save_diagnostic_images
                    save_diagnostic_images(
                        screen_gray, template_gray, (best_raw[0], best_raw[1]),
                        temp_w, temp_h, best_raw[2], best_raw[3], template_name
                    )
                except Exception as e:
                    logging.error(f"無法調用 scripts/save_diagnostic_images: {e}")
                logging.warning(
                    f"⚠️ 模板 '{template_name}' 匹配到 {len(candidates)} 個候選點，"
                    f"但所有點的亮度比例均低於門檻 {brightness_threshold:.2f}，判定為背景暗區按鈕，予以過濾！"
                )
                return None
            return max(passed, key=lambda c: c[2])

        return max(evaluated, key=lambda c: c[2])

    def _load_template(self, template_name, scale=1.0):
        """
        延遲載入並快取模板圖片，支援依據 scale 多尺度快取。
        """
        scale_key = round(float(scale), 4)
        cache_key = (template_name, scale_key)
        if cache_key in self._cached_templates:
            return self._cached_templates[cache_key]

        # 1. 取得原始 1.0 模板原圖
        if template_name in self._raw_templates:
            raw_img = self._raw_templates[template_name]
        else:
            if os.path.isabs(template_name) or template_name.startswith("."):
                path = os.path.normpath(template_name)
            else:
                path = os.path.normpath(os.path.join(self.templates_dir, template_name))

            if not os.path.exists(path):
                logging.error(f"找不到模板圖片檔案: {path}")
                return None

            raw_img = cv2.imread(path)
            if raw_img is None:
                logging.error(f"無法解析/讀取圖片: {path}")
                return None
            self._raw_templates[template_name] = raw_img

        # 2. 縮放處理
        if abs(scale_key - 1.0) < 1e-4:
            template_img = raw_img
        else:
            h, w = raw_img.shape[:2]
            nw = max(1, int(round(w * scale_key)))
            nh = max(1, int(round(h * scale_key)))
            template_img = cv2.resize(
                raw_img, 
                (nw, nh), 
                interpolation=cv2.INTER_AREA if scale_key < 1.0 else cv2.INTER_LINEAR
            )

        self._cached_templates[cache_key] = template_img
        return template_img

    def match_mutually_exclusive_tabs(self, screen_img, template_a, template_b, margin=0.02, threshold=0.70):
        """
        對比兩個互斥 UI 頁籤/按鈕的相對匹配度，回傳 (is_a_active, is_b_active, conf_a, conf_b)。
        """
        res_a = self.match(screen_img, template_a, threshold)
        res_b = self.match(screen_img, template_b, threshold)

        c_a = res_a[1] if (isinstance(res_a, (tuple, list)) and len(res_a) >= 2 and res_a[1] is not None) else 0.0
        c_b = res_b[1] if (isinstance(res_b, (tuple, list)) and len(res_b) >= 2 and res_b[1] is not None) else 0.0
        
        is_a_active = (c_a >= threshold and c_a > c_b + margin)
        is_b_active = (c_b >= threshold and c_b > c_a + margin)
        return is_a_active, is_b_active, c_a, c_b

    def match(self, screen_img, template_name, threshold=0.8, brightness_threshold=0.0, quiet=False, scale=None):
        """
        在 screen_img 中尋找與 template_name 匹配度最高的位置。
        支援 auto_scale 自動依據畫面解析度換算縮放因子。
        
        :param screen_img: 來源畫面 (numpy array)
        :param template_name: 模板檔名或路徑
        :param threshold: 信心度閥值 (0.0 ~ 1.0)
        :param brightness_threshold: 亮度比例門檻 (0.0代表不啟用，大於0代表低於此比例則過濾，並進行最亮點選擇)
        :param scale: 指定縮放比例 (若為 None 且 auto_scale=True 則自動以 screen_width / 1920 計算)
        :return: (center_x, center_y), confidence. 若未達閥值，回傳 None, confidence
        """
        if screen_img is None:
            return None, 0.0

        # 1. Scale 計算
        if scale is None:
            screen_w = screen_img.shape[1] if hasattr(screen_img, "shape") and len(screen_img.shape) >= 2 else 0
            scale = self._compute_auto_scale(screen_w)

        template_img = self._load_template(template_name, scale=scale)
        if template_img is None:
            return None, 0.0

        screen_h, screen_w = screen_img.shape[:2]
        temp_h, temp_w = template_img.shape[:2]

        # 如果模板比來源畫面大，必無法匹配，直接回傳 None 以免 OpenCV 崩潰
        if temp_h > screen_h or temp_w > screen_w:
            if not quiet:
                logging.warning(f"模板尺寸 ({temp_w}x{temp_h}) 大於來源畫面尺寸 ({screen_w}x{screen_h})。")
            return None, 0.0

        # 2. 金字塔預檢（快速排除）
        passed, precheck_val = self._pyramid_precheck(screen_img, template_img, threshold)
        if not passed:
            return None, precheck_val

        # 3. 主比對 + NMS 聚類抑制
        # NMS 半徑與模板尺寸對齊（temp_w // 2, temp_h // 2），確保和 match_all() 一致。
        # 舊版使用固定 20px，對小模板（< 40px）抑制半徑過大，可能誤合併相鄰的獨立目標。
        res = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        pts = list(zip(*loc[::-1]))
        raw_candidates = [(pt[0], pt[1], res[pt[1], pt[0]]) for pt in pts]
        raw_candidates.sort(key=lambda x: x[2], reverse=True)
        candidates = self._nms(raw_candidates, min_dist_x=temp_w // 2, min_dist_y=temp_h // 2)

        if not candidates:
            _, max_val, _, _ = cv2.minMaxLoc(res)
            return None, max_val

        # 4. 亮度過濾與最優點選取
        temp_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
        best_selected = self._apply_brightness_filter(
            candidates, screen_gray, temp_gray,
            temp_h=temp_h, temp_w=temp_w,
            brightness_threshold=brightness_threshold,
            template_name=template_name,
        )

        if best_selected is None:
            return None, max(candidates, key=lambda c: c[2])[2]

        # 5. 回傳最優點的中心座標與相似度
        final_x, final_y, final_conf, final_ratio = best_selected
        center_x = final_x + temp_w // 2
        center_y = final_y + temp_h // 2

        if not quiet:
            logging.info(f"成功匹配模板 '{template_name}'！相似度: {final_conf:.4f}，相對亮度比: {final_ratio:.2f}，座標: ({center_x}, {center_y})")
        return (center_x, center_y), final_conf

    def match_all(self, screen_img, template_name, threshold=0.7, scales=None, brightness_threshold=0.0, quiet=False):
        """
        在 screen_img 中尋找所有與 template_name 匹配度高於 threshold 的位置 (支援自適應多尺度測試與相對亮度比過濾)。
        :return: [(center_x, center_y, confidence), ...]
        """
        base_template = self._load_template(template_name, scale=1.0)
        if base_template is None or screen_img is None:
            return []

        screen_h, screen_w = screen_img.shape[:2]
        auto_factor = self._compute_auto_scale(screen_w)
        base_scales = scales or DEFAULT_MATCH_SCALES
        scales_to_try = [round(s * auto_factor, 4) for s in base_scales]

        for s in scales_to_try:
            template_img = self._load_template(template_name, scale=s)
            if template_img is None:
                continue

            temp_h, temp_w = template_img.shape[:2]
            if temp_h > screen_h or temp_w > screen_w:
                continue

            res = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= threshold)
            pts = list(zip(*loc[::-1]))
            if not pts:
                continue

            raw_candidates = [(pt[0], pt[1], float(res[pt[1], pt[0]])) for pt in pts]
            raw_candidates.sort(key=lambda x: x[2], reverse=True)

            candidates = self._nms(raw_candidates, min_dist_x=temp_w // 2, min_dist_y=temp_h // 2)

            # 相對亮度比例過濾 (Relative Brightness Ratio Filter)
            if brightness_threshold > 0.0 and candidates:
                temp_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
                mean_temp = np.mean(temp_gray)
                screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)

                filtered_candidates = []
                for x, y, conf in candidates:
                    crop = screen_gray[y:y+temp_h, x:x+temp_w]
                    mean_crop = np.mean(crop)
                    ratio = mean_crop / max(1.0, mean_temp)
                    if ratio >= brightness_threshold:
                        filtered_candidates.append((x, y, conf))
                    elif not quiet:
                        logging.warning(f"⚠️ [match_all] 模板 '{template_name}' 在 ({x}, {y}) 相似度 {conf:.4f} 達標，但亮度比 {ratio:.2f} < 門檻 {brightness_threshold:.2f}，予以過濾。")
                candidates = filtered_candidates

            results = []
            for x, y, conf in candidates:
                center_x = x + temp_w // 2
                center_y = y + temp_h // 2
                results.append((center_x, center_y, conf))

            if results:
                if not quiet:
                    logging.info(f"🔍 [match_all] 在 Scale={s:.3f} 找到 {len(results)} 個模板 [{template_name}] 匹配項 (threshold={threshold})")
                return results

        return []

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
