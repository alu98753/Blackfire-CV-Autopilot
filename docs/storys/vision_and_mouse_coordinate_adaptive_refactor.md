# PARS 開發故事：視窗 Client 座標點擊體系與動態自適應螢幕縮放比對重構 🎯

- **建立時間**: 2026-08-27
- **影響範圍**: `capture/screen.py`, `actions/mouse.py`, `vision/matcher.py`, `main.py`, `tools/test_single_click.py`

---

## 1. Purpose (開發目的)
在多螢幕（插外接螢幕線）與單筆電螢幕（拔線）之間切換時，遭遇兩大核心阻礙：
1. **點擊座標偏差**：Windows 視窗最大化外框（8px 隱形邊界）造成二次扣減或疊加，使後台 `PostMessage` 與前台滑鼠點擊偏移。
2. **圖像辨識失真**：多螢幕跨 DPI 虛擬化下截圖解析度變為 1536px (0.8x)，而單螢幕為 1920px (1.0x)，舊有代碼硬編碼縮放比導致其中一種螢幕環境比對失敗。

---

## 2. Action (具體行動)
1. **統一 Client 座標體系**：
   - `capture/screen.py` 全面改用 `win32gui.GetClientRect` 與 `ClientToScreen` 獲取純淨 Client 區域。
   - `actions/mouse.py` 後台模式直接依據 Client 座標打包 `MAKELONG(cx, cy)` 發送 `PostMessage`；前台模式透過 `ClientToScreen` 精確轉換。
2. **實裝動態自適應縮放 (Auto-Adaptive Scale)**：
   - `vision/matcher.py` 的 `TemplateMatcher` 支援動態感知畫面寬度：
     $$\text{scale} = \frac{\text{screen\_w}}{1920.0} \quad (\text{當 } \text{screen\_w} \ge 1200)$$
   - 建立 `_cached_templates[(template_name, scale)]` 多尺度快取機制。
3. **診斷工具與測試架構**：
   - 建立 `tools/test_single_click.py`，支援 3 秒倒數、單圖/多尺度比對、實體點擊與全場景診斷。
   - 在 `tests/test_vision_matcher.py` 與 `tests/test_mouse_coordinates.py` 補齊全方位單元測試。

---

## 3. Result (成果)
- **100% 滿分比對**：單螢幕 (1920p) 與多螢幕 (1536p) 下 `door.png` 與 `diamond.png` 信心度均達 **1.0000** 與 **0.9999**。
- **全套測試零 Regression**：全套 466 個單元測試綠燈通過。
- **雙螢幕無縫熱插拔**：無論接線或拔線，系統均能自動秒速對齊。

---

## 4. So What (架構價值)
徹底解除了腳本對特定硬體螢幕設定與 DPI 縮放的強耦合，使點擊控制器與視覺引擎具備跨解析度、跨顯示器的通用適應能力。

---

## 5. Influence (後續維護指引)
- 後續新增模板時，統一使用 1080p (寬度 1920) 原生尺寸截圖即可，無需手動縮放。
- 後台點擊一律以 Client 座標系為基準，禁止在 Handler 中自行二次增減 Windows 邊框。
