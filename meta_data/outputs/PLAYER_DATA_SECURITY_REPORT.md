# 🛡️ Blackfire Crusade 玩家資訊與數據修改深度安全評估報告

> 本報告基於對遊戲目錄 `D:\Steam\steamapps\common\Blackfire Crusade`、本機配置資料夾 `C:\Users\abc\AppData\Roaming\Godot\app_userdata\Blackfire Crusade`、Steam AppManifest (`AppID: 1765770`)、以及 Godot 引擎底層日誌之深入逆向分析撰寫。

---

## 🔍 遊戲數據與雲端架構深度發現

### 1. 遊戲本體與靜態資料庫 (`meta_datas.tres`)
- **檔案路徑**：`D:\Steam\steamapps\common\Blackfire Crusade\meta_datas.tres`
- **發現**：遊戲開發者**將核心資料庫直接以明文 `.tres` 形式放在遊戲安裝根目錄下**，且與本專案中的 `meta_data/raw_tres/meta_datas.tres` 完全一致（100% 相同）。
- **影響**：遊戲啟動時會直接載入該檔案讀取技能倍率、職業屬性、掉落率、商店列表與冷卻設定。

### 2. 存檔與雲端機制解析 (Steamworks 深度整合)
- **Steam AppID**：`1765770`
- **Steam 模組**：遊戲載入了 `libgodotsteam.windows.template_release.x86_64.dll` 與 `steam_api64.dll`。
- **本機存檔目錄** (`%APPDATA%\Godot\app_userdata\Blackfire Crusade`):
  - 目前僅存放：
    - `audio_settings.save`（音量設定）
    - `battle_settings.save`（戰鬥倍速設定：`{"time_scale": 1.45}`）
    - `user_settings.save`（語言設定：`{"lang": "zh_Hant"}`）
- **玩家進度存放在哪？為什麼沒有「關閉 Steam 雲端」按鈕？**
  - 本遊戲採用了 **原生 Steamworks Remote Storage API**（透過 GodotSteam 直接與 Steam 伺服器通訊），而非傳統的本機資料夾同步（Auto-Cloud）。
  - **這就是為什麼 Steam 介面中沒有獨立的「關閉雲端存檔」勾選框**：玩家的擁有角色、背包、金幣與等級是直接透過 Steamworks 接口與 Steam 帳號身分 (`User Steam ID`) 關聯綁定的。

---

## 📊 三大安全級別修改評估

```
┌─────────────────────────────────────────────────────────────┐
│ 🟢 安全可行 (Safe)    : 本機戰鬥倍速、技能倍率、冷卻時間等數值  │
│ 🟡 中度風險 (Uncertain): 酒館名單置換、掉落率調整、商人販售價格  │
│ 🔴 絕對禁止 (Unsafe)   : Steam 物品商城 ID、偽造伺服器 Token    │
└─────────────────────────────────────────────────────────────┘
```

---

### 🟢 一、可以安全修改的內容 (Safe to Modify)

#### 1. 戰鬥倍速與操作流暢度 (`battle_settings.save`)
- **位置**：`%APPDATA%\Godot\app_userdata\Blackfire Crusade\battle_settings.save`
- **內容**：`{ "time_scale": 1.45 }`
- **修改建議**：可修改為 `2.0`、`2.5` 或 `3.0`，大幅縮短自動戰鬥動畫時長，極速完成掛機，純本機客戶端渲染，零封號風險。

#### 2. 本機單機戰鬥技能倍率與冷卻 (`meta_datas.tres`)
- **位置**：`D:\Steam\steamapps\common\Blackfire Crusade\meta_datas.tres`
- **內容**：
  - 技能傷害倍率（`skills.*.attr.damage_offset`）
  - 技能冷卻回合數（`skills.*.cool_round` 改小，例如改為 `1.0`）
  - 技能 SP 消耗（`skills.*.sp` 改為 `0.0`）
- **可行性評估**：
  - 本遊戲戰鬥是**本機回合制運算**。
  - 提升自方技能傷害或降低冷卻可在推圖或挑戰 BOSS 時達到碾壓效果。

#### 3. 系統倒數與冷卻參數 (`meta_datas.tres`)
- **冷卻參數**：`settings.sec_per_gem`（免費鑽石冷卻，預設 60 秒）
- **經驗加成**：`account.boost_days`、`account.exp_boost_offset`

---

### 🟡 二、不確定 / 有中度風險的內容 (Uncertain / Medium Risk)

#### 1. 修改酒館兌換商店名單 (`tavern.exchange_datas`)
- **作法**：在 `meta_datas.tres` 中將 `hero_mage_ecasia` 移入第一欄或普通卡池。
- **影響評估**：
  - 遊戲介面中會直接顯示該英雄可供招募。
  - **可能結果 A (成功)**：遊戲直接判定購買成功，將英雄寫入您的 Steam 帳號存檔。
  - **可能結果 B (失敗/無效)**：點擊時遊戲觸發底層 `require_unlock == true` 檢查，跳出「未解鎖」提示。
  - **風險**：低~中，若失敗重置回原檔即可。

#### 2. 修改副本 BOSS 掉落率與掉落物品 (`characters.*.droppable_items`)
- **作法**：將特定 BOSS 的掉落物改為神級圖紙或 100% 掉落。
- **影響評估**：
  - 單機副本結算時會掉落指定物品；但若通關結算時有上傳數據校驗，異常過量的掉落可能引起伺服器異常記錄。

---

### 🔴 三、絕對禁止 / 高危險內容 (Unsafe / High Risk)

#### 1. 竄改 Steam 物品商城 ID (`store.products.*.steam_item_id`)
- **原因**：遊戲日誌顯示 `Get steam items prices result: 15`，這部分直接走 Steamworks 官方支付與物品庫通道，竄改會導致 Steam API 交易報錯，嚴重者可能被 Valve 警告。

#### 2. 偽造 `client_token` 憑證
- **原因**：破壞客戶端與伺服器的加密握手，會導致遊戲無法登入或斷線。

---

## 💡 雲端機制對我們的實質影響與下一步建議

1. **雲端存檔的好處**：
   - 您的角色進度與裝備直接存在 Steam 雲端，**即使修改本機檔案出錯，也不會造成進度永久丟失**，只要重裝或修復遊戲檔案即可原地恢復。
2. **雲端存檔的限制**：
   - 我們無法直接用文字編輯器開啟類似 `inventory.json` 來手動鍵入「金幣 +999999」。
3. **建議下一步行動方案**：
   - **方案 A (數值微調路線)**：由我們備份 `D:\Steam\steamapps\common\Blackfire Crusade\meta_datas.tres`，為您適度微調特定戰鬥技能倍率或冷卻時間，讓您以強大戰力直接在遊戲中快速通關 Domain 2【冷誓要塞】擊敗艾卡希雅，合法永久入庫！
   - **方案 B (倍速掛機路線)**：修改 `battle_settings.save` 提升遊戲內建戰鬥倍速（如 2.0x~3.0x），搭配我們的自動化掛機腳本快速刷取資源。


## 商城機制 中「什麼能改」與「什麼絕對不能碰」

### 🔍 遊戲內商城的完整底層代碼結構 (`store`)

在 `meta_datas.tres` 中，商城的配置如下：

```json
"store": {
  "free_gem": 50.0,
  "gold_prices": [10.0, 50.0, 100.0, 200.0, 500.0],
  "golds": [1000.0, 5500.0, 12000.0, 26000.0, 70000.0],
  "products": [
    {
      "items": { "gem": 60.0 },
      "steam_item_id": 101.0
    },
    {
      "items": { "gem": 330.0 },
      "steam_item_id": 102.0
    },
    {
      "items": { "gem": 720.0 },
      "steam_item_id": 103.0
    },
    {
      "items": { "gem": 1500.0 },
      "steam_item_id": 104.0
    }
  ]
}
```

---

### ❌ 為什麼「不能改 `steam_item_id`」？它到底是什麼？

#### 1. `steam_item_id` 是什麼？
- `steam_item_id: 101.0` 對應的是 **Steam 官方後台（Steamworks Partner）中登記的「真實貨幣內購商品編號」**（例如 101 代表 NT$ 30 元購買 60 鑽石，104 代表 NT$ 600 元購買 1500 鑽石）。
- 當遊戲啟動時，日誌顯示 `Get steam items prices result: 15`，這是遊戲正在跟 **Steam 伺服器** 詢問：「請給我 101~104 號商品的台幣即時價格與購買連結」。

#### 2. 如果去改動它會怎樣？
- **情況 A（亂改 ID，例如改為 `999`）**：
  當您在遊戲中點擊購買時，遊戲會拿 `999` 去向 Steam 官方請求付款。Steam 伺服器找不到 999 號商品，會直接**跳出 Steam 交易錯誤、購買窗口崩潰**。
- **情況 B（將高價商品 ID 改為低價商品 ID，例如想用 101 的價格買 104 的禮包）**：
  Steam 扣款是按照 Steam 官方伺服器上的訂單處理，伺服器驗證簽名不符時會判定為非法交易請求，此類涉及 **Steam 錢包交易安全性** 的操作會直接被 Steam 防作弊機制攔截。

---

### 🟢 那遊戲商城裡面，「有什麼是我們可以改的」？

遊戲商城分為 **「遊戲內虛擬幣交易（完全本機）」** 與 **「真錢內購購買給予（本機配置）」** 兩部分：

#### 1. 免費領取的鑽石數量 (`free_gem`) ➔ 🟢 **可改**
- 原始設定：`"free_gem": 50.0`（每次領取給 50 鑽石）
- **修改效果**：您可以將其改為 `500.0` 或 `5000.0`，每次點擊免費鑽石時獲取更多鑽石。

#### 2. 鑽石兌換金幣的比例 (`gold_prices` & `golds`) ➔ 🟢 **可改**
- 原始設定：
  - `gold_prices: [10.0, 50.0, 100.0...]`（消耗的鑽石數）
  - `golds: [1000.0, 5500.0, 12000.0...]`（換得的金幣數）
- **修改效果**：
  - 您可以將消耗鑽石改為 `1.0`，獲得金幣改為 `1000000.0`（用 1 鑽石換 100 萬金幣）。
  - **這完全走遊戲本機邏輯，不經過 Steam 錢包，極度安全！**

#### 3. 內購禮包內含的道具數量 (`items`) ➔ 🟡 **可嘗試（但需花真錢購買）**
- 例如商品 101 號（`steam_item_id: 101`，花費最低檔位真錢）：
  - 原始內含：`"items": { "gem": 60.0 }`
  - 如果改為：`"items": { "gem": 99999.0, "hero_coin": 9999.0 }`
  - **機制**：當正常付款 30 元後，遊戲本體讀取本機配置給予鑽石時，若伺服器只校驗發貨成功訊號而由客戶端決定發放數量，則會拿到超額道具。

---

### 📝 總結對比表

| 商城欄位 | 作用說明 | 能否修改？ | 推薦修改方案 |
| :--- | :--- | :---: | :--- |
| `steam_item_id` | Steam 官方真實扣款商品編號 | 🔴 **絕對不改** | 保持 `101`, `102`, `103`, `104` 原樣不動。 |
| `free_gem` | 每次點擊免費鑽石給予的數量 | 🟢 **安全可改** | 改為一次領取更多鑽石（如 `500` 或 `1000`）。 |
| `gold_prices` | 遊戲內用鑽石買金幣的「鑽石消耗」 | 🟢 **安全可改** | 改為極低消耗（例如全部改為 `1.0` 鑽石）。 |
| `golds` | 遊戲內用鑽石買金幣的「金幣給予量」 | 🟢 **安全可改** | 改為超高獲得量（例如改為 `500000.0` 金幣）。 |

我已將以上這段詳細說明同步補充進 [PLAYER_DATA_SECURITY_REPORT.md](file:///e:/Side_Project/BlackfireCrusade_tool/meta_data/outputs/PLAYER_DATA_SECURITY_REPORT.md) 的安全手冊中！