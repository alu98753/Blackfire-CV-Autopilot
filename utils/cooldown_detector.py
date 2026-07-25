import os
import cv2
import logging
from utils.time_parser import parse_time_to_seconds

def detect_cooldown_sign_and_time(crop_img, ocr_reader, max_allowed_seconds=7200.0, threshold=0.58, scale=1.0):
    """
    [ Clean Code 重用模組 ]
    在傳入的卡片/選單圖像中優先比對冷卻木牌範本 (cooldown_left.png / cooldown_right.png)。
    - 若無冷卻木牌 (max_val_cd < threshold)：回傳 (False, None, None)，零 OCR 開銷。
    - 若發現冷卻木牌：對木牌區域進行文字切割、補邊與 4 倍放大預處理，呼叫 EasyOCR 讀取倒數時間。
      嚴格驗證 (0 < parsed_secs <= max_allowed_seconds)，避免花紋雜訊誤讀。
      回傳 (True, parsed_secs, raw_text)。
    """
    if crop_img is None or crop_img.size == 0:
        return False, None, None

    has_cooldown = False
    matched_sign = None
    max_loc_cd = None
    cd_w = 0
    cd_h = 0

    for cd_temp in ["dungeons/cooldown_left.png", "dungeons/cooldown_right.png"]:
        template_path = os.path.join("templates", cd_temp)
        if os.path.exists(template_path):
            cd_img = cv2.imread(template_path)
            if cd_img is not None:
                cur_w = max(5, int(cd_img.shape[1] * scale))
                cur_h = max(5, int(cd_img.shape[0] * scale))
                resized_cd = cv2.resize(cd_img, (cur_w, cur_h))
                
                if crop_img.shape[0] >= cur_h and crop_img.shape[1] >= cur_w:
                    res_cd = cv2.matchTemplate(crop_img, resized_cd, cv2.TM_CCOEFF_NORMED)
                    _, max_val_cd, _, loc = cv2.minMaxLoc(res_cd)
                    if max_val_cd >= threshold:
                        has_cooldown = True
                        matched_sign = cd_temp
                        max_loc_cd = loc
                        cd_w = cur_w
                        cd_h = cur_h
                        break

    if not has_cooldown:
        return False, None, None

    # 已成功比對到冷卻木牌！進行文字區域切割、4倍放大與 EasyOCR 讀取
    try:
        cd_cx = max_loc_cd[0] + cd_w // 2
        cd_cy = max_loc_cd[1] + cd_h // 2

        if "left" in matched_sign:
            tx1 = max(0, cd_cx - 60)
            tx2 = min(crop_img.shape[1], cd_cx + 110)
        else:
            tx1 = max(0, cd_cx - 110)
            tx2 = min(crop_img.shape[1], cd_cx + 60)

        ty1 = max(0, cd_cy - 18)
        ty2 = min(crop_img.shape[0], cd_cy + 12)

        time_crop = crop_img[ty1:ty2, tx1:tx2]
        if time_crop.size > 0:
            time_gray = cv2.cvtColor(time_crop, cv2.COLOR_BGR2GRAY)
            padded = cv2.copyMakeBorder(time_gray, 15, 15, 30, 30, cv2.BORDER_CONSTANT, value=159)
            resized_text = cv2.resize(padded, (0, 0), fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

            if ocr_reader:
                ocr_results = ocr_reader.readtext(resized_text, allowlist="0123456789:")
                for item in ocr_results:
                    raw_text = item[1]
                    parsed_secs = parse_time_to_seconds(raw_text)
                    if parsed_secs is not None and 0 < parsed_secs <= max_allowed_seconds:
                        return True, parsed_secs, raw_text

                # 若木牌存在但 OCR 未能成功驗證出合法範圍時間，傳回木牌圖示預設上限
                if ocr_results and len(ocr_results) > 0:
                    raw_text = ocr_results[0][1]
                    return True, max_allowed_seconds, raw_text

        return True, max_allowed_seconds, "冷卻木牌"
    except Exception as e:
        logging.warning(f"⚠️ [CooldownDetector] 木牌文字區域 OCR 讀取異常: {e}")
        return True, max_allowed_seconds, "冷卻木牌"
