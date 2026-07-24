# 珠寶加工廠 (Jewelry Workshop) 出售功能說明 💎

本文件說明 《Blackfire Crusade》 自動化輔助工具中的 **珠寶加工廠 (Jewelry Workshop) 出售功能** 設計架構、顏色品質階層目錄、執行模式、商品個別設定與滑動搜尋比對機制。

---

## 🚀 功能概述

珠寶加工廠為城鎮中的核心建築之一，玩家可在出售選單 (`sell_out.png`) 中出售各類素材與商品。腳本自動遍歷商品清單，自動進行向下滑動搜尋、點選商品、賣出 (`sell.png`)、拉滿數量 (`sell_max.png`) 及確認離場。

---

## 📂 顏色品質階層目錄結構 (Color-Based Directory Structure)

素材模板依顏色品質等級分門別類收錄於 `templates/town_building/Jewelry_workshop/goods/` 子目錄中：

```
templates/town_building/Jewelry_workshop/goods/
├── gray/                                     # 灰色素材 (普通)
│   ├── Sandworm_scales.png                   # 沙蟲鱗片
│   ├── Spider_silk.png                       # 蜘蛛絲
│   ├── Spider_venom_glands.png               # 蜘蛛毒腺
│   ├── Warcraft_Fang.png                     # 魔獸之牙
│   ├── lizard_skin.png                       # 蜥蜴皮
│   └── scrap.png                             # 廢料
├── green/                                    # 綠色素材 (優秀)
│   ├── The_cloth_wrapped_around_the_dead.png # 包裹死者的布
│   └── Giant_Beast_Gold_Tooth.png           # 巨獸金牙
├── blue/                                     # 藍色素材 (預留)
└── purple/                                   # 紫色素材 (預留)
```

---

## ⚙️ 可配置出售規則 (Configurable Goods Settings)

使用者可在 [config.py](file:///e:/Side_Project/BlackfireCrusade_tool/config.py) 中的 `goods_settings` 字典內，按顏色品質區分並**個別管理每一個商品是否出售 (`True` / `False`)**：

```python
"goods_settings": {
    "gray": {
        "Sandworm_scales": True,     # 出售沙蟲鱗片
        "Spider_silk": True,         # 出售蜘蛛絲
        "Spider_venom_glands": True, # 出售蜘蛛毒腺
        "Warcraft_Fang": False,      # 保留魔獸之牙 (不賣)
        "lizard_skin": True,         # 出售蜥蜴皮
        "scrap": True,               # 出售廢料
    },
    "green": {
        "The_cloth_wrapped_around_the_dead": True, # 出售包裹死者的布
        "Giant_Beast_Gold_Tooth": True,            # 出售巨獸金牙
    },
    "blue": {},
    "purple": {},
}
```

### 💡 跨模式全域繼承與連動
- **獨立 CLI 模式 (`--mode jewelry_workshop`)**：讀取並執行上述商品出售規則。
- **城鎮任務流水線 (`Town Subflow Pipeline`)**：在 `mix` (混合模式)、`stage` (推圖模式) 或 `dungeon` (地城模式) 自動掛機過程中，若背包滿清理後退回城鎮連動進入珠寶加工廠，系統會 **100% 自動繼承與遵循此設定**。被設為 `False` 的商品（如 `Warcraft_Fang`）在流水線中同樣會被安全保留，絕對不會被誤賣！

---

## 💡 執行模式與用法

### 獨立單次出售模式 (CLI 獨立版)
使用者可由命令列單獨發起珠寶加工廠出售：
```powershell
.venv\Scripts\python main.py --backend --mode jewelry_workshop
```

- **自動進門與開啟選單**：於城鎮自動辨識並點擊 `Jewelry_workshop.png` ➔ 點擊 `sell_out.png` 開啟出售選單。
- **商品滑動與還原演算法**：
  1. 於頂層畫面匹配商品圖示 (門檻 $0.90$)。
  2. 若未尋獲 ➔ 執行向下滑動 2 次再次搜尋。
  3. 若仍未尋獲 ➔ 認定未持有該商品 ➔ **向上滑動 2 次還原畫面高度** ➔ 繼續比對下一個商品。
- **出售與確認**：點擊商品圖示 ➔ 點擊 `sell.png` ➔ 點擊 `sell_max.png` (拉滿) ➔ 點擊 `ok.png` / `confirm.png` 確認出售。
- **離場**：全數商品處置完畢後，點擊 `exitfromhouse_and_to_town.png` 離開建築回到城鎮並安全退出程式。
