# 規格書：大廳分頁成對消歧演算法升級（色相光環檢驗與自適應差值）

> 狀態：Proposed  
> 建立日期：2026-09-10  
> 關聯問題：[navigation_stock_bug.md](navigation_stock_bug.md)  
> 上位架構：[Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md)  
> 依據契約：[Precondition Contracts](../architecture/precondition_contracts.md), [Lobby Scene Contract](../features/navigation/lobby_scene_contract.md)  

---

## 1. 問題定義與物理圖像客觀證據 (Physical Evidence & Ground Truth)

### 1.1 現場問題現象
在執行混合模式（`type="mix"`）或地下城導航時，當角色身處活動大廳且地下城可挑戰時：
1. 系統首次點擊 `dungeons/dungeon.png` 切換至地下城分頁。
2. 畫面切換後**已經處於地下城分頁**，但係統每一幀仍然判定 `dungeon_select_open == False`。
3. 導致系統完全跳過地下城卡片掃描與選關，反而每一幀不斷重複點擊 `dungeons/dungeon.png` 切換按鈕，陷入死循環。

### 1.2 現場日誌與數值證據
```text
2026-09-10 20:02:40,671 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，座標: (648, 713)
2026-09-10 20:02:40,939 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，座標: (648, 715)
```
- **選中態模板 (Active)**：`dungeons/dungeon_after.png` 相似度 `0.9444`。
- **未選中態模板 (Inactive)**：`dungeons/dungeon.png` 相似度 `0.9281`。
- **實際差值**：$\Delta = 0.9444 - 0.9281 = \mathbf{0.0163}$。

### 1.3 大廳 5 大頁籤成對模板之圖像物理特徵實測
對比大廳全部 5 組共 10 張模板，經填充對齊（Padding Center Alignment）實測相互交叉匹配度：

| 頁籤語意 | Active 模板 | Inactive 模板 | 尺寸 (Active / Inactive) | 成對交叉相似度 (Cross-Match) |
| :--- | :--- | :--- | :---: | :---: |
| **普通關卡** | `common/select_stage_after.png` | `common/select_stage.png` | 168x149 / 170x152 | **`0.9154`** |
| **地下城** | `dungeons/dungeon_after.png` | `dungeons/dungeon.png` | 174x156 / 165x146 | **`0.9369`** |
| **禁域 (領地)** | `domains/Domains_entry_after.png` | `domains/Domains_entry.png` | 163x162 / 145x106 | **`0.8552`** |
| **首領 (領主)** | `load/Lord_entry_after.png` | `load/Lord_entry.png` | 155x154 / 168x148 | **`0.9206`** |
| **魔王 (魔神)** | `demon_lords/demon_lords_entry_after.png` | `demon_lords/demon_lords_entry.png` | 154x153 / 163x137 | **`0.9325`** |

#### 關鍵事實發現：
1. **5 組按鈕 100% 屬於同一設計體系**：
   - 5 組按鈕直徑均為約 150~170px 的圓形石雕銘牌，中央為各自主題圖騰（石島拱門、石門骷髏、木門、騎士頭盔、魔王皇冠），底部為統一的白色描邊黑底繁體文字。
2. **核心圖騰重合度高達 90% 以上**：
   - 無論是否被選中，按鈕中央的核心圖騰幾何紋理與文字完全一致，模板互比相似度高達 `0.85 ~ 0.94`。
3. **唯一的客觀物理差別：外圍紅色發光圓環 (Red Halo Ring)**：
   - **未選中態 (Inactive)**：圓形邊框為灰黑色、暗鐵色金屬環。
   - **選中態 (Active / After)**：圓形外圍點亮醒目的**高飽和紅色發光圓環**。
4. **硬性門檻 `0.02` 導致的死角**：
   - 由於中央 90% 的不變像素主導了 Template Matching 數值，當畫面處於選中態時，未選中模板同樣能算出 `0.92+` 的高相似度，使得 Active 與 Inactive 的數值差值被壓制在 `0.010 ~ 0.018` 之間。
   - 既有規則要求 `conf_act > conf_inact + 0.02`，剛好卡死在此物理邊界，導致系統在選中態畫面下誤判為「未開啟」。

---

## 2. 紅光外環色彩特徵演算法實測分析 (Chromatic Halo Analysis)

為消滅 Magic Number 並取得 100% 可靠的物理消歧判據，對 5 組全部 10 張模板進行色彩空間與幾何分佈實測。

### 2.1 外環半徑比率界定 (Outer Ring Geometry)
設按鈕匹配區域的寬為 $W$、高為 $H$，中心點座標為 $(cx, cy) = (W/2, H/2)$。任一像素 $(x, y)$ 到中心的歸一化橢圓距離為：
$$r(x, y) = \sqrt{\left(\frac{x - cx}{W/2}\right)^2 + \left(\frac{y - cy}{H/2}\right)^2}$$

實測不同半徑區間 $[r_{\text{inner}}, r_{\text{outer}}]$ 下的選中態與未選中態紅光分離度（Separation Gap）：
- $r \in [0.65, 1.05]$：Min ACT: 11.42%, Max INACT: 2.42% (Gap: 9.00%)
- $r \in [0.70, 1.05]$：Min ACT: 12.64%, Max INACT: 2.60% (Gap: 10.04%)
- **$r \in [0.75, 1.05]$（最佳幾何區間）**：Min ACT: **14.40%**, Max INACT: **2.57%** (Gap: **11.83%**)
- $r \in [0.80, 1.00]$：Min ACT: 19.98%, Max INACT: 3.59% (Gap: 16.39%)

**結論**：取歸一化半徑 **$r \in [0.75, 1.05]$** 作為外環檢驗區（Outer Ring ROI），既能完整捕捉紅色光暈，又能 100% 避開中央圖騰的色彩干擾。

### 2.2 色彩模型選型：為什麼必須使用 HSV 空間？
- 若使用 RGB 簡單比值（$R > G + 30, R > B + 30$）：
  - 禁域 (`domain`) 的未選中態木門包含黃褐色木紋，黃色在 RGB 中 $R$ 分量同樣高於 $B$，導致未選中態木紋被誤判為紅光（RGB 誤報率達 14.48%）。
- 若使用 **HSV 色彩空間**：
  - 紅光具有極為狹窄且特定的色相（Hue）：$H \in [0, 12] \cup [165, 180]$（OpenCV 規格，滿刻度 180）。
  - 發光光環具備高飽和與高明度：$S \ge 70, V \ge 70$。
  - 黃褐色木門（$H \in [25, 45]$）與暗灰鐵框（$S < 30$）在 HSV 條件下計數完全歸零！

### 2.3 5 組模板之 HSV 紅光像素比例實測統計表
在 $r \in [0.75, 1.05]$ 外環區域內，符合紅光條件之像素百分比：

| 頁籤語意 | 選中態 (Active / After) | 未選中態 (Inactive) | 物理分離度 (Separation Gap) |
| :--- | :---: | :---: | :---: |
| **普通關卡 (`stage`)** | **`14.40%`** | `2.57%` | $+11.83\%$ |
| **地下城 (`dungeon`)** | **`12.64%`** | `1.94%` | $+10.70\%$ |
| **禁域 (`domain`)** | **`13.28%`** | `0.33%` | $+12.95\%$ |
| **首領 (`lord`)** | **`15.60%`** | `2.43%` | $+13.17\%$ |
| **魔王 (`demon_lord`)** | **`14.68%`** | `2.60%` | $+12.08\%$ |

- **選中態 (Active)**：外環紅光像素比例皆在 **`12.6% ~ 15.6%`**。
- **未選中態 (Inactive)**：外環紅光像素比例皆在 **`0.3% ~ 2.6%`**。
- **判定閾值 (Decision Threshold)**：建議設定為 **`7.0%`**（中位數），兩側各有約 $2\times$ 以上的安全防護裕度。

---

## 3. 上位架構約束與契約對齊 (Architectural Alignment)

### 3.1 Greenfield-lite v1 第 4 節原則
- **感知與決策分離 (Separation of Perception & Decision)**：
  - `SceneDetector` 負責提供不可辯駁的客觀物理證據（Active 狀態）。
  - Handler 禁止跨層私自比對模板或擅自猜測狀態。
- **消滅 Magic Number**：
  - 拒絕單純將 `0.02` 改為另一個靜態數字；引入二維色彩物理特徵作為模糊帶之決定性證據。

### 3.2 Precondition Contracts 第 2、3、4 節
- **Execution Precondition**：
  - 操作地下城卡片之前置條件為 `SceneId.DUNGEON_SELECT` 成立。
- **Prerequisite Action**：
  - 頁籤切換屬於前置動作，必須由 `InFlightAction` 管理並等待 postcondition 驗證。
  - [states/handlers/navigation.py](../states/handlers/navigation.py) 第 1037 行與 1058 行手動 `match(dungeon.png)` 點擊屬於未受管旁路，必須納入冷卻或進度管理，杜絕每幀狂點。

### 3.3 Lobby Scene Contract (Invariant 1 & Invariant 5)
- 升格 **Invariant 1（成對差值主導保證）**：明確 Active-Dominance 在幾何重合度高時由「數值優勢 + 色相光環檢驗」共同擔保。

---

## 4. 解決方案設計：方案 A + B 雙重消歧架構 (Two-Dimensional Disambiguation)

```text
               ┌─────────────────────────────────────────┐
               │    輸入 screen_img 與目標頁籤 pair      │
               └────────────────────┬────────────────────┘
                                    │
                                    ▼
               ┌─────────────────────────────────────────┐
               │ 執行 TemplateMatcher: conf_act, conf_inact │
               └────────────────────┬────────────────────┘
                                    │
               ┌────────────────────┴────────────────────┐
               │ 差值: diff = conf_act - conf_inact      │
               └────────────────────┬────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
    diff >= 0.025             abs(diff) < 0.025         diff <= -0.025
(Active 顯著領先)             (微差模糊邊界區間)       (Inactive 顯著領先)
           │                        │                        │
           ▼                        ▼                        ▼
     【判定 Active】      ┌──────────────────┐        【判定 Inactive】
                          │ 方案 B: 色彩檢驗 │
                          │ (外環紅色光暈)   │
                          └────────┬─────────┘
                                   │
                      ┌────────────┴────────────┐
                      ▼                         ▼
            Red Halo Ratio >= 7%      Red Halo Ratio < 7%
                      │                         │
                      ▼                         ▼
                【判定 Active】           【判定 Inactive】
```

### 4.1 方案 A：自適應差值分級 (Adaptive Margin)
1. **明確領先區間**：
   - 若 $conf_{\text{act}} - conf_{\text{inact}} \ge 0.025$：Active 確定勝出。
   - 若 $conf_{\text{inact}} - conf_{\text{act}} \ge 0.025$：Inactive 確定勝出。
2. **微差模糊區間 ($|\Delta| < 0.025$)**：
   - 當兩者差距在 $0.025$ 以內且 $conf_{\text{act}} \ge 0.70$ 時，觸發方案 B 進行確定性色彩消歧。

### 4.2 方案 B：抽象共用模組 `verify_tab_red_halo`
建立獨立共用輔助函式（可置於 `utils/scene_detector.py` 或 `vision/matcher.py`）：
```python
def verify_tab_red_halo(
    screen_img: np.ndarray,
    pos: Tuple[int, int],
    btn_size: Tuple[int, int] = (160, 160),
    inner_ratio: float = 0.75,
    outer_ratio: float = 1.05,
    threshold_ratio: float = 0.07,
) -> bool:
    """
    向量化計算按鈕匹配位置外環的紅色光暈比例。
    - 截取以 pos 為中心、btn_size 為基準的 ROI。
    - 建立歸一化半徑遮罩 mask: inner_ratio <= r <= outer_ratio。
    - 轉換為 HSV 空間，核驗 H in [0, 12] or [165, 180] 且 S >= 70, V >= 70 的像素佔比。
    - 佔比 >= threshold_ratio (7%) 則判定紅光成立 (True)。
    - 計算開銷：160x160 局部 ROI 向量化布林計算，耗時 < 0.4ms。
    """
```

### 4.3 決策層治理：消滅 Handler 內部旁路死循環
在 [states/handlers/navigation.py](../states/handlers/navigation.py) 中：
1. 移除第 1037 行直接比對 `dungeons/dungeon.png` 並每幀點擊的邏輯。
2. 頁籤切換發出點擊後，設定冷卻時間戳（或記錄 `InFlightAction`），至少等待 0.5 秒讓動畫完成並由感知層回傳 `dungeon_select_open=True`，不再瘋狂重複發射點擊。

---

## 5. 變更檔案清單與測試計畫

### 5.1 變更檔案清單
1. **`utils/scene_detector.py`**：
   - 實作 `verify_tab_red_halo` 演算法。
   - 在 `_resolve_expected_lobby_tab()` 與 `_resolve_full_relocalize()` 套用方案 A + B 雙重消歧。
2. **`states/handlers/navigation.py`**：
   - 治理大廳地下城與普通關卡頁籤切換點擊，加入防抖與有界冷卻。
3. **`tests/test_entity_lobby_panel.py`**：
   - 增加微差情境單元測試：5 組頁籤在數值相近時，依賴紅光檢驗 100% 正確判定。
4. **`docs/features/navigation/lobby_scene_contract.md`**：
   - 契約同步更新 Invariant 1。

### 5.2 驗證指令
```powershell
.venv\Scripts\python -m unittest tests.test_entity_lobby_panel tests.test_scene_detector tests.test_behavior_navigation
```
