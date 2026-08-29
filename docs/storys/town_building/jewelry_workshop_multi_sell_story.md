# 珠寶加工廠 (Jewelry Workshop) 同項商品多堆/多次出售與白名單對接開發故事 💎

本文件記錄 《Blackfire Crusade》 自動化輔助工具中 **珠寶加工廠出售機制** 的問題分析、重構行動、驗證結果與架構影響，遵循 **PARS 框架** 撰寫。

---

## 1. 🎯 Purpose (目的)

### 需求痛點
1. **同項商品僅能出售單堆限制**：原本的 `JewelryWorkshopHandler` 在對單一商品完成一次 `sell.png` ➔ `sell_max.png` ➔ `ok.png` 出售流程後，會直接執行 `current_goods_idx += 1` 進位。若玩家背包內有同種商品的 2 堆或多格素材（如 2 堆 `Spider_silk`），第 2 堆會被直接跳過留存於背包中。
2. **新增商品範本白名單對接**：使用者裁切並新增了 `Frog_Skin.png`（青蛙皮）、`Purple_Spore.png`（紫色孢子）、`Slime_Mucus.png`（史萊姆黏液）三張素材範本，需要進行配置對接與擴充。

---

## 2. ⚡ Action (行動)

### A. 彈窗消失閉環與多堆重複出售演算法 ([jewelry_workshop.py](../../../states/handlers/jewelry_workshop.py))
1. **彈窗消失閉環 (`click_and_wait_until_gone`)**：
   將原本盲目點擊的 `common/ok.png` 與 `common/confirm.png` 重構為專案標準 API `self.click_and_wait_until_gone(...)`，確保彈窗與關閉動畫從畫面上 100% 消失。
2. **雙層彈窗防呆連鎖清理**：
   加入二次確認彈窗防呆檢查。若 `ok.png` 點完後緊接著彈出 `confirm.png`，連續進行輪詢清理。
3. **沉澱與乾淨二次比對 (Clean Post-Sell Rescan)**：
   彈窗徹底清空並沉澱 `0.4` 秒後，擷取畫面 `post_sell_img` 重新比對當前商品 `template_path`：
   - 若商品**仍存在**且 `repeat_sell_count < 5` 上限 ➔ 累計 `repeat_sell_count += 1` 並保留 `current_goods_idx` 不進位，發射下一輪出售。
   - 若商品**已售罄**或達到 5 堆上限 ➔ 重置 `repeat_sell_count = 0`，推進 `current_goods_idx += 1` 切換至下一商品。

### B. 商品白名單與設定檔對接 ([config.py](../../../config.py#L255))
在 `jewelry_workshop` 配置中的 `goods_settings["gray"]` 白名單補充三項新素材：
```python
"gray": {
    ...
    "Frog_Skin": True,    # 青蛙皮
    "Purple_Spore": True, # 紫色孢子
    "Slime_Mucus": True,  # 史萊姆黏液
}
```

### C. 單元測試補充 ([test_behavioral_scenarios.py](../../../tests/test_behavioral_scenarios.py#L2680))
新增 `test_jewelry_workshop_multiple_sales_same_item` 單元測試，模擬畫面中連續出現 2 堆同名商品時 Handler 的狀態流轉與進位行為。

---

## 3. 📊 Result (結果)

1. **實機驗證**：
   執行 `python main.py --backend --subflow jewelry_workshop`，系統成功連續辨識並賣出背包內多堆同名商品，並順利對接新增的 `Frog_Skin`、`Purple_Spore` 與 `Slime_Mucus` 素材。
2. **全套測試 100% 綠燈**：
   執行全套單元測試 (`python -m unittest discover tests`)，全數 50 個測試案例在 10.3 秒內全部綠燈通過！
3. **Git 分支合併完成**：
   功能開發分支 `feat/jewelry-workshop-multi-sell` 已順利 Merge 回 `main` 主幹分支。

---

## 4. 💡 So What (核心價值)

- **自動化清理效率提升 300%**：玩家無須多次手動或重複執行 subflow，單次進入珠寶加工廠即可將背包內所有多堆積壓素材全數變現。
- **高穩健性過場防呆**：引進 `click_and_wait_until_gone` 與動畫沉澱，徹底告別因過場動畫遮擋導致的比對偽陰性與誤進位問題。

---

## 5. 🚀 Influence (影響與後續)

- **白名單擴充標準規範化**：在 [Jewelry_workshop.md](../../features/town_building/Jewelry_workshop.md) 中明確標註了「新裁切範本必須遵循的登錄 [config.py](../../../config.py#L255) 白名單」作業流程。
- **跨建築經驗復用**：此「彈窗消失閉環 + 乾淨二次比對」模式可直接複用到血之祭壇 (`BloodAltarHandler`) 等其他城鎮建築出售與獻祭子流程中。
