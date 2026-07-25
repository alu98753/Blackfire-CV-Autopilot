---
name: card_cooldown_ocr
description: 通用卡片冷卻木牌比對與 OCR 時間辨識模組開發與維護技能 (適用於 首領討伐 lord_boss、地下城關卡卡片等)
---

# 卡片冷卻木牌比對與 OCR 模組規範 (Card Cooldown Sign & Scoped OCR Skill) 🛡️

本技能定義本專案中所有卡片（如首領領主、地下城關卡、告示牌等）在進行冷卻木牌辨識、解析度縮放與 OCR 解析時的標準架構與開發規範。

---

## 🎯 核心原則

### 1. 單張卡片精確切割 (Scoped Card Crop Only)
- **原則**：**絕對禁止拿木牌模板（如 `cooldown_left.png` / `cooldown_right.png`）對整張螢幕 `screen_img` 進行全域比對**。
- **原因**：全畫面比對極易抓到介面其他角落或非目標卡片的木牌特徵，造成嚴重誤判。
- **作法**：
  1. 透過卡片範本（如 `lord_spider.png` / `lord_spectre.png`）匹配卡片中心 `(cx, cy)`。
  2. 依單張卡片尺寸切出 `card_crop = screen_img[y1:y2, x1:x2]`。
  3. **僅在 `card_crop` 內部**進行木牌比對與 OCR。

### 2. 解析度等比例縮放 (Scale Adaptation)
- **原則**：當視窗尺寸發生變化時，範本寬高需依據基準解析度（預設 `1920x1080`）進行縮放：
  ```python
  scale_x = w / 1920.0
  scale_y = h / 1080.0
  t_w = int(t_base_w * scale_x)
  t_h = int(t_base_h * scale_y)
  ```
- 裁切邊界 `x1, x2, y1, y2` 必須依此動態計算，確保無論視窗被縮放至何種大小均能精確命中卡片。

### 3. 無木牌即挑戰，有木牌才 OCR (Sign Logic)
- **無木牌 (`cooldown_left.png` / `cooldown_right.png` 全未匹配)** ➔ 代表卡片可打，無冷卻，直接進入挑戰點擊。
- **有木牌 (匹配到 `cooldown_left.png` 或 `cooldown_right.png`)** ➔ 代表正在冷卻中，截取木牌上方數字區域送入 OCR，解析剩餘冷卻秒數並寫入 `DailyManager`。

---

## 📌 程式碼標準參考 (Reference Implementation)
參見 [lord_boss.py: Line 225](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/lord_boss.py#L225) 的 `_check_card_cooldown_ocr` 函式實作。
