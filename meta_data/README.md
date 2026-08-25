# 📊 Blackfire Crusade 遊戲數據分析與英雄圖鑑解析模組 (MetaData Module)

本模組專門負責解析《Blackfire Crusade》的 Godot 資源檔 (`meta_data/raw_tres/meta_datas.tres`)，提取遊戲內所有**英雄 (Heroes)**、**技能 (Skills)**、**職業 (Classes)**、**屬性 (Attributes)** 與數值成長公式，並進行繁體中文化轉換與多維度數據集導出。

---

## 📁 目錄結構一覽

```text
meta_data/
├── raw_tres/
│   └── meta_datas.tres            # 原始 Godot Resource 資源檔 (613 KB)
├── dicts/                         # 繁體中文翻譯字典庫 (可自由擴充與覆寫)
│   ├── class_i18n.json            # 7 大職業名稱
│   ├── rarity_i18n.json           # 0~6 星稀有度品質說明 (白/綠/藍/紫/橘/紅/彩)
│   ├── race_i18n.json             # 22+ 種族中文名稱 (精靈、龍裔、蛙人、獸人等)
│   ├── damage_type_i18n.json      # 傷害與效果屬性 (物理、魔法、火焰、冰霜等)
│   ├── target_i18n.json           # 目標範圍與陣營 (單體、遠程、近戰、全體等)
│   ├── attr_i18n.json             # 50+ 項數值屬性標籤 (暴擊、流血、冰凍、護盾等)
│   ├── hero_i18n.json             # 英雄專屬官方稱號對照
│   ├── skill_i18n.json            # 技能官方中文名稱對照
│   └── generate_dicts.py          # 字典快速生成與批量更新腳本
├── outputs/                       # 自動解析產出的 4 大資料集與圖鑑報表
│   ├── 1_heroes_list.json         # ① 全部 60 位英雄清單
│   ├── 2_hero_skills.json         # ② 每個英雄的完整技能配備表
│   ├── 3_raw_skills.json          # ③ 全遊戲 702 個技能原始數值與成長公式
│   ├── 4_hero_skill_analytics.json# 英雄與技能綜合主數據庫 (Master JSON)
│   └── HERO_ANALYSIS_REPORT.md    # ④ 繁體中文全景分析圖鑑 (800+ 行 Markdown)
├── tres_parser.py                 # Godot .tres 語法核心解析器
├── hero_analyzer.py               # 數據處理、翻譯與報表導出主程式
└── README.md                      # 本說明文檔
```

---

## 🎯 4 大導出產物說明

| 產物項目 | 檔案路徑 | 格式 | 核心用途與內容 |
| :--- | :--- | :--- | :--- |
| **① 全部英雄清單** | `meta_data/outputs/1_heroes_list.json` | JSON | 收錄全遊戲 60 位英雄的 ID、中文稱號、職業、稀有度星級、種族、性別、初始裝備與所屬技能。 |
| **② 每個英雄技能** | `meta_data/outputs/2_hero_skills.json` | JSON | 依英雄索引，收錄每位英雄身上的 1~7 個技能完整數值、主/被動、冷卻與目標對照。 |
| **③ 技能原始數值** | `meta_data/outputs/3_raw_skills.json` | JSON | 收錄遊戲內全 702 個技能的原始倍率 (`damage_offset`)、CD、SP、每級成長數值 (`attr_per_level`) 及異常狀態 (流血/冰凍/眩暈等)。 |
| **④ 繁體中文分析圖鑑** | `meta_data/outputs/HERO_ANALYSIS_REPORT.md` | Markdown | 精美排版的中文圖鑑，包含職業成長表、7 大系列英雄資料、技能詳細數值與附加效果。 |

---

## 🎮 遊戲實際英雄對照範例

本模組提取之英雄資料完全來自遊戲底層數據 `meta_datas.tres`。

以遊戲中的最高階英雄 **「寒噬女巫 · 艾卡希雅」** 為例：
- **內部 ID**：`hero_mage_ecasia`
- **階級 / 稀有度**：VII 階 / 稀有度 `6.0`（紅/彩色最高品質）
- **職業 / 種族**：法師 (`mage`) / 精靈 (`elf`) / 女性
- **配備技能組對照**：
  1. `frostscar_spike` ➔ **冰痕之刺**（主動，造成 50% 傷害並附加霜痕與冰凍機率）
  2. `shardspire_entombment` ➔ **霜棘冰葬**（主動，CD 5 回合，2 體目標）
  3. `shardspire_cataclysm` ➔ **霜棘殞滅**（主動，CD 7 回合，全體 5 體攻擊）
  4. `frost_control` ➔ **寒冷掌控**（屬性/被動，提升冰霜傷害加深與抗性）
  5. `icy_soul_echo` ➔ **冰魂迴響**（被動，行動點與能量獲取）
  6. `frostglyph_aegis` ➔ **霜紋庇護**（友方護盾）
  7. `icethorn_demise` ➔ **冰刺終局**（被動霜痕爆發）

---

## 🚀 快速開始與重新導出 (Usage)

### 1. 一鍵重新解析與生成所有產物
當更新了 `meta_data/raw_tres/meta_datas.tres` 或修改了翻譯字典後，於終端機執行：

```powershell
.\.venv\Scripts\python meta_data/hero_analyzer.py
```

### 2. 更新或擴充翻譯字典
若想調整詞彙翻譯，可直接編輯 `meta_data/dicts/*.json`，或在 `meta_data/dicts/generate_dicts.py` 增補後執行：

```powershell
.\.venv\Scripts\python meta_data/dicts/generate_dicts.py
```

### 3. 戰鬥時鐘倍速與自動化設定器 (支援免重開即時生效)
模組內建專屬輔助工具 [set_battle_settings.py](scripts/set_battle_settings.py)，可自由調整遊戲原生戰鬥時鐘倍速 (`time_scale` 1.0x ~ 100.0x)：

```powershell
# 設定為 12 倍極速上限 (預設推薦，直接執行即可)
.\.venv\Scripts\python meta_data/scripts/set_battle_settings.py

# 自由指定任意倍速 (例如 6x 或 12x)
.\.venv\Scripts\python meta_data/scripts/set_battle_settings.py --speed 6

# 還原為原廠 2.0x 正常倍速
.\.venv\Scripts\python meta_data/scripts/set_battle_settings.py --reset
```
* **特性**：自動處理 Windows 系統唯讀鎖 (`attrib +r`)，且支援**免關閉遊戲現場熱套用**（進入下一場戰鬥即刻生效）。

### 4. 執行單元測試驗證
本模組具備完整的單元測試防護：

```powershell
.\.venv\Scripts\python -m unittest tests.test_meta_tres_parser
```