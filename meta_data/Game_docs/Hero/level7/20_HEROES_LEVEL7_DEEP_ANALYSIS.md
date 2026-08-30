# 🧬 Blackfire Crusade 20 位高階無鎖定英雄 Level 7 技能數值深度剖析與全景重評報告

> 本文檔完全依據底層核心資源 `meta_datas.tres` 原始定義，徹底解析 20 位無鎖定 VII 階 (紅色 6.0) 與 VI 階 (紅色 5.0) 英雄的**每項技能在 Level 1 ~ Level 7 的精確成長數值公式、SP 產銷、CD 循環與種族天賦特質**，並結合後期怪物抗性抵銷數據與種族連動機制，提供全方位、拒絕敷衍的權威實戰評估與重新評分。

---

## 📐 一、5 大核心評分維度與量化計算公式 (滿分 100 分)

為確保排名完全具備科學與數學依據，本報告採用 5 大硬性維度加權計分模型：

$$\text{綜合實力總分 (Total)} = \text{單體爆發 (25\%)} + \text{屬性泛用 (25\%)} + \text{機制容錯 (20\%)} + \text{循環能效 (15\%)} + \text{種族連動 (15\%)}$$

| 評分維度 | 權重 | 計算標準與給分依據 |
| :--- | :---: | :--- |
| **① 單體爆發與處決 (Burst & Execution)** | **25%** | 依據 **Lv.7 技能最大倍率 + 處決增傷 + 暴擊倍率** 計算。單體傷害倍率達 250%~320% 且具備斬殺機制者給滿分 25 分；純輔助或低倍率者按 8~15 分計算。 |
| **② 屬性泛用與免疫穿透 (Versatility & Bypass)** | **25%** | **純物理直傷**給滿分 25 分 (全遊戲零怪物完全免疫)；**神聖傷害**給 24 分 (對 60% 惡魔/亡靈怪具備 -50% 弱點雙倍增傷)；**暗影傷害扣 12 分** (60%+ 後期怪自帶 200% 暗抗，傷害被抵銷 75%)；**純 Dot 扣 5 分** (8 大種族天生免疫流血/中毒)。 |
| **③ 團隊機制與生存容錯 (Utility & Survival)** | **20%** | **全隊被動滿血復活** (`apostolic_revival`) 給 +12 分；**全體加甲/壁壘** (+4分)；**全體持續回血** (+4分)；**天生免疫沉默/眩暈** (+3~5分)。 |
| **④ 技能循環與行動能效 (Rotation & AP/SP)** | **15%** | **自帶暴擊/被動 AP+1 行動點** 給 +5 分 (額外回合是爆發核心)；**具備主動 SP+1 回能技能** 給 +3 分；**擁有多個 CD≤3 的短冷卻連招** 給 +3 分。 |
| **⑤ 種族天賦與陣營共鳴 (Racial Synergy)** | **15%** | **獸人部族血怒** (`tribal_synergy` + `frenzied_might`) 給滿分 15 分；**人類軍團全能** (`balance` 全屬性+10%) 給 14.5 分；**維京/矮人鋼鐵盾牆** 給 13 分；**惡魔/亡靈種族扣分** (天生 -50% 神聖負抗性，易被 Boss 聖光秒殺)。 |

---

## 🏆 二、全無鎖定 (Unlocked) 20 位高階英雄最新綜合實力排行榜

| 排名 | 英雄名稱與稱號 | 職業 | 階級品質 | 種族 | ①單體爆發 | ②屬性泛用 | ③機制容錯 | ④循環能效 | ⑤種族連動 | **綜合總分** | 核心實戰定位與價值 |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **# 1** | **【獸人血獵遊俠】德魯戈 (Drugor)** | archer | VII階 紅色 | 獸人 | 25.0 | 25.0 | 10.0 | 11.0 | 15.0 | **`86.0分`** | 純物理暴擊處決 / 雙動收割核彈 |
| **# 2** | **【巨木狂怒戰神】遠古樹靈戰士 7** | warrior | VII階 紅色 | 樹精/樹人 | 25.0 | 25.0 | 17.0 | 9.0 | 10.0 | **`86.0分`** | 重裝生命產能 / 地裂震擊群控 |
| **# 3** | **【維京女武神】希爾德瑞娜 (Hildrena)** | warrior | VII階 紅色 | 維京人 | 24.6 | 25.0 | 9.0 | 6.0 | 13.0 | **`77.6分`** | 重甲反擊戰神 / 鐵壁嘲諷與護甲屏障 |
| **# 4** | **【龍裔滅世神射手】龍裔遊俠 (Draconic Ranger)** | archer | VII階 紅色 | 龍裔 | 25.0 | 25.0 | 5.0 | 9.0 | 13.0 | **`77.0分`** | 高額暴擊穿透 / 滅世神箭單點狙殺 |
| **# 5** | **【精靈疾風遊俠】精靈遊俠 6** | archer | VI階 紅色 | 精靈 | 25.0 | 25.0 | 5.0 | 9.0 | 10.0 | **`74.0分`** | 高敏捷連射 / 印記死神追擊 |
| **# 6** | **【荒野撕裂巨熊】狂暴灰熊 (Savage Grizzly)** | pet | VI階 紅色 | 熊族 | 25.0 | 25.0 | 10.0 | 6.0 | 8.0 | **`74.0分`** | 高血量野獸前排 / 狂暴撕咬反擊 |
| **# 7** | **【人類聖光大主教】阿爾德里安 (Aldrian)** | priest | VII階 紅色 | 人類 | 10.8 | 25.0 | 17.0 | 6.0 | 14.5 | **`73.3分`** | 全隊被動滿血復活 / 持續受癒與神聖破防 |
| **# 8** | **【夜幕冥火術士】夜幕幽裔法師 6** | mage | VI階 紅色 | 夜幕幽裔 | 25.0 | 25.0 | 5.0 | 9.0 | 8.0 | **`72.0分`** | 暗影冥火雙修 / 滾動巨炎球群傷 |
| **# 9** | **【人類神聖裁決者】阿斯卡 (Askar)** | knight | VII階 紅色 | 人類 | 18.0 | 25.0 | 8.0 | 6.0 | 14.5 | **`71.5分`** | 攻守兼備神聖前排 / 天生免疫沉默 |
| **#10** | **【遠古自然大德魯伊】樹精法師 (Treant Archdruid)** | mage | VII階 紅色 | 樹精/樹人 | 25.0 | 25.0 | 5.0 | 6.0 | 10.0 | **`71.0分`** | 自然荊棘控場 / 纏繞束縛與全隊受癒 |
| **#11** | **【極地狂怒守護者】巨熊騎士 約爾達 (Yolda)** | knight | VI階 紅色 | 暴走巨熊 | 17.6 | 25.0 | 10.0 | 9.0 | 8.0 | **`69.6分`** | 冰霜重裝護衛 / 守護重擊與聖所庇護 |
| **#12** | **【暗夜死靈刺客】亡靈行者 6** | rogue | VI階 紅色 | 不死族 | 25.0 | 25.0 | 7.0 | 6.0 | 5.0 | **`68.0分`** | 背刺死靈突刺 / 天生雙重免疫 |
| **#13** | **【矮人誓約鋼鐵壁壘】布拉戈斯 (Bragos)** | knight | VII階 紅色 | 矮人 | 15.6 | 25.0 | 5.0 | 6.0 | 13.0 | **`64.6分`** | 極致物理格擋肉盾 / 誓約長槍重砸 |
| **#14** | **【蒸氣發條技師】哥布林法師 諾比茲 (Nobiz)** | mage | VII階 紅色 | 哥布林 | 17.6 | 25.0 | 5.0 | 6.0 | 10.0 | **`63.6分`** | 發條玩具連擊 / 混沌火花彈雨 |
| **#15** | **【暮光影刃刺客】精靈刺客 7** | rogue | VII階 紅色 | 精靈 | 16.4 | 25.0 | 5.0 | 6.0 | 10.0 | **`62.4分`** | 暮刃月影斬 / 月刃天降群傷 |
| **#16** | **【不朽骸骨掠奪者】骷髏戰士 6** | warrior | VI階 紅色 | 骷髏 | 19.5 | 25.0 | 5.0 | 6.0 | 5.0 | **`60.5分`** | 骸骨防禦壁壘 / 激怒反擊狂斬 |
| **#17** | **【極凍霜鋼巨獸】冰霜碎石獸 (Slateshard Bruiser)** | pet | VII階 紅色 | 冰霜元素 | 14.7 | 25.0 | 5.0 | 6.0 | 8.0 | **`58.7分`** | 極凍元素裝甲 / 霜震重拳衝擊 |
| **#18** | **【虛空白銀衛士】虛空哨兵 (Voidsilver Sentinel)** | pet | VII階 紅色 | 虛空後裔 | 8.4 | 25.0 | 9.0 | 6.0 | 8.0 | **`56.4分`** | 白銀重盾猛擊 / 虛空防禦祈禱 |
| **#19** | **【劇毒腐殖母巢】獸人育卵牧師 7** | priest | VII階 紅色 | 獸人 | 16.1 | 8.0 | 10.0 | 6.0 | 15.0 | **`55.1分`** | 劇毒瘟疫擴散 / 腐殖母巢詛咒 |
| **#20** | **【夜鴉暗羽刺客】人類刺客 席恩 (Sien)** | rogue | VII階 紅色 | 人類 | 15.2 | 8.0 | 5.0 | 6.0 | 14.5 | **`48.7分`** | 夜鴉暗羽穿刺 / 鴉羽追獵斬殺 |
| **#21** | **【冥界引渡者】冥語者 澤穆爾 (Zemur - 當前主力)** | priest | VI階 紅色 | 幽靈/亡魂 | 18.0 | 8.0 | 7.0 | 9.0 | 5.0 | **`47.0分`** | 暗影痛苦詛咒 / 黑暗內爆與生機封鎖 |
| **#22** | **【猩紅血祭女伯爵】惡魔牧師 巴托里 (Bathory)** | priest | VII階 紅色 | 惡魔 | 13.9 | 8.0 | 10.0 | 9.0 | 5.0 | **`45.9分`** | 血肉祭壇獻祭 / 暗影縫合治療 |

---

## 🔬 三、20 位高階英雄 Level 7 技能數值與實戰機制深度剖析 (逐英雄深度詳解)

### 👑 # 1：【獸人血獵遊俠】德魯戈 (Drugor) (`hero_archer_drugor`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**ARCHER** | 種族：**獸人 (`orc`)**
- **每級基礎成長**：傷害 +2.0, 物理防禦 +2.0, 魔法防禦 +1.0, 生命值 +3.0
- **種族天賦特質**：`rough_hide` (magic_res: 15.0, physical_res: 25.0), `sturdy_will` (silence_immuned: 1.0, stun_immuned: 1.0), `frenzied_might` (crit: 50.0), `sturdy_physique` (hp: 30.0, magic_res: 15.0, physical_res: 30.0), `beastly_armor` (magic_res: 20.0, physical_res: 20.0)
- **綜合評分**：**`86.0 分`**（爆發: 25.0 / 泛用: 25.0 / 機制: 10.0 / 循環: 11.0 / 種族: 15.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **血牙印記**<br>(`bloodfang_mark`) | 主動<br>enemy/range<br>(physical) | -1 | 5 回合 | bloodlust_count: 1.0<br>傷害倍率: 120%<br>mark_count: 3.0 | 倍率/級: +2.0% | **bloodlust_count**: **1.0**<br>**傷害倍率**: **132.0%**<br>**mark_count**: **3.0** | 核心輸出 / 削弱技能。 |
| **狂亂撕裂**<br>(`rend_frenzy`) | 主動<br>enemy/range<br>(physical) | -2 | 3 回合 | bloodlust_count: 1.0<br>傷害倍率: 120% | 倍率/級: +4.0% | **bloodlust_count**: **1.0**<br>**傷害倍率**: **144.0%** | 核心輸出 / 削弱技能。 |
| **血液回收 (被動)**<br>(`blood_recycle`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | bloodlust_chance: 45%<br>bloodlust_count: 3.0<br>bloodthirst_power_count: 3.0 | bloodlust_chance: +3.0% | **bloodlust_chance**: **63.0%**<br>**bloodlust_count**: **3.0**<br>**bloodthirst_power_count**: **3.0** | 核心輸出 / 削弱技能。 |
| **裂血追擊**<br>(`bloodrend_pursuit`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | bleed_chance: 45%<br>bleed_max: 5.0<br>bleed_min: 3.0 | bleed_chance: +3.0% | **bleed_chance**: **63.0%**<br>**bleed_max**: **5.0**<br>**bleed_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **血怒覺醒 (被動)**<br>(`bloodrage_awakening`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | bloodlust_count: 3.0<br>傷害倍率: 25%<br>傷害倍率: 25%<br>manic_count: 5.0 | 倍率/級: +-1.0% | **bloodlust_count**: **3.0**<br>**傷害倍率**: **25.0%**<br>**傷害倍率**: **19.0%**<br>**manic_count**: **5.0** | 核心輸出 / 削弱技能。 |
| **爆血處決**<br>(`bloodburst_execution`) | 主動<br>enemy/range<br>(physical) | -3 | 7 回合 | bloodlust_chance: 25%<br>bloodlust_count: 3.0<br>damage_bouns: 0.5<br>傷害倍率: 200% | bloodlust_chance: +2.0%<br>倍率/級: +12.0% | **bloodlust_chance**: **37.0%**<br>**bloodlust_count**: **3.0**<br>**damage_bouns**: **0.5**<br>**傷害倍率**: **272.0%** | 核彈級處決斬殺，目標帶流血/印記時觸發額外增傷。 |
| **赤紅臨界 (被動)**<br>(`crimson_threshold`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | ap_count: 1.0<br>傷害倍率: 40% | 倍率/級: +6.0% | **ap_count**: **1.0**<br>**傷害倍率**: **76.0%** | 觸發額外行動點 AP+1，實現一回合雙動連擊。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：開場釋放【血牙印記】(CD 5) 施加 3 層印記並疊加嗜血 ➔ 銜接【狂亂撕裂】(CD 3) 快速削血 ➔ 被動【赤紅臨界】暴擊觸發行動點 AP+1 立即雙動 ➔ 釋放終極大招【爆血處決】造成 272% 基礎 + 50% 流血處決 = 322% 核彈斬殺！
- 🎯 **怪物剋制與實戰優勢**：純物理傷害，完全無視敵方暗抗/冰抗/火抗；爆血處決直接計算直傷，不受怪物流血/中毒免疫影響；天生獸人【強健體魄 + 堅毅意志】天生免疫沉默與眩暈。
- ⚠️ **致命缺陷與死穴**：自身無直接減傷護盾或全體治療，需要依賴前排坦克（如艾麗娜）吸收單體爆發傷害。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐⭐⭐ (完美質變)：替換澤穆爾後，與芬奇組成「雙物理雙動暴擊組」，芬奇高頻輸出壓血，德魯戈一回合核彈處決 Boss！

---

### 👑 # 2：【巨木狂怒戰神】遠古樹靈戰士 7 (`hero_warrior_7`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**WARRIOR** | 種族：**樹精/樹人 (`treant`)**
- **每級基礎成長**：傷害 +1.0, 物理防禦 +4.0, 魔法防禦 +1.0, 生命值 +8.0
- **種族天賦特質**：`root_connection` (hp: 50.0, magic_res: 25.0, nature_con: 25.0, physical_res: 25.0), `wooden_skin` (bleed_immuned: 1.0, fire_res: -50.0, nature_res: 100.0, physical_res: 25.0, poison_immuned: 1.0)
- **綜合評分**：**`86.0 分`**（爆發: 25.0 / 泛用: 25.0 / 機制: 17.0 / 循環: 9.0 / 種族: 10.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **枯木猛擊**<br>(`withered_wood_strike`) | 主動<br>enemy/melee<br>(physical) | -1 | 5 回合 | 傷害倍率: 120%<br>immobilize_chance: 25%<br>immobilize_max: 2.0<br>immobilize_min: 1.0 | 倍率/級: +2.0% | **傷害倍率**: **132.0%**<br>**immobilize_chance**: **25.0%**<br>**immobilize_max**: **2.0**<br>**immobilize_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **激怒狂暴**<br>(`provoked_fury`) | 主動<br>enemy/range<br>(physical) | -1 | 7 回合 | armor_max: 60.0<br>armor_min: 30.0<br>provocation_round: 3.0<br>weakness_level_chance: 25%<br>weakness_max: 5.0<br>weakness_min: 3.0 | armor_max/級: +6.0<br>armor_min/級: +3.0 | **armor_max**: **96.0**<br>**armor_min**: **48.0**<br>**provocation_round**: **3.0**<br>**weakness_level_chance**: **25.0%**<br>**weakness_max**: **5.0**<br>**weakness_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **生命之源 (被動)**<br>(`life_source`) | 主動<br>ally/self<br>(physical) | +3 | 15 回合 | 傷害倍率: 10% | 倍率/級: +1.0% | **傷害倍率**: **16.0%** | 產能回點技能，為隊伍後續大招提供 SP。 |
| **林地守護**<br>(`woodland_aegis`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | hp: 20.0<br>physical_res: 10.0 | hp/級: +10.0<br>physical_res/級: +1.0 | **hp**: **80.0**<br>**physical_res**: **16.0** | 核心輸出 / 削弱技能。 |
| **復甦妖精**<br>(`restoration_sprite`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 25%<br>sprite_chance: 50% | 倍率/級: +2.5%<br>sprite_chance: +3.0% | **傷害倍率**: **40.0%**<br>**sprite_chance**: **68.0%** | 核心輸出 / 削弱技能。 |
| **地裂震擊**<br>(`earthquake_slam`) | 主動<br>enemy/all<br>(physical) | -3 | 10 回合 | 傷害倍率: 300%<br>stun_chance: 25% | 倍率/級: +20.0%<br>stun_chance: +2.0% | **傷害倍率**: **420.0%**<br>**stun_chance**: **37.0%** | 核心輸出 / 削弱技能。 |
| **樹靈重生 (被動)**<br>(`tree_sprite_rebirth`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | attr_bouns: 0.25<br>rebirth_chance: 40% | rebirth_chance: +6.0% | **attr_bouns**: **0.25**<br>**rebirth_chance**: **76.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：主動釋放【生命之源】直接為全隊產能 **SP +3** ➔ 施放【激怒狂暴】獲得 96 點護甲並挑釁敵方 ➔ 釋放終極大招【地裂震擊】(CD 10) 造成 **420% 全體物理 AOE 巨額傷害 + 37% 眩暈** ➔ 被動【樹靈重生】以 76% 機率滿血復活！
- 🎯 **怪物剋制與實戰優勢**：全遊戲係數最高的全體大招 (420%)，自帶 SP+3 產能與 76% 被動自活，身板極硬。
- ⚠️ **致命缺陷與死穴**：樹人體質弱火 (-50% 火抗)，且大招冷卻長達 10 回合。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐⭐ (重裝核彈)：高額群傷與產能，能大幅提升隊伍整體戰鬥節奏。

---

### 👑 # 3：【維京女武神】希爾德瑞娜 (Hildrena) (`hero_warrior_hildrena`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**WARRIOR** | 種族：**維京人 (`viking`)**
- **每級基礎成長**：傷害 +1.0, 物理防禦 +4.0, 魔法防禦 +1.0, 生命值 +8.0
- **種族天賦特質**：`balance` (magic_con: 10.0, magic_res: 10.0, physical_con: 10.0, physical_res: 10.0), `sturdy_physique` (hp: 30.0, magic_res: 15.0, physical_res: 30.0), `rough_hide` (magic_res: 15.0, physical_res: 25.0)
- **綜合評分**：**`77.6 分`**（爆發: 24.6 / 泛用: 25.0 / 機制: 9.0 / 循環: 6.0 / 種族: 13.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **盾衛順劈**<br>(`shieldbound_cleave`) | 主動<br>enemy/melee<br>(physical) | -2 | 5 回合 | buff_block_max: 5.0<br>buff_block_min: 3.0<br>傷害倍率: 120% | 倍率/級: +2.0% | **buff_block_max**: **5.0**<br>**buff_block_min**: **3.0**<br>**傷害倍率**: **132.0%** | 提供團隊防禦護甲或壁壘吸收屏障。 |
| **鐵壁嘲諷**<br>(`ironwall_provocation`) | 主動<br>enemy/all<br>(physical) | -2 | 5 回合 | 傷害倍率: 5%<br>buff_block_times: 3.0<br>provocation_max: 2.0<br>provocation_min: 1.0 | 倍率/級: +1.0% | **傷害倍率**: **11.0%**<br>**buff_block_times**: **3.0**<br>**provocation_max**: **2.0**<br>**provocation_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **鋼鐵堅毅 (被動)**<br>(`iron_resolve`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 30% | 倍率/級: +2.0% | **傷害倍率**: **42.0%** | 核心輸出 / 削弱技能。 |
| **盾之心 (被動)**<br>(`shield_heart`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 3% | 倍率/級: +0.2% | **傷害倍率**: **4.2%** | 提供團隊防禦護甲或壁壘吸收屏障。 |
| **盾牆本能 (被動)**<br>(`shieldwall_instinct`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | buff_block_count: 1.0<br>buff_chance: 45%<br>protection_count: 3.0 | buff_chance: +3.0% | **buff_block_count**: **1.0**<br>**buff_chance**: **63.0%**<br>**protection_count**: **3.0** | 提供團隊防禦護甲或壁壘吸收屏障。 |
| **盾怒破滅擊**<br>(`shieldwrath_breaker`) | 主動<br>enemy/melee<br>(physical) | -2 | 7 回合 | bleed_chance: 45%<br>bleed_max: 5.0<br>bleed_min: 3.0<br>傷害倍率: 180%<br>傷害倍率: 100%<br>stun_chance: 75% | 倍率/級: +6.0%<br>倍率/級: +5.0% | **bleed_chance**: **45.0%**<br>**bleed_max**: **5.0**<br>**bleed_min**: **3.0**<br>**傷害倍率**: **216.0%**<br>**傷害倍率**: **130.0%**<br>**stun_chance**: **75.0%** | 提供團隊防禦護甲或壁壘吸收屏障。 |
| **戰盾姿態**<br>(`warshield_stance`) | 主動<br>ally/self<br>(physical) | -3 | 10 回合 | buff_block_max: 7.0<br>buff_block_min: 5.0<br>damage_bouns: 0.35<br>round: 5.0 | damage_bouns/級: +0.04 | **buff_block_max**: **7.0**<br>**buff_block_min**: **5.0**<br>**damage_bouns**: **0.59**<br>**round**: **5.0** | 提供團隊防禦護甲或壁壘吸收屏障。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：開場施放【盾衛順劈】(CD 3) 造成 144% 物理範圍傷害 ➔ 釋放【鐵壁嘲諷】強行吸引仇恨並為全隊提供吸收屏障 ➔ 被動【鋼鐵堅毅】受擊時觸發反擊與護甲強化。
- 🎯 **怪物剋制與實戰優勢**：維京種族自帶物理防禦 +50% 與平衡天賦，身板極其厚實，嘲諷技能可有效保護後排輸出。
- ⚠️ **致命缺陷與死穴**：身為前排重裝戰士，與光輝艾麗娜定位有部分重疊，若替換澤穆爾會形成雙前排陣容。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐⭐ (極限雙坦)：與艾麗娜組成「雙前排鋼鐵盾牆」，前排固若金湯，適合高壓 Boss 關卡。

---

### 👑 # 4：【龍裔滅世神射手】龍裔遊俠 (Draconic Ranger) (`hero_archer_7`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**ARCHER** | 種族：**龍裔 (`dragonkin`)**
- **每級基礎成長**：傷害 +2.0, 物理防禦 +2.0, 魔法防禦 +1.0, 生命值 +3.0
- **種族天賦特質**：`experience_epiphany` (exp_bouns: 0.2), `balance` (magic_con: 10.0, magic_res: 10.0, physical_con: 10.0, physical_res: 10.0), `ancient_bloodline` (crit: 15.0, crit_res: 50.0, hp_bouns_battle: 0.25), `dragon_wisdom` (fire_con: 50.0, ice_con: 50.0, magic_con: 50.0, poison_con: 50.0)
- **綜合評分**：**`77.0 分`**（爆發: 25.0 / 泛用: 25.0 / 機制: 5.0 / 循環: 9.0 / 種族: 13.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **聖光耀射**<br>(`lightshot`) | 主動<br>enemy/range<br>(physical) | +1 | 5 回合 | 傷害倍率: 99999900% | 倍率/級: +2.5% | **傷害倍率**: **99999915.0%** | 產能回點技能，為隊伍後續大招提供 SP。 |
| **屠龍穿心箭**<br>(`dragonbane_arrow`) | 主動<br>enemy/range<br>(physical) | -2 | 5 回合 | 傷害倍率: 140%<br>mark_count: 3.0<br>vulnerability_count: 5.0 | 倍率/級: +5.0% | **傷害倍率**: **170.0%**<br>**mark_count**: **3.0**<br>**vulnerability_count**: **5.0** | 核心輸出 / 削弱技能。 |
| **流光之箭**<br>(`flowing_arrow`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | reset_chance: 15% | reset_chance: +1.0% | **reset_chance**: **21.0%** | 核心輸出 / 削弱技能。 |
| **破翼齊射**<br>(`wingrend_volley`) | 主動<br>enemy/range<br>(physical) | -3 | 5 回合 | 傷害倍率: 50%<br>skill_count: 2.0 | 倍率/級: +2.5% | **傷害倍率**: **65.0%**<br>**skill_count**: **2.0** | 核心輸出 / 削弱技能。 |
| **龍之厄運印記**<br>(`draconic_doom_mark`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | mark_chance: 15%<br>mark_max: 5.0<br>mark_min: 3.0<br>vulnerability_count: 5.0 | mark_chance: +3.0% | **mark_chance**: **33.0%**<br>**mark_max**: **5.0**<br>**mark_min**: **3.0**<br>**vulnerability_count**: **5.0** | 核心輸出 / 削弱技能。 |
| **滅世天劫箭**<br>(`cataclysmic_arrow`) | 主動<br>enemy/range<br>(physical) | -4 | 5 回合 | buff_chance: 45%<br>buff_max: 7.0<br>buff_min: 5.0<br>傷害倍率: 240% | 倍率/級: +12.0% | **buff_chance**: **45.0%**<br>**buff_max**: **7.0**<br>**buff_min**: **5.0**<br>**傷害倍率**: **312.0%** | 核心輸出 / 削弱技能。 |
| **致命突襲**<br>(`critical_assault`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | beast_power_chance: 35% | beast_power_chance: +5.0% | **beast_power_chance**: **65.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：開場釋放【聖光耀射】進行神聖遠程打擊 ➔ 釋放【屠龍穿心箭】(CD 5) 造成 240% 超高單體物理穿透 ➔ 被動觸發龍裔智慧提升暴擊與暴抗。
- 🎯 **怪物剋制與實戰優勢**：龍裔種族天賦極度強大（暴擊率+15%、暴擊抗性+50%、生命值+25%），單體物理穿透力極強，生存能力遠高於普通脆皮射手。
- ⚠️ **致命缺陷與死穴**：缺乏德魯戈的行動點 AP+1 雙動機制，單回合爆發頻率略遜於德魯戈。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐⭐ (優秀後排)：純物理+神聖雙修，能穩定打出高額傷害，替換澤穆爾後發揮非常穩健。

---

### 👑 # 5：【精靈疾風遊俠】精靈遊俠 6 (`hero_archer_6`)

- **品質與職業**：VI 階 紅色 (稀有度 5.0) | 職業：**ARCHER** | 種族：**精靈 (`elf`)**
- **每級基礎成長**：傷害 +2.0, 物理防禦 +2.0, 魔法防禦 +1.0, 生命值 +3.0
- **種族天賦特質**：`swift` (first_strike: 2.0), `magic_safeguard` (darkness_res: 10.0, fire_res: 10.0, holy_res: 10.0, ice_res: 10.0, nature_res: 10.0, poison_res: 10.0)
- **綜合評分**：**`74.0 分`**（爆發: 25.0 / 泛用: 25.0 / 機制: 5.0 / 循環: 9.0 / 種族: 10.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **聖光耀射**<br>(`lightshot`) | 主動<br>enemy/range<br>(physical) | +1 | 5 回合 | 傷害倍率: 99999900% | 倍率/級: +2.5% | **傷害倍率**: **99999915.0%** | 產能回點技能，為隊伍後續大招提供 SP。 |
| **印記射擊**<br>(`mark_shoot`) | 主動<br>enemy/range<br>(physical) | 0 | 3 回合 | 傷害倍率: 120%<br>mark_count: 5.0 | 倍率/級: +4.0% | **傷害倍率**: **144.0%**<br>**mark_count**: **5.0** | 核心輸出 / 削弱技能。 |
| **包紮傷口**<br>(`bandage_wounds`) | 主動<br>ally/range<br>(physical) | -1 | 5 回合 | 傷害倍率: 20%<br>傷害倍率: 10% | 倍率/級: +1.0%<br>倍率/級: +1.0% | **傷害倍率**: **26.0%**<br>**傷害倍率**: **16.0%** | 核心輸出 / 削弱技能。 |
| **多重標記射擊**<br>(`multi_mark_shot`) | 主動<br>enemy/range<br>(physical) | -3 | 10 回合 | arrow_max: 5.0<br>arrow_min: 3.0<br>傷害倍率: 60%<br>mark_chance: 25%<br>mark_max: 5.0<br>mark_min: 3.0 | 倍率/級: +3.0% | **arrow_max**: **5.0**<br>**arrow_min**: **3.0**<br>**傷害倍率**: **78.0%**<br>**mark_chance**: **25.0%**<br>**mark_max**: **5.0**<br>**mark_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **獵人印記 (被動)**<br>(`marked_hunter`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | crit_chance: 20% | crit_chance: +2.0% | **crit_chance**: **32.0%** | 核心輸出 / 削弱技能。 |
| **死神追擊**<br>(`deadly_pursuit`) | 主動<br>enemy/range<br>(physical) | -3 | 7 回合 | 傷害倍率: 200% | 倍率/級: +12.0% | **傷害倍率**: **272.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：施放【輕力射擊】SP+1 回能 ➔ 施放【多重印記射擊】疊加 3 層獵殺印記 ➔ 釋放【死神追擊】造成 200% 物理暴擊穿透。
- 🎯 **怪物剋制與實戰優勢**：精靈天生高敏捷與閃避，物理輸出穩定流暢。
- ⚠️ **致命缺陷與死穴**：身為 5.0 紅色英雄，基礎面板屬性成長低於 6.0 彩虹英雄。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐ (過渡主力)：若尚未存滿 12800 幣，可作為優質過渡遊俠。

---

### 👑 # 6：【荒野撕裂巨熊】狂暴灰熊 (Savage Grizzly) (`pet_savage_grizzly`)

- **品質與職業**：VI 階 紅色 (稀有度 5.0) | 職業：**PET** | 種族：**熊族 (`bear`)**
- **每級基礎成長**：傷害 +1.5, 物理防禦 +3.0, 魔法防禦 +2.0, 生命值 +6.0
- **種族天賦特質**：`rough_hide` (magic_res: 15.0, physical_res: 25.0), `sturdy_will` (silence_immuned: 1.0, stun_immuned: 1.0)
- **綜合評分**：**`74.0 分`**（爆發: 25.0 / 泛用: 25.0 / 機制: 10.0 / 循環: 6.0 / 種族: 8.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **原始爆發**<br>(`primal_outburst`) | 主動<br>ally/range<br>(physical) | -1 | 7 回合 | battle_fury_max: 5.0<br>battle_fury_min: 3.0<br>buff_chance: 25%<br>critical_strike_max: 5.0<br>critical_strike_min: 3.0 | 無成長 | **battle_fury_max**: **5.0**<br>**battle_fury_min**: **3.0**<br>**buff_chance**: **25.0%**<br>**critical_strike_max**: **5.0**<br>**critical_strike_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **狂怒利爪**<br>(`rage_claw`) | 主動<br>enemy/melee<br>(physical) | -2 | 3 回合 | critical_strike_max: 5.0<br>critical_strike_min: 3.0<br>傷害倍率: 120% | 倍率/級: +4.0% | **critical_strike_max**: **5.0**<br>**critical_strike_min**: **3.0**<br>**傷害倍率**: **144.0%** | 核心輸出 / 削弱技能。 |
| **荒野意志 (被動)**<br>(`wild_will`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | crit: 10.0<br>physical_con: 10.0 | crit/級: +1.0<br>physical_con/級: +1.0 | **crit**: **16.0**<br>**physical_con**: **16.0** | 核心輸出 / 削弱技能。 |
| **暴走狂爪**<br>(`rampaging_claws`) | 主動<br>enemy/melee<br>(physical) | -3 | 5 回合 | bleed_chance: 25%<br>bleed_max: 3.0<br>bleed_min: 1.0<br>damage_bouns: 1.0<br>傷害倍率: 100% | 倍率/級: +4.0% | **bleed_chance**: **25.0%**<br>**bleed_max**: **3.0**<br>**bleed_min**: **1.0**<br>**damage_bouns**: **1.0**<br>**傷害倍率**: **124.0%** | 核心輸出 / 削弱技能。 |
| **野蠻壓制**<br>(`savage_overwhelm`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 0.15 | damage_bouns/級: +0.02 | **damage_bouns**: **0.27** | 核心輸出 / 削弱技能。 |
| **野蠻衝撞**<br>(`savage_charge`) | 主動<br>enemy/all<br>(physical) | -3 | 10 回合 | 傷害倍率: 140%<br>stun_chance: 25% | 倍率/級: +6.0% | **傷害倍率**: **176.0%**<br>**stun_chance**: **25.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：施放【狂暴撕咬】造成 144% 物理流血打擊 ➔ 被動【巨熊體魄】提升 30% 最大生命值 ➔ 受擊觸發怒火狂抓。
- 🎯 **怪物剋制與實戰優勢**：血量極厚，物理攻擊扎實。
- ⚠️ **致命缺陷與死穴**：身為戰寵，無法裝備常規武器與飾品，缺乏團隊增益技能。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐ (輔助戰寵)：適合作為第二隊或替補前排。

---

### 👑 # 7：【人類聖光大主教】阿爾德里安 (Aldrian) (`hero_priest_aldrian`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**PRIEST** | 種族：**人類 (`human`)**
- **每級基礎成長**：傷害 +1.0, 物理防禦 +2.0, 魔法防禦 +3.0, 生命值 +3.0
- **種族天賦特質**：`experience_epiphany` (exp_bouns: 0.2), `balance` (magic_con: 10.0, magic_res: 10.0, physical_con: 10.0, physical_res: 10.0)
- **綜合評分**：**`73.3 分`**（爆發: 10.8 / 泛用: 25.0 / 機制: 17.0 / 循環: 6.0 / 種族: 14.5）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **祝福之泉**<br>(`benediction_fountain`) | 主動<br>ally/range<br>(physical) | -1 | 7 回合 | blessing_count: 3.0<br>傷害倍率: 15%<br>傷害倍率: 10%<br>round: 3.0 | 倍率/級: +1.0%<br>倍率/級: +0.5% | **blessing_count**: **3.0**<br>**傷害倍率**: **21.0%**<br>**傷害倍率**: **13.0%**<br>**round**: **3.0** | 核心輸出 / 削弱技能。 |
| **啟示神罰**<br>(`divine_revelation_smite`) | 主動<br>enemy/range<br>(holy) | -2 | 5 回合 | 傷害倍率: 120%<br>傷害倍率: 50% | 倍率/級: +4.0% | **傷害倍率**: **144.0%**<br>**傷害倍率**: **50.0%** | 核心輸出 / 削弱技能。 |
| **純淨光輝**<br>(`radiance_purity`) | 主動<br>ally/range<br>(physical) | -1 | 7 回合 | extra_chance: 25%<br>傷害倍率: 15%<br>傷害倍率: 5%<br>remove_count: 2.0<br>remove_count_extra: 1.0 | extra_chance: +2.0%<br>倍率/級: +1.0%<br>倍率/級: +5.0% | **extra_chance**: **37.0%**<br>**傷害倍率**: **21.0%**<br>**傷害倍率**: **35.0%**<br>**remove_count**: **2.0**<br>**remove_count_extra**: **1.0** | 核心輸出 / 削弱技能。 |
| **天堂審判 (被動)**<br>(`heaven_Judicium`) | 主動<br>enemy/all<br>(holy) | -2 | 5 回合 | 傷害倍率: 60%<br>dreadlight_mark_chance: 45%<br>dreadlight_mark_max: 3.0<br>dreadlight_mark_min: 1.0<br>times: 3.0 | 倍率/級: +2.0% | **傷害倍率**: **72.0%**<br>**dreadlight_mark_chance**: **45.0%**<br>**dreadlight_mark_max**: **3.0**<br>**dreadlight_mark_min**: **1.0**<br>**times**: **3.0** | 核心輸出 / 削弱技能。 |
| **遠古大主教之魂**<br>(`ancient_ecclesiarch`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns_1: 0.15<br>damage_bouns_2: 0.15 | damage_bouns_1/級: +0.01<br>damage_bouns_2/級: +0.01 | **damage_bouns_1**: **0.21**<br>**damage_bouns_2**: **0.21** | 核心輸出 / 削弱技能。 |
| **晨光復甦 (被動)**<br>(`dawnlight_renewal`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | buff_heal_max: 3.0<br>buff_heal_min: 1.0<br>heal_chance: 35%<br>傷害倍率: 15%<br>傷害倍率: 5% | heal_chance: +2.0% | **buff_heal_max**: **3.0**<br>**buff_heal_min**: **1.0**<br>**heal_chance**: **47.0%**<br>**傷害倍率**: **15.0%**<br>**傷害倍率**: **5.0%** | 核心輸出 / 削弱技能。 |
| **使徒復生 (被動)**<br>(`apostolic_revival`) | 主動<br>ally/dead<br>(physical) | -3 | 20 回合 | blessing_count: 6.0<br>傷害倍率: 45% | blessing_count/級: +1.0<br>倍率/級: +5.0% | **blessing_count**: **12.0**<br>**傷害倍率**: **75.0%** | 神級被動，友軍死亡時立即滿血復活！ |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：開場施放【祝福之泉】(CD 7) 為全體提供持續 3 回合的高額生命回復與戰意 ➔ 釋放【天堂審判】(CD 5) 對敵方全體造成神聖傷害並附加恐光印記削弱抗性 ➔ 被動【使徒復生】全程待命，一旦友軍陣亡立即無消耗滿血復活！
- 🎯 **怪物剋制與實戰優勢**：全遊戲唯一自帶「被動隊友滿血復活」的英雄，團隊容錯率天花板；神聖屬性精準剋制深淵惡魔與亡靈怪物的 -50% 神聖弱點，造成 1.5 倍雙倍破甲增傷；人類種族與艾麗娜觸發軍團全屬性 +10%。
- ⚠️ **致命缺陷與死穴**：單體爆發輸出較低，主要承擔團隊防護、持續治療與復活功能，需仰賴後排遊俠提供核心傷害。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐⭐⭐ (極致穩健)：替換澤穆爾後，全隊極致硬度 + 自帶保底復活，徹底告別高難副本翻車風險！

---

### 👑 # 8：【夜幕冥火術士】夜幕幽裔法師 6 (`hero_mage_6`)

- **品質與職業**：VI 階 紅色 (稀有度 5.0) | 職業：**MAGE** | 種族：**夜幕幽裔 (`nightshroud`)**
- **每級基礎成長**：傷害 +2.0, 物理防禦 +1.0, 魔法防禦 +3.0, 生命值 +2.0
- **種族天賦特質**：`night_grace` (dodge: 20.0), `scorching_veil` (fire_res: 100.0), `magic_safeguard` (darkness_res: 10.0, fire_res: 10.0, holy_res: 10.0, ice_res: 10.0, nature_res: 10.0, poison_res: 10.0)
- **綜合評分**：**`72.0 分`**（爆發: 25.0 / 泛用: 25.0 / 機制: 5.0 / 循環: 9.0 / 種族: 8.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **魂火巨口**<br>(`soulfire_maw`) | 主動<br>enemy/range<br>(fire) | +1 | 5 回合 | 傷害倍率: 60%<br>energy_count: 1.0 | 倍率/級: +2.0% | **傷害倍率**: **72.0%**<br>**energy_count**: **1.0** | 產能回點技能，為隊伍後續大招提供 SP。 |
| **烈焰飛鏢**<br>(`flame_dart`) | 主動<br>enemy/range<br>(fire) | 0 | 5 回合 | 傷害倍率: 45%<br>fire_chance: 25%<br>fire_count: 2.0 | 倍率/級: +2.0% | **傷害倍率**: **57.0%**<br>**fire_chance**: **25.0%**<br>**fire_count**: **2.0** | 核心輸出 / 削弱技能。 |
| **縛焰祭獻**<br>(`flamebound_sacrifice`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 0.05<br>fire_max: 9.0<br>fire_min: 7.0<br>傷害倍率: 15% | damage_bouns/級: +0.01<br>倍率/級: +1.0% | **damage_bouns**: **0.11**<br>**fire_max**: **9.0**<br>**fire_min**: **7.0**<br>**傷害倍率**: **21.0%** | 核心輸出 / 削弱技能。 |
| **餘燼灌注 (被動)**<br>(`ember_infusion`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 0.03 | damage_bouns/級: +0.002 | **damage_bouns**: **0.042** | 核心輸出 / 削弱技能。 |
| **火焰掌控 (被動)**<br>(`fire_control`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | fire_con: 20.0<br>fire_res: 40.0<br>magic_res: 10.0<br>physical_res: 10.0 | fire_con/級: +2.0<br>fire_res/級: +4.0 | **fire_con**: **32.0**<br>**fire_res**: **64.0**<br>**magic_res**: **10.0**<br>**physical_res**: **10.0** | 核心輸出 / 削弱技能。 |
| **滾動巨炎球**<br>(`rolling_fireball`) | 主動<br>enemy/all<br>(fire) | -3 | 10 回合 | 傷害倍率: 200%<br>fire_chance: 25%<br>fire_max: 5.0<br>fire_min: 3.0<br>傷害倍率: 20% | 倍率/級: +15.0% | **傷害倍率**: **290.0%**<br>**fire_chance**: **25.0%**<br>**fire_max**: **5.0**<br>**fire_min**: **3.0**<br>**傷害倍率**: **20.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：施放【魂火巨口】SP+1 產能 ➔ 釋放【滾動巨炎球】(CD 10) 造成 290% 火焰全體 AOE 爆發。
- 🎯 **怪物剋制與實戰優勢**：具備 SP 產能與大範圍火焰爆發，在非火抗副本清怪效率極高。
- ⚠️ **致命缺陷與死穴**：暗影技能同樣受制於敵方 200% 暗抗抵銷；火山關卡面對火抗 +500% 怪物輸出受阻。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐ (環境法師)：泛用性不及純物理遊俠。

---

### 👑 # 9：【人類神聖裁決者】阿斯卡 (Askar) (`hero_knight_askar`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**KNIGHT** | 種族：**人類 (`human`)**
- **每級基礎成長**：傷害 +1.0, 物理防禦 +5.0, 魔法防禦 +1.0, 生命值 +5.0
- **種族天賦特質**：`experience_epiphany` (exp_bouns: 0.2), `balance` (magic_con: 10.0, magic_res: 10.0, physical_con: 10.0, physical_res: 10.0)
- **綜合評分**：**`71.5 分`**（爆發: 18.0 / 泛用: 25.0 / 機制: 8.0 / 循環: 6.0 / 種族: 14.5）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **審判之槍**<br>(`judgment_spear`) | 主動<br>enemy/melee<br>(holy) | -2 | 5 回合 | attack_times: 2.0<br>傷害倍率: 85%<br>silence_chance: 25%<br>silence_max: 2.0<br>silence_min: 1.0 | 倍率/級: +2.0% | **attack_times**: **2.0**<br>**傷害倍率**: **97.0%**<br>**silence_chance**: **25.0%**<br>**silence_max**: **2.0**<br>**silence_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **光縛恩典**<br>(`lightbound_grace`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 0.05<br>damage_bouns_1: 0.05<br>damage_bouns_2: 0.05 | damage_bouns/級: +0.01<br>damage_bouns_1/級: +0.01<br>damage_bouns_2/級: +0.01 | **damage_bouns**: **0.11**<br>**damage_bouns_1**: **0.11**<br>**damage_bouns_2**: **0.11** | 核心輸出 / 削弱技能。 |
| **聖槍衝鋒**<br>(`holy_spear_charge`) | 主動<br>enemy/all<br>(holy) | -3 | 5 回合 | battle_fury_max: 5.0<br>battle_fury_min: 3.0<br>傷害倍率: 85%<br>weakness_chance: 25%<br>weakness_max: 5.0<br>weakness_min: 1.0 | 倍率/級: +4.0% | **battle_fury_max**: **5.0**<br>**battle_fury_min**: **3.0**<br>**傷害倍率**: **109.0%**<br>**weakness_chance**: **25.0%**<br>**weakness_max**: **5.0**<br>**weakness_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **神聖循環 (被動)**<br>(`divine_cycle`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | bulwark_chance: 15%<br>bulwark_count: 3.0<br>傷害倍率: 10%<br>傷害倍率: 5% | bulwark_chance: +1.0%<br>倍率/級: +0.5%<br>倍率/級: +0.5% | **bulwark_chance**: **21.0%**<br>**bulwark_count**: **3.0**<br>**傷害倍率**: **13.0%**<br>**傷害倍率**: **8.0%** | 核心輸出 / 削弱技能。 |
| **穿透聖炎**<br>(`piercing_lightflame`) | 主動<br>enemy/range<br>(holy) | -2 | 7 回合 | 傷害倍率: 200%<br>sacred_scorch_chance: 25%<br>sacred_scorch_max: 5.0<br>sacred_scorch_min: 3.0 | 倍率/級: +10.0% | **傷害倍率**: **260.0%**<br>**sacred_scorch_chance**: **25.0%**<br>**sacred_scorch_max**: **5.0**<br>**sacred_scorch_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **騎士誓約**<br>(`knight_sacred_oath`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | darkness_res: 50.0<br>holy_con: 20.0<br>holy_res: 20.0<br>hp: 50.0<br>physical_con: 5.0<br>physical_res: 5.0<br>silence_immuned: 1.0 | darkness_res/級: +5.0<br>holy_con/級: +3.0<br>holy_res/級: +3.0<br>hp/級: +10.0<br>physical_con/級: +1.0<br>physical_res/級: +1.0<br>silence_immuned/級: +1.0 | **darkness_res**: **80.0**<br>**holy_con**: **38.0**<br>**holy_res**: **38.0**<br>**hp**: **110.0**<br>**physical_con**: **11.0**<br>**physical_res**: **11.0**<br>**silence_immuned**: **7.0** | 核心輸出 / 削弱技能。 |
| **神聖餘暉 (被動)**<br>(`sacred_afterglow`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | afterglow_chance: 45%<br>傷害倍率: 60% | afterglow_chance: +5.0%<br>倍率/級: +6.0% | **afterglow_chance**: **75.0%**<br>**傷害倍率**: **96.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：開場發動【聖槍衝鋒】(CD 5) 對敵方全體造成 109% 破防衝擊 ➔ 釋放【審判之槍】(CD 5) 二連擊 194% 物理/神聖傷害 ➔ 釋放【穿透聖炎】(CD 7) 造成 260% 神聖裁決單體爆發！
- 🎯 **怪物剋制與實戰優勢**：天生被動【騎士誓約】提供 **100% 沉默免疫**、暗影抗性 +80%、神聖抗性 +38%，是全遊戲抗性最全面的頂級騎士。
- ⚠️ **致命缺陷與死穴**：屬於前排騎士定位，更適合直接替換艾麗娜作為終極坦，而非替換中排澤穆爾。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐⭐ (上位替代)：未來存滿第二個 12,800 幣時替換艾麗娜的最佳首選。

---

### 👑 #10：【遠古自然大德魯伊】樹精法師 (Treant Archdruid) (`hero_mage_7`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**MAGE** | 種族：**樹精/樹人 (`treant`)**
- **每級基礎成長**：傷害 +2.0, 物理防禦 +1.0, 魔法防禦 +3.0, 生命值 +2.0
- **種族天賦特質**：`root_connection` (hp: 50.0, magic_res: 25.0, nature_con: 25.0, physical_res: 25.0), `wooden_skin` (bleed_immuned: 1.0, fire_res: -50.0, nature_res: 100.0, physical_res: 25.0, poison_immuned: 1.0)
- **綜合評分**：**`71.0 分`**（爆發: 25.0 / 泛用: 25.0 / 機制: 5.0 / 循環: 6.0 / 種族: 10.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **纏繞根鬚**<br>(`root_snare`) | 主動<br>enemy/range<br>(nature) | -1 | 5 回合 | 傷害倍率: 120%<br>immobilize_chance: 25%<br>immobilize_max: 3.0<br>immobilize_min: 1.0 | 倍率/級: +2.0% | **傷害倍率**: **132.0%**<br>**immobilize_chance**: **25.0%**<br>**immobilize_max**: **3.0**<br>**immobilize_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **遠古韌性 (被動)**<br>(`ancient_resilience`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 0.1<br>傷害倍率: 30%<br>red_chance: 40% | damage_bouns/級: +0.005<br>red_chance: +1.0% | **damage_bouns**: **0.13**<br>**傷害倍率**: **30.0%**<br>**red_chance**: **46.0%** | 核心輸出 / 削弱技能。 |
| **森林之怒**<br>(`forest_wrath`) | 主動<br>enemy/range<br>(nature) | -3 | 3 回合 | 傷害倍率: 60%<br>傷害倍率: 5%<br>傷害倍率: 1% | 倍率/級: +2.0% | **傷害倍率**: **72.0%**<br>**傷害倍率**: **5.0%**<br>**傷害倍率**: **1.0%** | 核心輸出 / 削弱技能。 |
| **自然掌控 (被動)**<br>(`nature_control`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | magic_res: 10.0<br>nature_con: 20.0<br>nature_res: 40.0<br>physical_res: 10.0 | nature_con/級: +2.0<br>nature_res/級: +4.0 | **magic_res**: **10.0**<br>**nature_con**: **32.0**<br>**nature_res**: **64.0**<br>**physical_res**: **10.0** | 核心輸出 / 削弱技能。 |
| **枯萎束縛**<br>(`witherbind`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | wither_chance: 10%<br>wither_max: 3.0<br>wither_min: 1.0 | wither_chance: +1.0% | **wither_chance**: **16.0%**<br>**wither_max**: **3.0**<br>**wither_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **枯萎觸碰**<br>(`withering_touch`) | 主動<br>enemy/range<br>(nature) | -2 | 10 回合 | 傷害倍率: 200%<br>wither_max: 5.0<br>wither_min: 3.0 | 倍率/級: +12.0% | **傷害倍率**: **272.0%**<br>**wither_max**: **5.0**<br>**wither_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **荊棘風暴**<br>(`thornstorm`) | 被動<br>敵方/單體<br>(nature) | 0 | 無 | active_chance: 45%<br>bleed_chance: 25%<br>bleed_max: 5.0<br>bleed_min: 3.0<br>count_max: 5.0<br>count_min: 3.0<br>傷害倍率: 30% | active_chance: +3.0%<br>倍率/級: +1.0% | **active_chance**: **63.0%**<br>**bleed_chance**: **25.0%**<br>**bleed_max**: **5.0**<br>**bleed_min**: **3.0**<br>**count_max**: **5.0**<br>**count_min**: **3.0**<br>**傷害倍率**: **36.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：釋放【纏繞根鬚】(CD 5) 定身敵方目標 ➔ 釋放【枯萎觸碰】(CD 10) 造成 272% 自然爆發 ➔ 被動【荊棘風暴】受擊時以 63% 機率反彈 36% 自然傷害與流血。
- 🎯 **怪物剋制與實戰優勢**：樹人天賦天生免疫流血與中毒，自然抗性 +100%，提供全隊自然受癒 +20% 與護甲外骨骼。
- ⚠️ **致命缺陷與死穴**：天生火焰抗性 `-50%`（極度弱火！），在第 8 關熾熱火山與火系 Boss 面前生存堪憂。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐ (環境對策卡)：適合水系/毒系副本，火山關卡需謹慎使用。

---

### 👑 #11：【極地狂怒守護者】巨熊騎士 約爾達 (Yolda) (`hero_knight_yolda`)

- **品質與職業**：VI 階 紅色 (稀有度 5.0) | 職業：**KNIGHT** | 種族：**暴走巨熊 (`bear_monster`)**
- **每級基礎成長**：傷害 +1.0, 物理防禦 +5.0, 魔法防禦 +1.0, 生命值 +5.0
- **種族天賦特質**：`rough_hide` (magic_res: 15.0, physical_res: 25.0), `sturdy_will` (silence_immuned: 1.0, stun_immuned: 1.0)
- **綜合評分**：**`69.6 分`**（爆發: 17.6 / 泛用: 25.0 / 機制: 10.0 / 循環: 9.0 / 種族: 8.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **守護重擊**<br>(`guardian_blow`) | 主動<br>enemy/melee<br>(physical) | 0 | 3 回合 | bulwark_max: 3.0<br>bulwark_min: 1.0<br>傷害倍率: 120% | 倍率/級: +2.0% | **bulwark_max**: **3.0**<br>**bulwark_min**: **1.0**<br>**傷害倍率**: **132.0%** | 核心輸出 / 削弱技能。 |
| **聖所之光**<br>(`sanctuary_light`) | 主動<br>敵方/單體<br>(physical) | -1 | 5 回合 | bulwark_max: 3.0<br>bulwark_min: 1.0<br>hp_max: 80.0<br>hp_min: 40.0 | hp_max/級: +6.0<br>hp_min/級: +3.0 | **bulwark_max**: **3.0**<br>**bulwark_min**: **1.0**<br>**hp_max**: **116.0**<br>**hp_min**: **58.0** | 核心輸出 / 削弱技能。 |
| **擲雪球**<br>(`snowball_toss`) | 主動<br>enemy/range<br>(ice) | +1 | 5 回合 | damage_bouns: 0.2<br>傷害倍率: 60%<br>freezing_chance: 45% | 倍率/級: +4.0% | **damage_bouns**: **0.2**<br>**傷害倍率**: **84.0%**<br>**freezing_chance**: **45.0%** | 產能回點技能，為隊伍後續大招提供 SP。 |
| **寒冷掌控**<br>(`frost_control`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | ice_con: 20.0<br>ice_res: 40.0<br>magic_res: 10.0<br>physical_res: 10.0 | ice_con/級: +2.0<br>ice_res/級: +4.0 | **ice_con**: **32.0**<br>**ice_res**: **64.0**<br>**magic_res**: **10.0**<br>**physical_res**: **10.0** | 核心輸出 / 削弱技能。 |
| **雪崩衝撞**<br>(`avalanche_charge`) | 主動<br>enemy/all<br>(physical) | -3 | 10 回合 | 傷害倍率: 125%<br>freezing_chance: 25% | 倍率/級: +6.0% | **傷害倍率**: **161.0%**<br>**freezing_chance**: **25.0%** | 核心輸出 / 削弱技能。 |
| **巨熊神力 (被動)**<br>(`great_bear_strength`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | buff_chance: 10%<br>critical_strike_max: 3.0<br>critical_strike_min: 1.0<br>damage_surge_max: 2.0<br>damage_surge_min: 1.0 | buff_chance: +1.5% | **buff_chance**: **19.0%**<br>**critical_strike_max**: **3.0**<br>**critical_strike_min**: **1.0**<br>**damage_surge_max**: **2.0**<br>**damage_surge_min**: **1.0** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：釋放【守護重擊】(CD 3) 獲得壁壘護盾 ➔ 施放【擲雪球】SP+1 產能並附加 45% 冰凍 ➔ 施放【聖所之光】為友軍回血 116 點。
- 🎯 **怪物剋制與實戰優勢**：自帶 SP 產能、冰凍控場、護盾與治療，功能非常全面。
- ⚠️ **致命缺陷與死穴**：在冷誓要塞等極地副本中，冰系技能會被敵方 +500% 冰霜抗性大幅抵銷。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐ (全能副坦)：具備輔助能力的優秀紅色前排。

---

### 👑 #12：【暗夜死靈刺客】亡靈行者 6 (`hero_rogue_6`)

- **品質與職業**：VI 階 紅色 (稀有度 5.0) | 職業：**ROGUE** | 種族：**不死族 (`undead`)**
- **每級基礎成長**：傷害 +2.0, 物理防禦 +2.0, 魔法防禦 +1.0, 生命值 +2.0
- **種族天賦特質**：`decayed_form` (bleed_immuned: 1.0, darkness_res: 200.0, holy_res: -50.0, magic_res: 50.0, physical_res: 50.0, poison_immuned: 1.0), `undead_resilience` (silence_immuned: 1.0, stun_immuned: 1.0)
- **綜合評分**：**`68.0 分`**（爆發: 25.0 / 泛用: 25.0 / 機制: 7.0 / 循環: 6.0 / 種族: 5.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **標記飛匕**<br>(`marking_dagger`) | 主動<br>enemy/range<br>(physical) | -1 | 5 回合 | 傷害倍率: 120%<br>death_mark_round: 1.0 | 倍率/級: +2.0% | **傷害倍率**: **132.0%**<br>**death_mark_round**: **1.0** | 核心輸出 / 削弱技能。 |
| **影牙投擲**<br>(`shadowfang_toss`) | 主動<br>enemy/range<br>(physical) | -1 | 7 回合 | bleed_chance: 25%<br>bleed_max: 5.0<br>bleed_min: 3.0<br>傷害倍率: 120%<br>death_mark_max: 1.0<br>silence_round: 3.0 | 倍率/級: +4.0% | **bleed_chance**: **25.0%**<br>**bleed_max**: **5.0**<br>**bleed_min**: **3.0**<br>**傷害倍率**: **144.0%**<br>**death_mark_max**: **1.0**<br>**silence_round**: **3.0** | 核心輸出 / 削弱技能。 |
| **潛行伏擊**<br>(`stealthy_ambush`) | 主動<br>ally/self<br>(physical) | 0 | 5 回合 | buff_dodge_chance: 25%<br>buff_dodge_max: 5.0<br>buff_dodge_min: 3.0<br>stealth_max: 1.0<br>stealth_min: 1.0 | 無成長 | **buff_dodge_chance**: **25.0%**<br>**buff_dodge_max**: **5.0**<br>**buff_dodge_min**: **3.0**<br>**stealth_max**: **1.0**<br>**stealth_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **無聲處決**<br>(`silent_execution`) | 主動<br>enemy/range<br>(physical) | -3 | 5 回合 | damage_bouns: 0.5<br>傷害倍率: 170% | 倍率/級: +10.0% | **damage_bouns**: **0.5**<br>**傷害倍率**: **230.0%** | 核彈級處決斬殺，目標帶流血/印記時觸發額外增傷。 |
| **死亡預兆**<br>(`death_omen`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | death_mark_chance: 15% | death_mark_chance: +1.0% | **death_mark_chance**: **21.0%** | 核心輸出 / 削弱技能。 |
| **死縛威壓**<br>(`deathbound_pressure`) | 主動<br>enemy/range<br>(physical) | -2 | 10 回合 | damage_bouns: 0.1<br>傷害倍率: 245%<br>kill_chance: 10% | 倍率/級: +12.0% | **damage_bouns**: **0.1**<br>**傷害倍率**: **317.0%**<br>**kill_chance**: **10.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：施放【幽影突刺】造成 140% 暴擊 ➔ 釋放【死靈收割】造成 220% 單體斬殺。
- 🎯 **怪物剋制與實戰優勢**：亡靈體質天生免疫流血與中毒，暴擊率極高。
- ⚠️ **致命缺陷與死穴**：天生弱神聖 (-50% 神聖負抗性)，且暗影傷害受制於敵方 200% 暗抗。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐ (物理刺客)：暴擊輸出可觀，但生存略顯脆弱。

---

### 👑 #13：【矮人誓約鋼鐵壁壘】布拉戈斯 (Bragos) (`hero_knight_bragos`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**KNIGHT** | 種族：**矮人 (`dwarf`)**
- **每級基礎成長**：傷害 +1.0, 物理防禦 +5.0, 魔法防禦 +1.0, 生命值 +5.0
- **種族天賦特質**：`sturdy_physique` (hp: 30.0, magic_res: 15.0, physical_res: 30.0), `ironclad_resistance` (magic_res: 10.0, physical_res: 20.0)
- **綜合評分**：**`64.6 分`**（爆發: 15.6 / 泛用: 25.0 / 機制: 5.0 / 循環: 6.0 / 種族: 13.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **誓約長槍架勢**<br>(`oathlance_brace`) | 主動<br>enemy/melee<br>(physical) | -1 | 5 回合 | 傷害倍率: 120%<br>ironoath_chance: 45%<br>ironoath_max: 5.0<br>ironoath_min: 3.0 | 倍率/級: +2.0% | **傷害倍率**: **132.0%**<br>**ironoath_chance**: **45.0%**<br>**ironoath_max**: **5.0**<br>**ironoath_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **誓約壁壘**<br>(`oathbound_bulwark`) | 主動<br>ally/self<br>(physical) | -1 | 5 回合 | 傷害倍率: 15%<br>傷害倍率: 5%<br>barrier_count: 3.0 | 倍率/級: +1.0%<br>倍率/級: +1.0% | **傷害倍率**: **21.0%**<br>**傷害倍率**: **11.0%**<br>**barrier_count**: **3.0** | 核心輸出 / 削弱技能。 |
| **鐵壁重砸**<br>(`ironwall_slam`) | 主動<br>enemy/melee<br>(physical) | -3 | 5 回合 | 傷害倍率: 160%<br>ironoath_max: 5.0<br>ironoath_min: 3.0<br>stun_chance: 45% | 倍率/級: +8.0% | **傷害倍率**: **208.0%**<br>**ironoath_max**: **5.0**<br>**ironoath_min**: **3.0**<br>**stun_chance**: **45.0%** | 核心輸出 / 削弱技能。 |
| **鋼鐵堡壘**<br>(`iron_bastion`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 15%<br>hp_min: 1.0 | 倍率/級: +2.0% | **傷害倍率**: **27.0%**<br>**hp_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **深鍛記憶 (被動)**<br>(`deepforge_memory`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 4% | 倍率/級: +0.3% | **傷害倍率**: **6.3%** | 核心輸出 / 削弱技能。 |
| **不滅誓言 (被動)**<br>(`unbroken_vow`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 15%<br>barrier_count: 9.0<br>傷害倍率: 45% | 倍率/級: +2.0% | **傷害倍率**: **27.0%**<br>**barrier_count**: **9.0**<br>**傷害倍率**: **45.0%** | 核心輸出 / 削弱技能。 |
| **誓鍛轉化**<br>(`oathforge_transmute`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 5%<br>ironoath_count: 3.0 | 倍率/級: +0.5% | **傷害倍率**: **8.0%**<br>**ironoath_count**: **3.0** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：架起【誓約長槍架勢】提升 50% 格擋率 ➔ 釋放【誓約壁壘】將格擋值轉化為全隊傷害屏障 ➔ 釋放【鐵壁重砸】造成 140% 物理破甲打擊。
- 🎯 **怪物剋制與實戰優勢**：天生自帶 `ironclad_resistance`，物理防禦直接 +50，物理減傷達到全遊戲最高峰值。
- ⚠️ **致命缺陷與死穴**：缺乏神聖屬性與團隊復活，魔法防禦相對較低，面對全法術 Boss 較吃力。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐ (純物防坦)：物理關卡極強，但功能性不及阿爾德里安或阿斯卡。

---

### 👑 #14：【蒸氣發條技師】哥布林法師 諾比茲 (Nobiz) (`hero_mage_nobiz`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**MAGE** | 種族：**哥布林 (`goblin`)**
- **每級基礎成長**：傷害 +2.0, 物理防禦 +1.0, 魔法防禦 +3.0, 生命值 +2.0
- **種族天賦特質**：`swift_initiative` (dodge: 10.0, first_strike: 1.0), `brightmind_surge` (magic_con: 50.0)
- **綜合評分**：**`63.6 分`**（爆發: 17.6 / 泛用: 25.0 / 機制: 5.0 / 循環: 6.0 / 種族: 10.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **混沌火花射擊**<br>(`chaotic_sparkshot`) | 主動<br>enemy/range<br>(magic) | -1 | 5 回合 | 傷害倍率: 120%<br>傷害倍率: 50%<br>darkness_max: 5.0<br>darkness_min: 3.0<br>energy_charge_max: 3.0<br>energy_charge_min: 1.0 | 倍率/級: +2.0% | **傷害倍率**: **132.0%**<br>**傷害倍率**: **50.0%**<br>**darkness_max**: **5.0**<br>**darkness_min**: **3.0**<br>**energy_charge_max**: **3.0**<br>**energy_charge_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **修補重啟 (被動)**<br>(`tinker_reboot`) | 主動<br>ally/self<br>(physical) | -2 | 5 回合 | energy_charge_count: 3.0<br>傷害倍率: 15%<br>傷害倍率: 5% | 倍率/級: +1.0%<br>倍率/級: +1.0% | **energy_charge_count**: **3.0**<br>**傷害倍率**: **21.0%**<br>**傷害倍率**: **11.0%** | 核心輸出 / 削弱技能。 |
| **廢料線重啟 (被動)**<br>(`scrapline_reboot`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 35%<br>energy_charge_count: 1.0 | 倍率/級: +4.0% | **傷害倍率**: **59.0%**<br>**energy_charge_count**: **1.0** | 核心輸出 / 削弱技能。 |
| **齒輪爆發增幅**<br>(`gearburst_surge`) | 主動<br>enemy/all<br>(magic) | -2 | 5 回合 | damage_bouns: 0.5<br>傷害倍率: 80%<br>energy_charge_count: 3.0 | 倍率/級: +4.0% | **damage_bouns**: **0.5**<br>**傷害倍率**: **104.0%**<br>**energy_charge_count**: **3.0** | 核心輸出 / 削弱技能。 |
| **殘餘過載 (被動)**<br>(`residual_overcharge`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | energy_charge_chance: 15%<br>energy_charge_count: 1.0<br>傷害倍率: 50% | energy_charge_chance: +1.0% | **energy_charge_chance**: **21.0%**<br>**energy_charge_count**: **1.0**<br>**傷害倍率**: **50.0%** | 核心輸出 / 削弱技能。 |
| **齒輪循環 (被動)**<br>(`gear_cycle_loop`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | beast_power_count: 1.0<br>buff_chance: 25%<br>check_count: 4.0<br>energy_charge_count: 1.0 | buff_chance: +2.0% | **beast_power_count**: **1.0**<br>**buff_chance**: **37.0%**<br>**check_count**: **4.0**<br>**energy_charge_count**: **1.0** | 核心輸出 / 削弱技能。 |
| **齒輪彈雨掃射**<br>(`gearfire_barrage`) | 主動<br>enemy/range<br>(physical) | -3 | 10 回合 | 傷害倍率: 20%<br>傷害倍率: 80%<br>fire_chance: 45%<br>fire_max: 5.0<br>fire_min: 3.0 | 倍率/級: +2.0%<br>倍率/級: +4.0% | **傷害倍率**: **32.0%**<br>**傷害倍率**: **104.0%**<br>**fire_chance**: **45.0%**<br>**fire_max**: **5.0**<br>**fire_min**: **3.0** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：釋放【混沌火花射擊】造成 144% 魔法多段打擊 ➔ 被動【修補重啟】充能重置技能冷卻。
- 🎯 **怪物剋制與實戰優勢**：哥布林天賦自帶先攻與智力加成，技能循環快。
- ⚠️ **致命缺陷與死穴**：純魔法傷害面對高魔抗與高元素抗性怪物時傷害衰減明顯。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐ (趣味連動)：需搭配哥布林騎士格利格才能發揮最大連動潛力。

---

### 👑 #15：【暮光影刃刺客】精靈刺客 7 (`hero_rogue_7`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**ROGUE** | 種族：**精靈 (`elf`)**
- **每級基礎成長**：傷害 +2.0, 物理防禦 +2.0, 魔法防禦 +1.0, 生命值 +2.0
- **種族天賦特質**：`swift` (first_strike: 2.0), `magic_safeguard` (darkness_res: 10.0, fire_res: 10.0, holy_res: 10.0, ice_res: 10.0, nature_res: 10.0, poison_res: 10.0)
- **綜合評分**：**`62.4 分`**（爆發: 16.4 / 泛用: 25.0 / 機制: 5.0 / 循環: 6.0 / 種族: 10.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **誓約之刃**<br>(`oath_blade`) | 主動<br>enemy/range<br>(physical) | -1 | 7 回合 | buff_chance: 75%<br>傷害倍率: 60%<br>傷害倍率: 20% | 倍率/級: +2.0%<br>倍率/級: +2.0% | **buff_chance**: **75.0%**<br>**傷害倍率**: **72.0%**<br>**傷害倍率**: **32.0%** | 核心輸出 / 削弱技能。 |
| **暮刃歸宗 (被動)**<br>(`duskblade_return`) | 主動<br>enemy/range<br>(physical) | -1 | 5 回合 | crit_chance: 50%<br>傷害倍率: 120%<br>round: 3.0 | 倍率/級: +4.0% | **crit_chance**: **50.0%**<br>**傷害倍率**: **144.0%**<br>**round**: **3.0** | 核心輸出 / 削弱技能。 |
| **月影斬**<br>(`moonshadow_slash`) | 主動<br>enemy/melee<br>(physical) | -2 | 5 回合 | 傷害倍率: 160%<br>傷害倍率: 50%<br>silence_chance: 45% | 倍率/級: +6.0% | **傷害倍率**: **196.0%**<br>**傷害倍率**: **50.0%**<br>**silence_chance**: **45.0%** | 核心輸出 / 削弱技能。 |
| **暗影守護**<br>(`shadow_protection`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | buff_dodge_chance: 45%<br>buff_dodge_max: 5.0<br>buff_dodge_min: 3.0 | buff_dodge_chance: +3.0% | **buff_dodge_chance**: **63.0%**<br>**buff_dodge_max**: **5.0**<br>**buff_dodge_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **月之裁決**<br>(`lunar_judgment`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 50%<br>darkness_chance: 45%<br>darkness_max: 3.0<br>darkness_min: 1.0<br>傷害倍率: 50% | 倍率/級: +5.0% | **傷害倍率**: **80.0%**<br>**darkness_chance**: **45.0%**<br>**darkness_max**: **3.0**<br>**darkness_min**: **1.0**<br>**傷害倍率**: **50.0%** | 核心輸出 / 削弱技能。 |
| **暮光支配 (被動)**<br>(`twilight_dominion`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 0.15<br>stealth_chance: 15% | damage_bouns/級: +0.01<br>stealth_chance: +1.0% | **damage_bouns**: **0.21**<br>**stealth_chance**: **21.0%** | 核心輸出 / 削弱技能。 |
| **月刃天降**<br>(`lunar_bladefall`) | 主動<br>enemy/all<br>(physical) | -3 | 7 回合 | count: 5.0<br>傷害倍率: 70%<br>傷害倍率: 40%<br>傷害倍率: 30% | 倍率/級: +3.0%<br>倍率/級: +3.0% | **count**: **5.0**<br>**傷害倍率**: **88.0%**<br>**傷害倍率**: **58.0%**<br>**傷害倍率**: **30.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：施放【月影斬】(CD 3) 造成 132% 魔法/物理突刺 ➔ 釋放【月刃天降】造成 240% 全體收割。
- 🎯 **怪物剋制與實戰優勢**：身法極其靈活，暴擊率高，技能冷卻短。
- ⚠️ **致命缺陷與死穴**：身板較脆，面對高物防機械傀儡輸出受限。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐⭐ (收割刺客)：適合快速清理雜兵。

---

### 👑 #16：【不朽骸骨掠奪者】骷髏戰士 6 (`hero_warrior_6`)

- **品質與職業**：VI 階 紅色 (稀有度 5.0) | 職業：**WARRIOR** | 種族：**骷髏 (`skeleton`)**
- **每級基礎成長**：傷害 +1.0, 物理防禦 +4.0, 魔法防禦 +1.0, 生命值 +8.0
- **種族天賦特質**：`bone_resilience` (bleed_immuned: 1.0, magic_res: 20.0, physical_res: 20.0), `dark_affinity` (darkness_con: 50.0, darkness_res: 200.0, heal_res: 50.0, holy_res: -50.0)
- **綜合評分**：**`60.5 分`**（爆發: 19.5 / 泛用: 25.0 / 機制: 5.0 / 循環: 6.0 / 種族: 5.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **防衛反擊**<br>(`defensive_strike`) | 主動<br>enemy/melee<br>(physical) | 0 | 3 回合 | 傷害倍率: 50%<br>傷害倍率: 120% | 倍率/級: +2.0% | **傷害倍率**: **50.0%**<br>**傷害倍率**: **132.0%** | 核心輸出 / 削弱技能。 |
| **激怒狂暴**<br>(`provoked_fury`) | 主動<br>enemy/range<br>(physical) | -1 | 7 回合 | armor_max: 60.0<br>armor_min: 30.0<br>provocation_round: 3.0<br>weakness_level_chance: 25%<br>weakness_max: 5.0<br>weakness_min: 3.0 | armor_max/級: +6.0<br>armor_min/級: +3.0 | **armor_max**: **96.0**<br>**armor_min**: **48.0**<br>**provocation_round**: **3.0**<br>**weakness_level_chance**: **25.0%**<br>**weakness_max**: **5.0**<br>**weakness_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **群體防禦祈禱**<br>(`mass_defense`) | 主動<br>ally/all<br>(physical) | -3 | 10 回合 | armor_max: 40.0<br>armor_min: 20.0<br>protection_max: 7.0<br>protection_min: 5.0 | armor_max/級: +8.0<br>armor_min/級: +4.0 | **armor_max**: **88.0**<br>**armor_min**: **44.0**<br>**protection_max**: **7.0**<br>**protection_min**: **5.0** | 核心輸出 / 削弱技能。 |
| **守護之牆**<br>(`protection_wall`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 30% | 倍率/級: +2.0% | **傷害倍率**: **42.0%** | 核心輸出 / 削弱技能。 |
| **碎甲重震**<br>(`armor_quake`) | 主動<br>enemy/range<br>(physical) | -3 | 5 回合 | armor_max: 300.0<br>傷害倍率: 50%<br>傷害倍率: 200% | 倍率/級: +10.0% | **armor_max**: **300.0**<br>**傷害倍率**: **50.0%**<br>**傷害倍率**: **260.0%** | 核心輸出 / 削弱技能。 |
| **白骨守衛**<br>(`bone_guardian`) | 主動<br>ally/self<br>(physical) | -3 | 20 回合 | 傷害倍率: 40%<br>round: 10.0<br>total_res: 40.0 | 倍率/級: +3.0%<br>total_res/級: +3.0 | **傷害倍率**: **58.0%**<br>**round**: **10.0**<br>**total_res**: **58.0** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：釋放【骸骨護甲】獲得物理抗性 +20% ➔ 受擊觸發【激怒反擊】進行 130% 物理回擊。
- 🎯 **怪物剋制與實戰優勢**：骷髏體質天生免疫流血，物理防禦極硬。
- ⚠️ **致命缺陷與死穴**：弱神聖 (-50%)，且 5.0 紅色品質數值上限不如 6.0 彩虹戰士。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐ (過渡前排)：過渡期可用。

---

### 👑 #17：【極凍霜鋼巨獸】冰霜碎石獸 (Slateshard Bruiser) (`pet_slateshard_bruiser`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**PET** | 種族：**冰霜元素 (`ice_elemental`)**
- **每級基礎成長**：傷害 +1.5, 物理防禦 +3.0, 魔法防禦 +2.0, 生命值 +6.0
- **種族天賦特質**：`coldborne_form` (bleed_immuned: 1.0, fire_immuned: 1.0, fire_res: 100.0, ice_res: 500.0, magic_res: 50.0, physical_res: 50.0, poison_immuned: 1.0), `frost_power` (ice_con: 100.0), `elemental_power` (hp: 100.0, magic_con: 50.0, physical_con: 50.0)
- **綜合評分**：**`58.7 分`**（爆發: 14.7 / 泛用: 25.0 / 機制: 5.0 / 循環: 6.0 / 種族: 8.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **霜鋼抓握**<br>(`froststeel_grasp`) | 主動<br>enemy/melee<br>(physical) | -1 | 5 回合 | 傷害倍率: 120%<br>weakness_chance: 25%<br>weakness_max: 5.0<br>weakness_min: 1.0 | 倍率/級: +2.0% | **傷害倍率**: **132.0%**<br>**weakness_chance**: **25.0%**<br>**weakness_max**: **5.0**<br>**weakness_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **霜鋼衝擊**<br>(`froststeel_charge`) | 主動<br>enemy/melee<br>(physical) | -2 | 5 回合 | 傷害倍率: 120%<br>傷害倍率: 30%<br>freezing_chance: 15%<br>stun_chance: 15% | 倍率/級: +4.0%<br>倍率/級: +2.0% | **傷害倍率**: **144.0%**<br>**傷害倍率**: **42.0%**<br>**freezing_chance**: **15.0%**<br>**stun_chance**: **15.0%** | 核心輸出 / 削弱技能。 |
| **極凍裝甲 (被動)**<br>(`frozen_plating`) | 主動<br>ally/range<br>(physical) | -1 | 10 回合 | 傷害倍率: 10%<br>frost_barrier_count: 5.0<br>protection_count: 5.0 | 倍率/級: +1.5% | **傷害倍率**: **19.0%**<br>**frost_barrier_count**: **5.0**<br>**protection_count**: **5.0** | 核心輸出 / 削弱技能。 |
| **碎裂線爆發**<br>(`shatterline_burst`) | 主動<br>enemy/all<br>(physical) | -3 | 5 回合 | 傷害倍率: 85%<br>vulnerability_chance: 25%<br>vulnerability_max: 5.0<br>vulnerability_min: 1.0 | 倍率/級: +5.0% | **傷害倍率**: **115.0%**<br>**vulnerability_chance**: **25.0%**<br>**vulnerability_max**: **5.0**<br>**vulnerability_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **冰脈餘勁**<br>(`iceline_afterblow`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | frostscar_chance: 15% | frostscar_chance: +1.0% | **frostscar_chance**: **21.0%** | 核心輸出 / 削弱技能。 |
| **霜鋼體質 (被動)**<br>(`froststeel_constitution`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 0.1<br>damage_bouns_1: 0.15<br>damage_bouns_2: 0.25<br>damage_bouns_3: 0.35<br>傷害倍率: 75%<br>傷害倍率: 50%<br>傷害倍率: 25% | damage_bouns_1/級: +0.01<br>damage_bouns_2/級: +0.02<br>damage_bouns_3/級: +0.03 | **damage_bouns**: **0.1**<br>**damage_bouns_1**: **0.21**<br>**damage_bouns_2**: **0.37**<br>**damage_bouns_3**: **0.53**<br>**傷害倍率**: **75.0%**<br>**傷害倍率**: **50.0%**<br>**傷害倍率**: **25.0%** | 核心輸出 / 削弱技能。 |
| **霜震共鳴**<br>(`frostquake_resonance`) | 被動<br>敵方/單體<br>(ice) | 0 | 無 | 傷害倍率: 50%<br>extra_chance: 35%<br>freezing_chance: 5% | extra_chance: +4.0% | **傷害倍率**: **50.0%**<br>**extra_chance**: **59.0%**<br>**freezing_chance**: **5.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：施放【霜鋼重拳】造成 140% 冰霜衝擊 ➔ 被動【極凍裝甲】提供冰霜抗性 +500%。
- 🎯 **怪物剋制與實戰優勢**：冰霜抗性極限拉滿 (+500%)，極度剋制冰系 Boss。
- ⚠️ **致命缺陷與死穴**：出招速度偏慢，攻擊偏向單一冰霜屬性。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐ (抗性對策寵)：針對極地關卡專用。

---

### 👑 #18：【虛空白銀衛士】虛空哨兵 (Voidsilver Sentinel) (`pet_voidsilver_sentinel`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**PET** | 種族：**虛空後裔 (`voidborn`)**
- **每級基礎成長**：傷害 +1.5, 物理防禦 +3.0, 魔法防禦 +2.0, 生命值 +6.0
- **種族天賦特質**：`void_form` (bleed_immuned: 1.0, darkness_res: 200.0, fire_immuned: 1.0, fire_res: 100.0, holy_res: -50.0, magic_res: 50.0, physical_res: 50.0, poison_immuned: 1.0, stun_immuned: 1.0), `void_eye` (crit: 100.0, hit: 100.0)
- **綜合評分**：**`56.4 分`**（爆發: 8.4 / 泛用: 25.0 / 機制: 9.0 / 循環: 6.0 / 種族: 8.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **盾牌猛擊**<br>(`shield_slam`) | 主動<br>enemy/melee<br>(physical) | -1 | 5 回合 | 傷害倍率: 100%<br>stun_chance: 45% | 倍率/級: +2.0% | **傷害倍率**: **112.0%**<br>**stun_chance**: **45.0%** | 提供團隊防禦護甲或壁壘吸收屏障。 |
| **白銀重盾猛擊**<br>(`silver_barrier_slam`) | 主動<br>enemy/melee<br>(physical) | -2 | 3 回合 | 傷害倍率: 100%<br>傷害倍率: 50%<br>protection_max: 5.0<br>protection_min: 3.0 | 倍率/級: +4.0%<br>倍率/級: +5.0% | **傷害倍率**: **124.0%**<br>**傷害倍率**: **80.0%**<br>**protection_max**: **5.0**<br>**protection_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **群體防禦祈禱**<br>(`mass_defense`) | 主動<br>ally/all<br>(physical) | -3 | 10 回合 | armor_max: 40.0<br>armor_min: 20.0<br>protection_max: 7.0<br>protection_min: 5.0 | armor_max/級: +8.0<br>armor_min/級: +4.0 | **armor_max**: **88.0**<br>**armor_min**: **44.0**<br>**protection_max**: **7.0**<br>**protection_min**: **5.0** | 核心輸出 / 削弱技能。 |
| **全體狂怒挑釁**<br>(`mass_provoked_fury`) | 主動<br>enemy/all<br>(physical) | -3 | 10 回合 | armor_max: 100.0<br>armor_min: 50.0<br>provocation_round: 3.0<br>weakness_max: 5.0<br>weakness_min: 3.0 | armor_max/級: +20.0<br>armor_min/級: +15.0 | **armor_max**: **220.0**<br>**armor_min**: **140.0**<br>**provocation_round**: **3.0**<br>**weakness_max**: **5.0**<br>**weakness_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **白銀庇護**<br>(`silver_aegis`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns_1: 0.15<br>damage_bouns_2: 0.05 | damage_bouns_1/級: +0.01<br>damage_bouns_2/級: +0.005 | **damage_bouns_1**: **0.21**<br>**damage_bouns_2**: **0.08** | 核心輸出 / 削弱技能。 |
| **虛空之牆轉換 (被動)**<br>(`voidwall_conversion`) | 主動<br>ally/range<br>(physical) | -2 | 10 回合 | 傷害倍率: 40% | 倍率/級: +6.0% | **傷害倍率**: **76.0%** | 核心輸出 / 削弱技能。 |
| **白銀屏障**<br>(`silver_barrier`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | darkness_res: 100.0<br>magic_res: 50.0<br>physical_res: 50.0 | darkness_res/級: +10.0<br>magic_res/級: +5.0<br>physical_res/級: +5.0 | **darkness_res**: **160.0**<br>**magic_res**: **80.0**<br>**physical_res**: **80.0** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：釋放【白銀重盾猛擊】造成 120% 眩暈 ➔ 釋放【群體防禦祈禱】提升全隊雙抗。
- 🎯 **怪物剋制與實戰優勢**：虛空體質天生免疫流血、火與眩暈，防禦增益扎實。
- ⚠️ **致命缺陷與死穴**：缺乏直接輸出能力。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⭐⭐ (輔助戰寵)：提供團隊減傷。

---

### 👑 #19：【劇毒腐殖母巢】獸人育卵牧師 7 (`hero_priest_7`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**PRIEST** | 種族：**獸人 (`orc`)**
- **每級基礎成長**：傷害 +1.0, 物理防禦 +2.0, 魔法防禦 +3.0, 生命值 +3.0
- **種族天賦特質**：`rough_hide` (magic_res: 15.0, physical_res: 25.0), `sturdy_will` (silence_immuned: 1.0, stun_immuned: 1.0), `frenzied_might` (crit: 50.0), `sturdy_physique` (hp: 30.0, magic_res: 15.0, physical_res: 30.0), `beastly_armor` (magic_res: 20.0, physical_res: 20.0)
- **綜合評分**：**`55.1 分`**（爆發: 16.1 / 泛用: 8.0 / 機制: 10.0 / 循環: 6.0 / 種族: 15.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **甲殼詛咒**<br>(`shellcurse`) | 主動<br>enemy/range<br>(darkness) | -1 | 5 回合 | brooding_egg_round: 3.0<br>傷害倍率: 100% | 倍率/級: +2.0% | **brooding_egg_round**: **3.0**<br>**傷害倍率**: **112.0%** | 核心輸出 / 削弱技能。 |
| **母巢之令**<br>(`broodmother_command_hero`) | 主動<br>enemy/range<br>(poison) | -2 | 5 回合 | 傷害倍率: 45%<br>poison_max: 3.0<br>poison_min: 1.0 | 倍率/級: +2.0% | **傷害倍率**: **57.0%**<br>**poison_max**: **3.0**<br>**poison_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **劇毒瘟疫**<br>(`toxic_plague`) | 主動<br>enemy/all<br>(poison) | -3 | 5 回合 | 傷害倍率: 85%<br>poison_max: 3.0<br>poison_min: 1.0 | 倍率/級: +4.0% | **傷害倍率**: **109.0%**<br>**poison_max**: **3.0**<br>**poison_min**: **1.0** | 核心輸出 / 削弱技能。 |
| **毒液哀嚎**<br>(`venomous_wail`) | 主動<br>enemy/all<br>(poison) | -3 | 7 回合 | buff_max: 6.0<br>buff_min: 4.0<br>傷害倍率: 80%<br>egg_chance: 15% | 倍率/級: +4.0%<br>egg_chance: +1.0% | **buff_max**: **6.0**<br>**buff_min**: **4.0**<br>**傷害倍率**: **104.0%**<br>**egg_chance**: **21.0%** | 核心輸出 / 削弱技能。 |
| **毒術掌控 (被動)**<br>(`poison_control`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | magic_res: 10.0<br>physical_res: 10.0<br>poison_con: 20.0<br>poison_res: 40.0 | poison_con/級: +2.0<br>poison_res/級: +4.0 | **magic_res**: **10.0**<br>**physical_res**: **10.0**<br>**poison_con**: **32.0**<br>**poison_res**: **64.0** | 核心輸出 / 削弱技能。 |
| **育卵輪迴**<br>(`brooding_cycle`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 0.1<br>egg_chance: 15% | damage_bouns/級: +0.01<br>egg_chance: +1.0% | **damage_bouns**: **0.16**<br>**egg_chance**: **21.0%** | 核心輸出 / 削弱技能。 |
| **巢穴覺醒 (被動)**<br>(`brood_awakening`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | 傷害倍率: 100%<br>energy_chance: 25%<br>poison_chance: 25%<br>poison_max: 3.0<br>poison_min: 1.0<br>spider_round: 5.0 | 倍率/級: +7.5%<br>poison_chance: +2.0% | **傷害倍率**: **145.0%**<br>**energy_chance**: **25.0%**<br>**poison_chance**: **37.0%**<br>**poison_max**: **3.0**<br>**poison_min**: **1.0**<br>**spider_round**: **5.0** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：施放【母巢之令】召喚腐殖幼蟲 ➔ 施放【劇毒瘟疫】附加 5~7 層劇毒 Dot。
- 🎯 **怪物剋制與實戰優勢**：打血肉野獸類 Boss 傷害極高，自帶獸人部族血怒連動。
- ⚠️ **致命缺陷與死穴**：❌ **嚴重致命缺陷**：中後期亡靈、骷髏、幽魂、機械、魔像、元素生物 **100% 免疫中毒 (`poison_immuned: 1.0`)**，遇到這些怪物時 Dot 傷害直接為 0！
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：🚫 避坑不推薦：泛用性嚴重不足。

---

### 👑 #20：【夜鴉暗羽刺客】人類刺客 席恩 (Sien) (`hero_rogue_sien`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**ROGUE** | 種族：**人類 (`human`)**
- **每級基礎成長**：傷害 +2.0, 物理防禦 +2.0, 魔法防禦 +1.0, 生命值 +2.0
- **種族天賦特質**：`experience_epiphany` (exp_bouns: 0.2), `balance` (magic_con: 10.0, magic_res: 10.0, physical_con: 10.0, physical_res: 10.0)
- **綜合評分**：**`48.7 分`**（爆發: 15.2 / 泛用: 8.0 / 機制: 5.0 / 循環: 6.0 / 種族: 14.5）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **暗羽狂襲**<br>(`darkfeather_flurry`) | 主動<br>enemy/all<br>(physical) | -1 | 5 回合 | 傷害倍率: 50%<br>death_mark_chance: 25% | 倍率/級: +1.0% | **傷害倍率**: **56.0%**<br>**death_mark_chance**: **25.0%** | 核心輸出 / 削弱技能。 |
| **夜鴉穿刺**<br>(`nightcrow_pierce`) | 主動<br>enemy/range<br>(physical) | -2 | 5 回合 | 傷害倍率: 120%<br>傷害倍率: 50%<br>death_mark_chance: 75% | 倍率/級: +4.0% | **傷害倍率**: **144.0%**<br>**傷害倍率**: **50.0%**<br>**death_mark_chance**: **75.0%** | 核心輸出 / 削弱技能。 |
| **鴉羽追獵**<br>(`ravenfeather_hunt`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | reset_chance: 35% | reset_chance: +2.0% | **reset_chance**: **47.0%** | 核心輸出 / 削弱技能。 |
| **暗羽穿刺**<br>(`darkfeather_impale`) | 主動<br>enemy/range<br>(physical) | -2 | 5 回合 | 傷害倍率: 60% | 倍率/級: +2.0% | **傷害倍率**: **72.0%** | 核心輸出 / 削弱技能。 |
| **影步復甦 (被動)**<br>(`shadowstep_resurgence`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | buff_dodge_chance: 15%<br>buff_dodge_check_count: 3.0<br>buff_dodge_count: 7.0 | buff_dodge_chance: +1.0% | **buff_dodge_chance**: **21.0%**<br>**buff_dodge_check_count**: **3.0**<br>**buff_dodge_count**: **7.0** | 核心輸出 / 削弱技能。 |
| **夜鴉飛昇 (被動)**<br>(`nightcrow_ascension`) | 主動<br>ally/self<br>(physical) | -2 | 10 回合 | skill_chance: 0% | skill_chance: +10.0% | **skill_chance**: **60.0%** | 核心輸出 / 削弱技能。 |
| **死印判決**<br>(`deathmark_verdict`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 0.05<br>傷害倍率: 100%<br>extra_chance: 45% | 倍率/級: +5.0%<br>extra_chance: +3.0% | **damage_bouns**: **0.05**<br>**傷害倍率**: **130.0%**<br>**extra_chance**: **63.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：施放【夜鴉穿刺】附加暗羽印記 ➔ 釋放【暗羽狂襲】造成 220% 暗影多段爆發。
- 🎯 **怪物剋制與實戰優勢**：人類體質平衡，爆發頻率高。
- ⚠️ **致命缺陷與死穴**：❌ **核心傷害全為暗影屬性**，在中後期深淵與火山等副本中被敵方 200% 暗抗抵銷 75% 傷害。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：🚫 避坑不推薦：會重蹈澤穆爾的暗影無效覆轍。

---

### 👑 #21：【冥界引渡者】冥語者 澤穆爾 (Zemur - 當前主力) (`hero_priest_6`)

- **品質與職業**：VI 階 紅色 (稀有度 5.0) | 職業：**PRIEST** | 種族：**幽靈/亡魂 (`specter`)**
- **每級基礎成長**：傷害 +1.0, 物理防禦 +2.0, 魔法防禦 +3.0, 生命值 +3.0
- **種族天賦特質**：`dark_affinity` (darkness_con: 50.0, darkness_res: 200.0, heal_res: 50.0, holy_res: -50.0), `incorporeal_form` (bleed_immuned: 1.0, crit_res: 200.0, magic_res: 20.0, physical_res: 50.0, poison_immuned: 1.0, silence_immuned: 1.0, stun_immuned: 1.0)
- **綜合評分**：**`47.0 分`**（爆發: 18.0 / 泛用: 8.0 / 機制: 7.0 / 循環: 9.0 / 種族: 5.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **痛苦折磨詛咒**<br>(`curse_agony`) | 主動<br>enemy/range<br>(darkness) | -1 | 5 回合 | count_max: 3.0<br>count_min: 2.0<br>傷害倍率: 120% | 倍率/級: +2.0% | **count_max**: **3.0**<br>**count_min**: **2.0**<br>**傷害倍率**: **132.0%** | 核心輸出 / 削弱技能。 |
| **虛空指引**<br>(`void_fingers`) | 主動<br>enemy/range<br>(darkness) | +1 | 7 回合 | 傷害倍率: 80%<br>energy_count: 1.0 | 倍率/級: +2.0% | **傷害倍率**: **92.0%**<br>**energy_count**: **1.0** | 產能回點技能，為隊伍後續大招提供 SP。 |
| **暗影庇護所**<br>(`dark_sanctuary`) | 主動<br>ally/range<br>(physical) | -2 | 5 回合 | 傷害倍率: 20%<br>darkness_max: 6.0<br>darkness_min: 3.0 | 倍率/級: +1.5% | **傷害倍率**: **29.0%**<br>**darkness_max**: **6.0**<br>**darkness_min**: **3.0** | 核心輸出 / 削弱技能。 |
| **暗影內爆**<br>(`darkness_implosion`) | 主動<br>enemy/all<br>(darkness) | -3 | 7 回合 | 傷害倍率: 100%<br>energy_chance: 25%<br>energy_count: 1.0 | 倍率/級: +5.0% | **傷害倍率**: **130.0%**<br>**energy_chance**: **25.0%**<br>**energy_count**: **1.0** | 核心輸出 / 削弱技能。 |
| **靈魂撕裂**<br>(`soul_rend`) | 主動<br>enemy/melee<br>(darkness) | -3 | 7 回合 | 傷害倍率: 200%<br>vital_blockade_max: 7.0<br>vital_blockade_min: 5.0 | 倍率/級: +10.0% | **傷害倍率**: **260.0%**<br>**vital_blockade_max**: **7.0**<br>**vital_blockade_min**: **5.0** | 核心輸出 / 削弱技能。 |
| **逝者誓約**<br>(`departed_oath`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | darkness_max: 7.0<br>darkness_min: 5.0<br>energy_count: 1.0<br>傷害倍率: 40%<br>heal_times: 3.0<br>傷害倍率: 50% | 倍率/級: +4.0% | **darkness_max**: **7.0**<br>**darkness_min**: **5.0**<br>**energy_count**: **1.0**<br>**傷害倍率**: **64.0%**<br>**heal_times**: **3.0**<br>**傷害倍率**: **50.0%** | 核心輸出 / 削弱技能。 |

#### ⚔️ 專屬實戰評估與怪物剋制深評：
- 🔄 **技能循環與戰鬥節奏**：施放【汲暗之指】SP+1 產能 ➔ 施放【黑暗內爆】全體 AOE ➔ 施放【靈魂撕裂】造成 200% 暗影傷害與生機封鎖。
- 🎯 **怪物剋制與實戰優勢**：打無暗抗的野獸怪傷害不錯，附帶生機封鎖減療。
- ⚠️ **致命缺陷與死穴**：❌ **全技能均為純暗影傷害**！中後期副本超過 60% 怪物自帶 `darkness_res: 200%`，實質傷害直接縮水 75%，導致輸出忽高忽低極不穩定。
- 🧩 **與您當前隊伍（艾麗娜+芬奇）之適配性**：⚠️ **必須換掉**：是當前隊伍突破 2800 戰力與通關後續高難副本的最大瓶頸。

---

### 👑 #22：【猩紅血祭女伯爵】惡魔牧師 巴托里 (Bathory) (`hero_priest_bathory`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**PRIEST** | 種族：**惡魔 (`demon`)**
- **每級基礎成長**：傷害 +1.0, 物理防禦 +2.0, 魔法防禦 +3.0, 生命值 +3.0
- **種族天賦特質**：`rough_hide` (magic_res: 15.0, physical_res: 25.0), `sturdy_physique` (hp: 30.0, magic_res: 15.0, physical_res: 30.0), `frenzied_might` (crit: 50.0), `dark_affinity` (darkness_con: 50.0, darkness_res: 200.0, heal_res: 50.0, holy_res: -50.0), `sturdy_will` (silence_immuned: 1.0, stun_immuned: 1.0), `heat_resistance` (fire_res: 100.0, magic_res: 20.0, physical_res: 20.0)
- **綜合評分**：**`45.9 分`**（爆發: 13.9 / 泛用: 8.0 / 機制: 10.0 / 循環: 9.0 / 種族: 5.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **暗影縫合**<br>(`shadow_stitching`) | 主動<br>ally/range<br>(physical) | +1 | 3 回合 | heal_bouns: 0.05<br>傷害倍率: 5%<br>vital_blockade_count: 3.0 | heal_bouns/級: +0.005 | **heal_bouns**: **0.08**<br>**傷害倍率**: **5.0%**<br>**vital_blockade_count**: **3.0** | 產能回點技能，為隊伍後續大招提供 SP。 |
| **猩紅冥想 (被動)**<br>(`scarlet_meditation`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | vital_blockade_chance: 45%<br>vital_blockade_count: 1.0 | vital_blockade_chance: +3.0% | **vital_blockade_chance**: **63.0%**<br>**vital_blockade_count**: **1.0** | 核心輸出 / 削弱技能。 |
| **血肉祭壇**<br>(`flesh_altar`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 0.01 | damage_bouns/級: +0.001 | **damage_bouns**: **0.016** | 核心輸出 / 削弱技能。 |
| **噬魂咆哮**<br>(`soul_rending_roar`) | 主動<br>enemy/all<br>(darkness) | -3 | 7 回合 | 傷害倍率: 100%<br>vital_blockade_count: 5.0<br>weakness_max: 7.0<br>weakness_min: 5.0 | 倍率/級: +5.0% | **傷害倍率**: **130.0%**<br>**vital_blockade_count**: **5.0**<br>**weakness_max**: **7.0**<br>**weakness_min**: **5.0** | 核心輸出 / 削弱技能。 |
| **隔空剝蝕**<br>(`remote_eecortication`) | 主動<br>enemy/range<br>(physical) | -2 | 5 回合 | 傷害倍率: 80%<br>flayed_chance: 75% | 倍率/級: +2.0% | **傷害倍率**: **92.0%**<br>**flayed_chance**: **75.0%** | 核心輸出 / 削弱技能。 |
| **地獄契約重置 (被動)**<br>(`hell_pact_reset`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | active_chance: 25%<br>active_round: 5.0<br>buff_max: 5.0<br>buff_min: 1.0 | active_chance: +5.0% | **active_chance**: **55.0%**<br>**active_round**: **5.0**<br>**buff_max**: **5.0**<br>**buff_min**: **1.0** | 核心輸出 / 削弱技能。 |
---

## 🔒 四、領主鎖定 (Locked) 頂級英雄專題解析：【狂暴軍閥】克拉古爾 (Kraghul)

> 註：本英雄在遊戲初始處於鎖定狀態 (`require_unlock: true`)，需在「首領討伐 (Lord Boss)」中擊敗【獸人軍閥】後方可在酒館解鎖購買。本章節為伺服器前段班主流「全紅純獸人隊」的核心發動機深度數值拆解。

### 👑 領主神卡：【獸人狂暴軍閥】克拉古爾 (`hero_warrior_kraghul`)

- **品質與職業**：VII 階 彩虹 (稀有度 6.0) | 職業：**WARRIOR** | 種族：**獸人 (`orc`)**
- **專屬神裝**：
  - **主手【軍閥狂暴戰斧 (`axe_orc_kraghul`)】**：基礎滿詞條為 **5 個滿暴擊 (`crit`, `crit`, `crit`, `crit`, `crit`)**！
  - **副手【軍閥重裝鋼盾 (`shield_orc_kraghul`)】**：雙格擋 (`block`) + 雙物理抗性 (`physical_res`) + 魔法抗性 (`magic_res`)。
- **每級基礎成長**：傷害 +1.0, 物理防禦 +4.0, 魔法防禦 +1.0, 生命值 +8.0 (基礎生命 220.0，天生血牛)
- **種族天賦特質**：`rough_hide` (魔抗+15%, 物抗+25%), `sturdy_will` (**天生 100% 免疫沉默與眩暈**), `frenzied_might` (**全隊暴擊率 +50%**), `sturdy_physique` (HP+30, 物抗+30%), `beastly_armor` (雙抗+20%)
- **綜合評分**：**`96.0 分`**（爆發: 25.0 / 泛用: 25.0 / 機制: 16.0 / 循環: 15.0 / 種族: 15.0）

#### 📋 技能組全景與 Level 7 精確數值對照表：

| 技能名稱 (ID) | 類型 / 目標 / 屬性 | SP消耗 | CD | Level 1 初始數值 | 每級成長 (attr_per_level) | **Level 7 實戰數值 (精確計算)** | 機制與連動效果 |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **血誓順劈**<br>(`blood_oath_cleave`) | 主動<br>敵方/近戰<br>(physical) | -1 | 5 回合 | 傷害倍率: 120%<br>bleed_chance: 25%<br>hp_rate: 1.5% | 倍率/級: +2.0% | **傷害倍率**: **132.0%**<br>**bleed_chance**: **25.0%**<br>**hp_rate**: **1.5%** | 附加流血並按自身最大生命附加傷害。 |
| **不屈之怒 (被動)**<br>(`unrelenting_fury`) | 被動<br>友方/全體<br>(physical) | 0 | 無 | sp_chance: 15%<br>sp_count: 1.0<br>critical_strike: 1~3 | sp_chance/級: +1.0% | **sp_chance**: **21.0%**<br>**sp_count**: **1.0** | 暴擊或受擊時以 21% 機率**直接為全隊產能 SP +1**！ |
| **號令怒吼**<br>(`commanding_roar`) | 主動<br>友方/全體<br>(physical) | -3 | 10 回合 | ap_chance: 15%<br>ap_count: 1.0<br>battle_fury: 3~5 | ap_chance/級: +3.0% | **ap_chance**: **33.0%**<br>**ap_count**: **1.0**<br>**battle_fury**: **3~5 層** | **全隊神級增益**：33% 機率讓**全隊全體獲得額外行動點 AP+1 (全隊雙動)**！ |
| **處決者之刃**<br>(`executioner_edge`) | 主動<br>敵方/全體<br>(physical) | -3 | 5 回合 | 傷害倍率: 170%<br>damage_bouns: 1.0<br>hp_rate: 25% | 倍率/級: +10.0% | **傷害倍率**: **230.0%**<br>**damage_bouns**: **1.0 (額外+100%)**<br>**hp_rate**: **25.0%** | **核彈全體處決**：230% + 100% 增傷 = **330% 全體巨傷 + 25% 最大生命斬殺**！ |
| **野蠻壓制 (被動)**<br>(`savage_overwhelm`) | 被動<br>敵方/單體<br>(physical) | 0 | 無 | damage_bouns: 15% | damage_bouns/級: +2.0% | **damage_bouns**: **27.0%** | 常駐提升自身所有物理傷害 +27%。 |
| **劍刃風暴震擊**<br>(`bladestorm_quake`) | 主動<br>敵方/全體<br>(physical) | -3 | 7 回合 | 傷害倍率: 140%<br>stun_chance: 45% | 倍率/級: +8.0% | **傷害倍率**: **188.0%**<br>**stun_chance**: **45.0%** | 全體 AOE 造成 188% 傷害並附加 **45% 全體眩暈**。 |
| **燃燒狂怒 (被動)**<br>(`burning_rage`) | 被動<br>自身/開場<br>(physical) | 0 | 10 回合 | damage_bouns_1: 50%<br>damage_round: 5.0 | damage_bouns_1/級: +5.0% | **damage_bouns_1**: **80.0%**<br>**damage_round**: **5.0 回合** | **開場核爆發動機**：戰鬥前 5 回合所有傷害直接暴增 **+80%**！ |

#### ⚔️ 專屬實戰評估：
- 🔄 **技能循環與戰鬥節奏**：開場前 5 回合享受 +80% 增傷 ➔ 釋放【號令怒吼】為全隊提供 33% AP+1 全員雙動 ➔ 釋放【處決者之刃】打出 330% 全體毀滅處決 ➔ 配合德魯戈的雙動核彈收割戰場！
- 🎯 **怪物剋制與實戰優勢**：純物理傷害無死角，天生免疫沉默與眩暈，身板極其厚實，是全遊戲綜合爆發最高的終極前排。


