import os
import cv2
import logging
from utils.quest_mapper import QuestMapper

class QuestOCRExtractor:
    """
    懸賞告示牌標題極速擷取器：
    1. 使用 match_all 在告示牌畫面中比對圖示錨點 (town_building/bulletin_board/task.png)。
    2. 按 Y 座標由小到大排序 (從第一條任務到最下條任務)。
    3. 對每個圖示錨點向右裁切文字區域 ROI (x + icon_w + 5, y, text_width=360, text_height=40)。
    4. 丟給 EasyOCR 辨識，提取出乾淨的標題字串。
    5. 用逗號串接字串，傳給 QuestMapper.parse_quests_to_schedule(...) 產生排程。
    """
    def __init__(self, matcher=None, ocr_reader=None):
        self.matcher = matcher
        self.ocr_reader = ocr_reader

    def extract_quest_names(self, screen_img, template_name="town_building/bulletin_board/task.png", threshold=0.70):
        """
        對截圖進行圖示錨點定位與右側文字辨識，回傳 (task_names_list, comma_separated_string)。
        """
        if screen_img is None or self.matcher is None:
            return [], ""

        # 1. 尋找畫面中所有 task.png 錨點
        anchors = self.matcher.match_all(screen_img, template_name, threshold=threshold, quiet=True)
        if not anchors:
            logging.warning("⚠️ [QuestOCRExtractor] 未在畫面中辨識到任何懸賞任務標籤 (task.png) 錨點！")
            return [], ""

        h_img, w_img = screen_img.shape[:2]

        # 專精優化：過濾只保留螢幕左半邊 (cx < w_img // 2) 的 task.png 錨點，並透過相對優勢過濾 task_after.png
        task_after_tpl = "town_building/bulletin_board/task_after.png"
        filtered_anchors = []
        for (cx, cy, conf_b) in anchors:
            if cx >= w_img // 2:
                continue
            x1 = max(0, cx - 60)
            x2 = min(w_img, cx + 60)
            y1 = max(0, cy - 60)
            y2 = min(h_img, cy + 60)
            roi = screen_img[y1:y2, x1:x2]
            pos_a, conf_a = self.matcher.match(roi, task_after_tpl, threshold=0.65, quiet=True)
            if pos_a and conf_a >= conf_b - 0.02:
                # 已接取
                continue
            filtered_anchors.append((cx, cy, conf_b))

        anchors = filtered_anchors
        if not anchors:
            logging.warning("⚠️ [QuestOCRExtractor] 左半邊未找到任何未接取的 task.png 錨點 (全數為已接取 task_after.png)！")
            return [], ""

        # 按 Y 座標排序 (自上而下)
        anchors = sorted(anchors, key=lambda a: a[1])

        # 取得模板實際大小與縮放比
        temp_img = self.matcher._load_template(template_name)
        temp_h, temp_w = (temp_img.shape[0], temp_img.shape[1]) if temp_img is not None else (40, 40)
        
        scale = getattr(self.matcher, "template_scale", 1.0)
        if scale == 1.0 and w_img < 1500:
            scale = w_img / 1940.0

        icon_w = max(20, int(temp_w * scale))
        icon_h = max(20, int(temp_h * scale))

        extracted_names = []

        for idx, (cx, cy, conf) in enumerate(anchors):
            # 左上角座標
            x0 = cx - icon_w // 2
            y0 = cy - icon_h // 2

            from config import BULLETIN_BOARD_OCR_OFFSET
            off_x = BULLETIN_BOARD_OCR_OFFSET.get("offset_x", 5)
            off_y = BULLETIN_BOARD_OCR_OFFSET.get("offset_y", -5)
            box_w = BULLETIN_BOARD_OCR_OFFSET.get("box_width", 360)
            box_h = BULLETIN_BOARD_OCR_OFFSET.get("box_height", 40)

            # 計算右側文字 ROI 範圍 (相對於卷軸圖示右上角)
            crop_x = max(0, x0 + icon_w + int(off_x * scale))
            crop_y = max(0, y0 + int(off_y * scale))
            crop_w = min(max(20, int(box_w * scale)), w_img - crop_x)
            crop_h = min(max(10, int(box_h * scale)), h_img - crop_y)

            if crop_w <= 0 or crop_h <= 0:
                continue

            text_roi = screen_img[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]


            # 進行 OCR 辨識
            name = self._ocr_crop(text_roi, crop_top_half=True)

            if name:
                logging.info(f"📋 [QuestOCRExtractor] 任務列 #{idx+1} (Y={cy}) 辨識出標題: '{name}' (錨點信心度: {conf:.4f})")
                extracted_names.append(name)

        comma_str = ", ".join(extracted_names)
        return extracted_names, comma_str

    def _ocr_crop(self, text_roi, crop_top_half=False):
        if self.ocr_reader is None:
            try:
                import easyocr
                self.ocr_reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)
            except Exception as e:
                logging.error(f"無法載入 EasyOCR: {e}")
                return ""

        try:
            h, w = text_roi.shape[:2]
            # 僅在顯式指定 crop_top_half=True 時二次切除上半部
            target_img = text_roi[:int(h * 0.55), :] if (crop_top_half and h > 30) else text_roi
            # 放大 2 倍以提升中文字元特徵清晰度
            scaled = cv2.resize(target_img, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)


            results = self.ocr_reader.readtext(scaled)
            if results:
                texts = []
                for res in results:
                    txt = res[1].strip()
                    # 過濾純單個符號如 ")", "!", "!" 等雜訊
                    if len(txt) == 1 and not ('\u4e00' <= txt <= '\u9fff' or txt.isalnum()):
                        continue
                    texts.append(txt)
                final_str = "".join(texts).strip()
                # 剔除首尾英數雜訊標點
                import re
                final_str = re.sub(r'^[^\w\u4e00-\u9fff]+|[^\w\u4e00-\u9fff]+$', '', final_str)
                return final_str
        except Exception as e:
            logging.error(f"OCR 辨識異常: {e}")
        return ""

    def extract_and_schedule(self, screen_img, template_name="town_building/bulletin_board/task.png", threshold=0.70):
        """
        一鍵提取標題並產生 TaskNode 動態排程佇列。
        """
        names, comma_str = self.extract_quest_names(screen_img, template_name, threshold)
        if not names:
            return []

        mapper = QuestMapper()
        task_nodes = []
        for name in names:
            node = mapper.parse_quest(title=name)
            if node:
                task_nodes.append(node)

        return task_nodes
