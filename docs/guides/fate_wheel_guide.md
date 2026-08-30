# 🎡 命運輪盤 (Fate Wheel) 機制與資料庫數據分析指南

> 本指南依據遊戲核心資料庫 [`meta_data/raw_tres/meta_datas.tres`](../../meta_data/raw_tres/meta_datas.tres) 之原始設定與前台實際機制進行整理。

---

## 📌 一、 核心機制與消耗規則

### 1. 前台輪盤運作模式
* **抽一少一（獎勵不放回）**：
  * 每週輪盤展示固定格數的獎勵，抽中的獎勵當週不會重複出現（剔除制）。
  * 輪盤每週重置一次（介面標語：「*命運輪調之間，幸運悄悄降臨，每週重置*」）。
* **命運幣遞增消耗機制**：
  * 轉動輪盤消耗專屬貨幣「命運幣 (`fate_coin`)」。
  * 每次抽取所需的命運幣數量**會隨抽取進度逐次遞增**（非固定 1 幣）。
  > [!NOTE]
  > **資料庫記錄聲明**：在 `meta_datas.tres` 靜態配置資源中，**並無記錄具體的每抽遞增數列或計算公式**（該消耗計算邏輯封裝於遊戲客戶端程式碼內）。因此此處僅確認機制為遞增消耗，不列出未經資料庫證實的推測數值。

---

## 💰 二、 資料庫確認之命運幣購買設定 (`fate_coin_sell_dic`)

在 `meta_datas.tres` 中明確定義的命運幣商城販售規格如下：

* **每包數量**：**15 枚命運幣**
* **每包售價**：**300 寶石**（換算單價 **20 寶石 / 1 幣**）
* **限購次數**：每週期（每週）**限購 5 次**
* **單週購買上限**：最高可購買 **75 枚命運幣**，總花費 **1,500 寶石**

---

## 🎁 三、 資料庫確認之獎勵池分層清單 (`fate_wheel`)

在 `meta_datas.tres` 中，命運輪盤的獎勵池嚴格按品質欄位劃分：

| 品質階級 | 資料庫欄位 | 包含道具內容清單 |
| :--- | :--- | :--- |
| 🔴 **遠古 (Ancient)** | `ancient_items` | `piercing_hammer_6` (6階打孔錘)、`skill_card_7` (7階技能卡)、`weapon_shard_6` (6階武器石)、`amulet_hp_7` ~ `amulet_mag_7` (7階護符)、`rune_dam_7` ~ `rune_mag_7` (7階符文)、`demon_seal_stone_4` (4階惡魔封印石) |
| 🟠 **神話 (Mythic)** | `mythic_items` | `piercing_hammer_5`、`skill_card_6`、`weapon_shard_5`、`amulet_hp_6` ~ `amulet_mag_6`、`rune_dam_6` ~ `rune_mag_6`、`demon_seal_stone_3` |
| 🟡 **傳說 (Legendary)**| `legendary_items` | `piercing_hammer_4`、`skill_card_5`、`weapon_shard_4`、`amulet_hp_5` ~ `amulet_mag_5`、`rune_dam_5` ~ `rune_mag_5`、`demon_seal_stone_2` |
| 🟣 **史詩 (Epic)** | `epic_items` | `piercing_hammer_3`、`skill_card_4`、`weapon_shard_3`、`amulet_hp_4` ~ `amulet_mag_4`、`rune_dam_4` ~ `rune_mag_4`、`demon_seal_stone_1` |
| 🟢 **其他 (Other)** | `other_items` | `piercing_hammer_2`、`skill_card_3`、`weapon_shard_2`、`amulet_hp_3` ~ `amulet_mag_3`、`rune_dam_3` ~ `rune_mag_3` |
| 🪙 **貨幣類獎勵** | `coins` / `hero_coins` / `fate_coins` | 金幣（`400.0` / `500.0`）、英雄幣（`400.0` / `500.0`）、命運幣（`5.0` / `10.0` 返還） |

---

## 🎲 四、 機率分析：為何總是「先抽到低階、大獎在最後」？

### 1. 全域品質權重表 (`rarity.chances`)
遊戲底層各品質的抽取基準權重為：

```json
"rarity": {
  "chances": [100.0, 40.0, 20.0, 10.0, 5.0, 2.5, 1.25]
}
```

* **低階品質 (1~3階)**：基礎權重 `100.0` / `40.0` / `20.0`
* **史詩 (4階)**：基礎權重 `10.0`
* **傳說 (5階)**：基礎權重 `5.0`
* **神話 (6階)**：基礎權重 `2.5`
* **遠古 (7階)**：基礎權重 `1.25`（僅為低階的 1/80）

### 2. 機制與體感關聯
1. **加權隨機 ✕ 獎勵剔除**：
   * 輪盤每格在畫面呈現上大小相同，但後端並非均等機率，而是按品質權重分配。
   * 前期獎池完整時，低階道具權重佔比壓倒性過半，因此消耗較少幣的前幾抽極大概率命中低階材料。
   * 隨著低階道具逐一被抽中並剔除，高階神話/遠古大獎的命中率才會顯著提升，但此時已處於遞增消耗較高的階段。
2. **成就設定**：
   * 成就系統中設有 `turn_fate_wheel`，累積轉動 500 次可獲得專屬頭像 `fate_wheel` 與稱號「命運先驅 (`fate_harbinger`)」。
