# 珠寶加工廠 (Jewelry Workshop) 出售功能說明 💎

本文件說明 《Blackfire Crusade》 自動化輔助工具中的 **珠寶加工廠 (Jewelry Workshop) 出售功能** 設計架構、顏色品質階層目錄、執行模式、商品個別設定與滑動搜尋比對機制。

---

## 🚀 功能概述

珠寶加工廠為城鎮中的核心建築之一，玩家可在出售選單 (`sell_out.png`) 中出售各類素材與商品。腳本自動遍歷商品清單，自動進行向下滑動搜尋、點選商品、賣出 (`sell.png`)、拉滿數量 (`sell_max.png`) 及確認離場。

---

## 📂 顏色品質階層目錄結構 (Color-Based Directory Structure)

素材模板依顏色品質等級分門別類收錄於 `templates/town_building/Jewelry_workshop/goods/` 子目錄中

---

## ⚙️ 可配置出售規則 (Configurable Goods Settings)

使用者可在 [config.py](file:///e:/Side_Project/BlackfireCrusade_tool/config.py#L255) 中的 `goods_settings` 字典內，按顏色品質區分並**個別管理每一個商品是否出售 (`True` / `False`)**：
> ⚠️ **注意事項**：新增任何商品截圖至 `goods/` 資料夾時，必須同步在 [config.py](file:///e:/Side_Project/BlackfireCrusade_tool/config.py#L255) 的 `goods_settings` 白名單設定為 `True`，系統才會發起比對與出售！

---

## 🔄 同一商品多堆/多次連續出售機制 (Multi-Stack Repeat Sell)

當背包內擁有同一個商品的**多堆/多格**（如 2 堆 `Spider_silk`）時：
1. **彈窗消失閉環 (`click_and_wait_until_gone`)**：發起點擊 `sell.png` ➔ `sell_max.png` ➔ `ok.png` / `confirm.png` 後，系統會持續輪詢確認彈窗徹底從畫面上消失。
2. **多層彈窗自動清理**：若點擊 `ok.png` 後緊接着跳出第二層 `confirm.png`，會連續清理閉環。
3. **乾淨二次比對**：彈窗清空並沉澱 `0.4` 秒後，重新比對畫面 `post_sell_img`：
   - 若畫面上**仍有同名商品** 且重複次數 $< 5$ 堆上限 ➔ 繼續對該商品發射出售，不推進至下一個商品。
   - 若商品**已售罄**或達到 5 堆安全上限 ➔ 才清零計數器並推進至下一個商品。

---

## 💡 執行模式與用法

### 獨立單次出售模式 (CLI 獨立版)
使用者可由命令列單獨發起珠寶加工廠出售：
```powershell
.venv\Scripts\python main.py --backend --mode jewelry_workshop
```

- **自動進門與開啟選單**：於城鎮自動辨識並點擊 `Jewelry_workshop.png` ➔ 點擊 `sell_out.png` 開啟出售選單。
- **商品滑動與還原演算法**：
  1. 於頂層畫面匹配商品圖示 (門檻 $0.75$)。
  2. 若未尋獲 ➔ 執行向下滑動 2 次再次搜尋。
  3. 若仍未尋獲 ➔ 認定未持有該商品 ➔ **向上滑動 2 次還原畫面高度** ➔ 繼續比對下一個商品。
- **出售與確認**：點擊商品圖示 ➔ 點擊 `sell.png` ➔ 點擊 `sell_max.png` (拉滿) ➔ `click_and_wait_until_gone` 雙層 `ok.png` / `confirm.png` 閉環確認。
- **離場**：全數商品處置完畢後，點擊 `exitfromhouse_and_to_town.png` 離開建築回到城鎮並安全退出程式。
