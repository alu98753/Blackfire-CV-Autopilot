# 珠寶加工廠 (Jewelry Workshop) 出售功能說明 💎

本文件說明 《Blackfire Crusade》 自動化輔助工具中的 **珠寶加工廠 (Jewelry Workshop) 出售功能** 設計架構、執行模式與商品滑動搜尋比對機制。

---

## 🚀 功能概述

珠寶加工廠為城鎮中的核心建築之一，玩家可在出售選單 (`sell_out.png`) 中出售各類素材與商品。腳本自動遍歷商品清單，自動進行向下滑動搜尋、點選商品、賣出 (`sell.png`)、拉滿數量 (`sell_max.png`) 及確認離場。

---

## 💡 執行模式與用法

### 獨立單次出售模式 (CLI 獨立版)
使用者可由命令列單獨發起珠寶加工廠出售：
```powershell
.venv\Scripts\python main.py --backend --mode jewelry_workshop
```

- **自動進門與開啟選單**：於城鎮自動辨識並點擊 `Jewelry_workshop.png` ➔ 點擊 `sell_out.png` 開啟出售選單。
- **商品滑動與還原演算法**：
  1. 於頂層畫面匹配商品圖示 (信心度 $\ge 0.75$)。
  2. 若未尋獲 ➔ 執行向下滑動 2 次再次搜尋。
  3. 若仍未尋獲 ➔ 認定未持有該商品 ➔ **向上滑動 2 次還原畫面高度** ➔ 繼續比對下一個商品。
- **出售與確認**：點擊商品圖示 ➔ 點擊 `sell.png` ➔ 點擊 `sell_max.png` (拉滿) ➔ 點擊 `ok.png` / `confirm.png` 確認出售。
- **離場**：全數商品處置完畢後，點擊 `exitfromhouse_and_to_town.png` 離開建築回到城鎮並安全退出程式。

---

## 📦 出售商品清單 (Goods Templates)

收錄於 `templates/town_building/Jewelry_workshop/goods/`：
1. `Sandworm_scales.png` (沙蟲鱗片)
2. `Spider_silk.png` (蜘蛛絲)
3. `Spider_venom_glands.png` (蜘蛛毒腺)
4. `The_cloth_wrapped_around_the_dead.png` (包裹死者的布)
5. `Warcraft_Fang.png` (魔獸之牙)
6. `lizard_skin.png` (蜥蜴皮)
7. `scrap.png` (廢料)
