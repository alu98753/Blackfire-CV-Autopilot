# ⚔️ 全遊戲狀態效果與 BUFF/DEBUFF 完整機制手冊

> **數據來源**：[`meta_data/raw_tres/meta_datas.tres`](../../raw_tres/meta_datas.tres)  
> **更新時間**：2026-08-29  
> **涵蓋範圍**：全 61 種戰鬥狀態效果（控制、持續傷害 DoT、易傷印記、輸出增益、防禦護甲、抗性免疫）。

---

## 💡 核心底層結算與免疫規則 (Core Combat Rules)

1. **自帶免疫防連環控 (Inherent Immunity in Hard CC)**：
   - **沉默 (`silence`)**：狀態自帶 `silence_immuned: 1.0`。在被沉默的持續期間內，**英雄對二次沉默 100% 免疫**，無法被疊加第二層沉默或在未解除前刷新！解除後即恢復可受控狀態。
   - **暈眩 (`stun`)**：狀態自帶 `stun_immuned: 1.0`。在被暈眩的當前階段，**英雄對二次暈眩 100% 免疫**，防止被連續暈眩鎖死。

2. **DoT 疊層規則 (`merge` 屬性)**：
   - `merge: false`（如 `bleed`、`poison`、`fire`、`sacred_scorch`、`buff_heal`）：每次施加**獨立計算層數與持續時間**，不會覆蓋舊層，多層同時跳傷害/回血。
   - `merge: true`（如 `manic`）：重複施加時會直接**合併疊加數值**。

3. **觸發結算時機 (`buff_events`)**：
   - `before_action`：行動前回合結算（例如 DoT 扣血、HoT 回血、`stun` 暈眩判定、`freezing` 冰凍判定）。
   - `before_attack`：出招攻擊前結算（例如 `stealth` 破隱增傷、`damage_surge` 傷害湧動、`weakness` 降傷）。
   - `before_damage`：受到傷害前結算（例如 `bulwark` 25% 免傷判定、`mark` 印記增傷、`trauma` 創傷易傷、`protection` 減傷）。
   - `after_action`：行動結束後結算（例如 `silence` 沉默倒數、`stealth` 隱形破除、`immobilize` 定身結算）。

---

## 🛑 1. 控制與特殊狀態 (Crowd Control & Immortality)

| 狀態代號 | 中文名稱 | 類型 | 觸發時機 | 最大回合 | 效果與機制說明 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `silence` | **禁言沉默** | 強控 (Debuff) | `after_action` | 3 回合 | 無法使用主動技能，僅能普攻。**生效期間自身自帶 `silence_immuned: 1.0`（完全免疫二次沉默，無法在持續中被刷新或疊加）**。<br>最大持續 3 回合 (`max_round: 3.0`)。結算時機為行動後 (`after_action`)。 |
| `stun` | **擊暈眩暈** | 強控 (Debuff) | `before_action` | 依技能 | 完全跳過回合無法行動。**生效期間自身自帶 `stun_immuned: 1.0`（完全免疫二次暈眩，無法在持續中被連環暈）**。<br>結算時機為行動前 (`before_action`)。 |
| `freezing` | **極寒冰凍** | 強控/抗性變更 (Debuff) | `before_action` | 依技能 | 凍結無法行動。冰凍狀態下獲得火抗 +100% (`fire_res: 100`)，但冰抗 +200% (`ice_res: 200`)。<br>結算時機為行動前 (`before_action`)。 |
| `petrification` | **堅硬石化** | 特殊控制 (Buff/Debuff) | `before_action, before_damage` | 依技能 | 石化無法行動，但獲得 +75% 增傷，且每回合開始時恢復 10%~20% 生命值。<br>結算時機為行動前與受傷前 (`before_action`, `before_damage`)。 |
| `immobilize` | **定身束縛** | 位移限制 (Debuff) | `after_action` | 依技能 | 無法更換前後排站位與走位。<br>結算時機為行動後 (`after_action`)。 |
| `hallucination` | **幻覺混亂** | 軟控 (Debuff) | `after_action` | 依技能 | 精神錯亂，攻擊目標可能偏離或失準。<br>結算時機為行動後 (`after_action`)。 |
| `taunt` | **強制嘲諷** | 仇恨控制 (Buff) | `before_action` | 依技能 | 強制敵方所有單體指向攻擊優先以自身為目標。<br>結算時機為行動前 (`before_action`)。 |
| `provocation` | **怒火挑釁** | 仇恨控制 (Debuff) | `無 / 常駐` | 依技能 | 挑釁目標使其攻擊鎖定自身。<br>Debuff 類型仇恨導向。 |
| `death_immunity` | **免死不滅** | 不死守護 (Buff) | `無 / 常駐` | 9 回合 | 受到致死傷害時生命鎖定在 1 點不死，上限 9 回合。<br>被動觸發型免死保護。 |

---

## 🩸 2. 持續傷害與回復 (DoT & HoT Effects)

| 狀態代號 | 中文名稱 | 類型 | 觸發時機 | 最大回合 | 效果與機制說明 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `bleed` | **流血** | 持續傷害 (DoT Debuff) | `before_action` | 依技能 | 行動前回合扣血 (20% 攻擊力係數)。`merge: false` 獨立計層，多層流血各自獨立倒數結算。<br>結算時機為行動前 (`before_action`)。 |
| `poison` | **劇毒侵蝕** | 持續傷害 (DoT Debuff) | `before_action` | 5 回合 | 行動前回合扣血 (20% 攻擊力係數)，持續 5 回合。`merge: false` 獨立計層。<br>結算時機為行動前 (`before_action`)，`max_round: 5.0`。 |
| `fire` | **燃燒點燃** | 持續傷害 (DoT Debuff) | `before_action` | 依技能 | 行動前回合扣血 (20% 火焰傷害係數)。`merge: false` 獨立計層。<br>結算時機為行動前 (`before_action`)。 |
| `plague` | **劇毒瘟疫** | 永久持續傷害 (DoT Debuff) | `before_action` | 9999 回合 | 行動前受到 20% 瘟疫傷害。持續時間高達 9999 回合（本質上為永久存在，直到使用驅散技能清除）。<br>結算時機為行動前 (`before_action`)，`max_round: 9999.0`。 |
| `sacred_scorch` | **聖炎灼燒** | 複合 DoT/易傷 (Debuff) | `before_action` | 依技能 | 行動前受到 25% 聖炎傷害，且受到傷害額外增加 15% (`damage_bouns: 0.15`)。`merge: false` 獨立計層。<br>結算時機為行動前 (`before_action`)。 |
| `buff_heal` | **持續治癒 (HoT)** | 持續恢復 (Buff) | `before_action` | 依技能 | 行動前回合恢復生命 (20% 係數)。`merge: false` 獨立計層回血。<br>結算時機為行動前 (`before_action`)。 |
| `brooding_egg` | **寄生異卵** | 複合 DoT/易傷 (Debuff) | `無 / 常駐` | 依技能 | 承受傷害增加 15%，且每回合受到 50% 傷害偏移，`merge: false` 獨立計層。<br>蟲族或寄生體專屬異常狀態。 |

---

## 🎯 3. 印記、易傷與弱化減益 (Marks, Vulnerability & Debuffs)

| 狀態代號 | 中文名稱 | 類型 | 觸發時機 | 最大回合 | 效果與機制說明 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `mark` | **弱點標記** | 增傷易傷 (Debuff) | `before_damage` | 依技能 | 受擊前結算，使目標承受的傷害提升 20% (`damage_bouns: 0.2`)。<br>結算時機為受傷前 (`before_damage`)。 |
| `death_mark` | **死亡印記** | 增傷易傷 (Debuff) | `無 / 常駐` | 5 回合 | 使目標承受的傷害提升 10% (`damage_bouns: 0.1`)，最多持續 5 回合。<br>`max_round: 5.0`。 |
| `dreadlight_mark` | **恐光印記** | 高階易傷 (Debuff) | `無 / 常駐` | 9 回合 | 使目標承受的傷害提升 25% (`damage_bouns: 0.25`)，持續 9 回合。<br>`max_round: 9.0`。 |
| `trauma` | **重度創傷** | 堆疊易傷 (Debuff) | `before_damage` | 9 回合 | 受擊前結算，每層使承受傷害提升 5% (`damage_bouns: 0.05`)，最多 9 回合。<br>結算時機為受傷前 (`before_damage`)。 |
| `vulnerability` | **破綻脆弱** | 堆疊易傷 (Debuff) | `before_damage` | 9 回合 | 受擊前結算，每層使承受傷害提升 5% (`damage_bouns: 0.05`)，最多 9 回合。<br>結算時機為受傷前 (`before_damage`)。 |
| `frostscar` | **寒霜刻印 (霜痕)** | 冰系易傷 (Debuff) | `無 / 常駐` | 9 回合 | 每層使目標承受傷害提升 5% (`damage_bouns: 0.05`)，最多 9 回合。<br>`max_round: 9.0`。 |
| `flayed` | **裂解剝皮** | 易傷 (Debuff) | `無 / 常駐` | 3 回合 | 剝除外皮防禦，每層使承受傷害提升 1% (`damage_bouns: 0.01`)，上限 3 回合。<br>`max_round: 3.0`。 |
| `suppressed` | **精神壓制** | 易傷 (Debuff) | `無 / 常駐` | 9 回合 | 受到壓制，承受傷害提升 15% (`damage_bouns: 0.15`)，最多 9 回合。<br>`max_round: 9.0`。 |
| `wither` | **衰敗凋零** | 易傷 (Debuff) | `無 / 常駐` | 9 回合 | 目標生命力衰退，承受傷害提升 5% (`damage_bouns: 0.05`)，最多 9 回合。<br>`max_round: 9.0`。 |
| `weakness` | **虛弱無力** | 輸出弱化 (Debuff) | `before_attack` | 9 回合 | 出招前結算，使目標造成的傷害降低 5%/層 (`damage_bouns: 0.05`)，上限 9 回合。<br>結算時機為攻擊前 (`before_attack`)。 |
| `damage_reduction` | **攻擊削弱** | 輸出弱化 (Debuff) | `before_attack` | 9 回合 | 出招前結算，使目標造成的傷害降低 5%/層 (`damage_bouns: -0.05`)，上限 9 回合。<br>結算時機為攻擊前 (`before_attack`)。 |
| `vital_blockade` | **生機阻斷 (禁療)** | 受療削弱 (Debuff) | `無 / 常駐` | 9 回合 | 使目標受到的所有治療量降低 10%/層 (`healing_red: 0.1`)，上限 9 回合。<br>`max_round: 9.0`。 |
| `darkness` | **致盲黑暗** | 命中弱化 (Debuff) | `無 / 常駐` | 9 回合 | 使目標攻擊時的未命中機率增加 5%/層 (`miss_chance: 0.05`)，上限 9 回合。<br>`max_round: 9.0`。 |
| `drenched` | **潮濕浸透** | 元素傳導 (Debuff) | `無 / 常駐` | 依技能 | 使目標承受傷害提升 25% (`damage_bouns: 0.25`)。<br>水屬性/海域技能施加。 |
| `drowning` | **溺水窒息** | 水域窒息 (Debuff) | `無 / 常駐` | 依技能 | 陷入溺水狀態，行動與生存能力受制。<br>環境/水系技能觸發。 |
| `sinbrand` | **罪業烙印** | 深淵印記 (Debuff) | `無 / 常駐` | 3 回合 | 罪業標記，持續 3 回合，觸發特定深淵額外效果。<br>`max_round: 3.0`。 |

---

## ⚔️ 4. 攻擊與輸出增益 (Offensive Buffs)

| 狀態代號 | 中文名稱 | 類型 | 觸發時機 | 最大回合 | 效果與機制說明 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `stealth` | **暗影潛行** | 爆發/隱蔽 (Buff) | `before_attack, after_action` | 依技能 | 進入潛行狀態無法被單體鎖定。**破隱第一擊獲得高達 +75% 傷害加成 (`damage_bouns: 0.75`)**。<br>結算時機為攻擊前與行動後 (`before_attack`, `after_action`)。 |
| `assault` | **強襲突擊** | 爆發增傷 (Buff) | `無 / 常駐` | 9 回合 | 獲得極具毀滅性的 +150% 傷害加成 (`damage_bouns: 1.5`)，上限 9 回合。<br>`max_round: 9.0`。 |
| `manic` | **狂躁暴怒** | 堆疊狂化 (Buff) | `無 / 常駐` | 依技能 | 複合雙重 +50% 增傷 (`dam_bouns_1: 0.5, dam_bouns_2: 0.5`)。`merge: true` 可直接合併疊加。<br>少數支援 `merge: true` 的暴力狀態。 |
| `damage_surge` | **傷害湧動** | 攻擊增強 (Buff) | `before_attack` | 9 回合 | 攻擊前結算，提高該次造成的傷害 5%/層 (`damage_bouns: 0.05`)，上限 9 回合。<br>結算時機為攻擊前 (`before_attack`)。 |
| `critical_strike` | **致命專注** | 暴擊增強 (Buff) | `無 / 常駐` | 9 回合 | 提升自身暴擊機率 5%/層 (`crit_chance: 0.05`)，上限 9 回合。<br>`max_round: 9.0`。 |
| `battle_fury` | **戰意狂怒** | 戰鬥積累 (Buff) | `無 / 常駐` | 9 回合 | 戰鬥中隨時間累積傷害加成 (+5%/層)，上限 9 回合。<br>`max_round: 9.0`。 |
| `bloodlust` | **嗜血狂熱** | 短時爆發 (Buff) | `無 / 常駐` | 3 回合 | 提高造成傷害 5%/層，持續 3 回合。<br>`max_round: 3.0`。 |
| `bloodthirst_power` | **渴血之力** | 吸血增強 (Buff) | `無 / 常駐` | 9 回合 | 提高造成傷害 5%/層，持續 9 回合。<br>`max_round: 9.0`。 |
| `slaughter_power` | **殺戮之威** | 斬殺增益 (Buff) | `無 / 常駐` | 999 回合 | 擊殺目標後獲得的永久狂暴狀態，持續 999 回合。<br>`max_round: 999.0`。 |
| `beast_power` | **野獸之力** | 野性爆發 (Buff) | `無 / 常駐` | 9 回合 | 野性力量充盈，獲得 +45% 傷害加成 (`damage_bouns: 0.45`)，上限 9 回合。<br>`max_round: 9.0`。 |
| `abyss_seed` | **深淵之種** | 全能積累 (Buff) | `無 / 常駐` | 9 回合 | 每層提供 +1% 暴擊、+1% 傷害加成、+1% 傷害減免，上限 9 回合。<br>`crit_chance: 0.01, damage_bouns: 0.01, damage_red: 0.01`。 |
| `energy_charge` | **能量充能** | 蓄力狀態 (Buff) | `無 / 常駐` | 9 回合 | 能量充填蓄勢待發，上限 9 回合。<br>`max_round: 9.0`。 |
| `summon_power` | **召喚統御之力** | 光環/加成 (Buff) | `無 / 常駐` | 依技能 | 提高召喚單位全屬性 10% (`attr_bouns: 0.1`)。<br>召喚流核心增益。 |
| `disordered_directive` | **紊亂指令** | 特殊指令 (Buff) | `無 / 常駐` | 9 回合 | 混亂模式下的特殊指令增益，上限 9 回合。<br>`max_round: 9.0`。 |

---

## 🛡️ 5. 防禦、護甲與抗性 (Defensive Buffs, Armors & Environments)

| 狀態代號 | 中文名稱 | 類型 | 觸發時機 | 最大回合 | 效果與機制說明 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `bulwark` | **堅毅壁壘** | 免傷護甲 (Buff) | `before_damage` | 9 回合 | 受到傷害前判定，**擁有 25% 機率完全抵消傷害 (`negate_chance: 0.25`)**，上限 9 回合。<br>結算時機為受傷前 (`before_damage`)。 |
| `protection` | **守護庇蔭** | 減傷防護 (Buff) | `before_damage` | 9 回合 | 受到傷害前判定，每層減少承受傷害 5% (`damage_red: 0.05`)，上限 9 回合。<br>結算時機為受傷前 (`before_damage`)。 |
| `buff_block` | **格擋姿態** | 格擋防禦 (Buff) | `無 / 常駐` | 9 回合 | 提升格擋機率 5%/層 (`block_chance: 0.05`)，上限 9 回合。<br>`max_round: 9.0`。 |
| `buff_dodge` | **靈動閃避** | 迴避防禦 (Buff) | `無 / 常駐` | 9 回合 | 提升閃避機率 5%/層 (`dodge_chance: 0.05`)，上限 9 回合。<br>`max_round: 9.0`。 |
| `frost_barrier` | **極霜護盾** | 抗性屏障 (Buff) | `無 / 常駐` | 依技能 | 提高冰霜抗性 +75% (`ice_res: 75.0`) 與魔法抗性 +20% (`magic_res: 20.0`)。<br>冰法/防禦技能專屬屏障。 |
| `barrier` | **能量護盾** | 防護增傷 (Buff) | `無 / 常駐` | 依技能 | 獲得能量護盾並附帶 +45% 傷害加成 (`damage_bouns: 0.45`)。<br>複合型防護屏障。 |
| `blessing` | **神聖祝福** | 攻防祝福 (Buff) | `無 / 常駐` | 依技能 | 獲得 +15% 傷害加成 (`dam_bouns: 0.15`) 且同時獲得 +15% 傷害減免 (`dam_red: 0.15`)。<br>聖職者核心攻防光環。 |
| `foul_carapace` | **穢惡甲殼** | 異種甲殼 (Buff) | `無 / 常駐` | 5 回合 | 甲殼護體，提升傷害加成 +5%，上限 5 回合。<br>`max_round: 5.0`。 |
| `ironoath` | **鋼鐵誓言** | 騎士誓言 (Buff) | `無 / 常駐` | 9 回合 | 聖騎士防禦誓約，上限 9 回合。<br>`max_round: 9.0`。 |
| `burn_immunity` | **燃燒免疫增幅** | 抗性強化 (Buff) | `無 / 常駐` | 9 回合 | 免疫燃燒並獲得 +25% 傷害加成，上限 9 回合。<br>`max_round: 9.0`。 |
| `armor_mag` | **魔力護甲** | 魔法護甲 (Armor) | `無 / 常駐` | 9999 回合 | 吸收魔法傷害的專用護甲值，持續 9999 回合。<br>`max_round: 9999.0`。 |
| `buff_armor` | **物理護甲** | 物理護甲 (Armor) | `無 / 常駐` | 9999 回合 | 吸收物理傷害的專用護甲值，持續 9999 回合。<br>`max_round: 9999.0`。 |
| `beverage` | **微醺飲酒** | 消耗品增益 (Buff) | `無 / 常駐` | 依技能 | 酒館飲品獲得的戰鬥前置加成狀態。<br>酒館消耗品效果。 |
| `deepsea_resonance` | **深海共鳴** | 海域共鳴 (Buff) | `無 / 常駐` | 9 回合 | 深海種族獲得的專屬共鳴加成，上限 9 回合。<br>`max_round: 9.0`。 |
| `deepsea` | **深海環境壓制** | 戰場環境 (Environment) | `無 / 常駐` | 1 回合 | 深海戰場環境效果，受到傷害增加 15% (`damage_bouns: 0.15`)，持續 1 回合。<br>`max_round: 1.0`。 |

---

## 📊 附錄：全狀態屬性與參數字典對照表

| 屬性鍵值 | 中文含意 | 典型作用狀態 |
| :--- | :--- | :--- |
| `silence_immuned` | 免疫沉默 | `silence`（自身作用中賦予免疫）、天賦特質 |
| `stun_immuned` | 免疫擊暈 | `stun`（自身作用中賦予免疫）、天賦特質 |
| `damage_offset` | 每回合傷害偏移 (DoT/HoT 係數) | `bleed`, `poison`, `fire`, `plague`, `buff_heal` |
| `damage_bouns` | 傷害加成 / 承受易傷 | `stealth` (+75%), `assault` (+150%), `mark` (+20%), `trauma` (+5%) |
| `damage_red` | 傷害減免 | `protection` (-5%), `blessing` (-15%), `abyss_seed` (-1%) |
| `negate_chance` | 傷害完全抵消機率 | `bulwark` (25% 完全免疫受傷) |
| `miss_chance` | 未命中機率增加 (失準) | `darkness` (+5%) |
| `healing_red` | 治療效果降低 (禁療) | `vital_blockade` (+10%) |
| `merge: false` | 不合併 (多層獨立並行計算) | `bleed`, `poison`, `fire`, `sacred_scorch` |
| `merge: true` | 合併 (數值直接疊加) | `manic` |
