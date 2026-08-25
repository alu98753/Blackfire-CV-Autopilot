# ⚔️ Blackfire Crusade 全英雄與全技能繁體中文分析圖鑑

> 本文件由 `meta_data/hero_analyzer.py` 依據遊戲原始數據 `meta_datas.tres` 自動解析並翻譯生成。

## 📊 數據統計概覽
- **收錄英雄總數**：60 位
- **職業類別總數**：7 種
- **全遊戲技能總數**：702 個

---

## 🛡️ 職業基礎屬性與每級成長表

| 職業 (Class) | 基礎專精屬性 | 每級升級屬性成長 (Upgrade Attr) | 裝備偏好 |
| :--- | :--- | :--- | :--- |
| **遊俠 (弓箭手)** (`archer`) | 暴擊率 (%): 10.0, 物理傷害加深 (%): 20.0, 物理抗性 (%): 10.0 | 最大傷害: +1.0, 最小傷害: +1.0, 物理防禦: +3.0, 魔法防禦: +3.0, 生命值: +5.0 | armor: ['medium_armor'], main_hand: ['bow'], off_hand: ['quiver'] |
| **騎士 (聖騎士)** (`knight`) | 神聖傷害加深 (%): 10.0, 神聖抗性 (%): 10.0, 生命值: 10.0, 物理抗性 (%): 10.0 | 最大傷害: +1.0, 最小傷害: +1.0, 物理防禦: +5.0, 魔法防禦: +1.0, 生命值: +5.0 | armor: ['heavy_armor'], main_hand: ['spear'], off_hand: ['shield'] |
| **法師 (元素使)** (`mage`) | 火焰傷害加深 (%): 10.0, 火焰抗性 (%): 10.0, 冰霜傷害加深 (%): 10.0, 冰霜抗性 (%): 10.0 | 最大傷害: +1.0, 最小傷害: +1.0, 物理防禦: +1.0, 魔法防禦: +5.0, 生命值: +5.0 | armor: ['light_armor'], main_hand: ['staff'], off_hand: ['book'] |
| **戰寵 (靈獸)** (`pet`) | 魔法傷害加深 (%): 10.0, 魔法抗性 (%): 10.0, 物理傷害加深 (%): 10.0, 物理抗性 (%): 10.0 | 最大傷害: +1.0, 最小傷害: +1.0, 物理防禦: +3.0, 魔法防禦: +3.0, 生命值: +5.0 | beaststone: ['all'] |
| **牧師 (神官)** (`priest`) | 治療效果提升 (%): 10.0, 神聖傷害加深 (%): 20.0, 神聖抗性 (%): 10.0 | 最大傷害: +1.0, 最小傷害: +1.0, 物理防禦: +1.0, 魔法防禦: +5.0, 生命值: +5.0 | armor: ['light_armor'], main_hand: ['scepter'], off_hand: ['book'] |
| **刺客 (盜賊)** (`rogue`) | 閃避率 (%): 10.0, 先攻權: 1.0, 物理傷害加深 (%): 10.0 | 最大傷害: +1.0, 最小傷害: +1.0, 物理防禦: +3.0, 魔法防禦: +3.0, 生命值: +5.0 | armor: ['medium_armor'], main_hand: ['dagger'], off_hand: ['dagger'] |
| **戰士 (狂戰士)** (`warrior`) | 暴擊抗性 (%): 10.0, 物理傷害加深 (%): 10.0, 物理抗性 (%): 20.0 | 最大傷害: +1.0, 最小傷害: +1.0, 物理防禦: +5.0, 魔法防禦: +1.0, 生命值: +5.0 | armor: ['heavy_armor'], main_hand: ['sword', 'axe', 'hammer'], off_hand: ['shield'] |

---

## 🧙‍♂️ 全部英雄與技能全景清單

### ⚔️ 【遊俠 (弓箭手)】系列英雄 (9 位)

#### 🔹 hero_archer_1 - 遊俠 (弓箭手) (普通 (白))
- **基本資料**：種族 `精靈` | 性別 `男` | 稀有度星級 `0.0`
- **初始裝備**：main_hand: `bow_001`, off_hand: `quiver_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `double_shoot` | **雙重射擊** | 主動 | 物理傷害 | 65% | 5 回合 | 0 | 敵方 遠程/全範圍 (2體) | 流血觸發機率: 0.25<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>每級傷害係數/倍率: +0.02 |

#### 🔹 hero_archer_2 - 遊俠 (弓箭手) (優秀 (綠))
- **基本資料**：種族 `人類` | 性別 `女` | 稀有度星級 `1.0`
- **初始裝備**：main_hand: `bow_001`, off_hand: `quiver_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `double_shoot` | **雙重射擊** | 主動 | 物理傷害 | 65% | 5 回合 | 0 | 敵方 遠程/全範圍 (2體) | 流血觸發機率: 0.25<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>每級傷害係數/倍率: +0.02 |
| `mark_shoot` | **印記射擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 遠程/全範圍 (1體) | 標記層數: 5.0<br>每級傷害係數/倍率: +0.04 |

#### 🔹 hero_archer_3 - 遊俠 (弓箭手) (稀有 (藍))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `2.0`
- **初始裝備**：main_hand: `bow_002`, off_hand: `quiver_002`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `double_shoot` | **雙重射擊** | 主動 | 物理傷害 | 65% | 5 回合 | 0 | 敵方 遠程/全範圍 (2體) | 流血觸發機率: 0.25<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>每級傷害係數/倍率: +0.02 |
| `scatter_shot` | **散射連發** | 主動 | 物理傷害 | - | 5 回合 | 0 | 敵方 遠程/全範圍 (1體) | 流血觸發機率: 0.25<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>一段傷害倍率: 0.8<br>二段傷害倍率: 0.25<br>隨機連擊次數: 3.0<br>每級一段傷害倍率: +0.02<br>每級二段傷害倍率: +0.01 |
| `bandage_wounds` | **包紮傷口** | 主動 | 物理傷害 | - | 5 回合 | -1 | 友方 遠程/全範圍 (1體) | 最大生命回復率: 0.2<br>最小生命回復率: 0.1<br>每級最大生命回復率: +0.01<br>每級最小生命回復率: +0.01 |

#### 🔹 hero_archer_4 - 遊俠 (弓箭手) (史詩 (紫))
- **基本資料**：種族 `精靈` | 性別 `女` | 稀有度星級 `3.0`
- **初始裝備**：main_hand: `bow_003`, off_hand: `quiver_003`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `double_shoot` | **雙重射擊** | 主動 | 物理傷害 | 65% | 5 回合 | 0 | 敵方 遠程/全範圍 (2體) | 流血觸發機率: 0.25<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>每級傷害係數/倍率: +0.02 |
| `scatter_shot` | **散射連發** | 主動 | 物理傷害 | - | 5 回合 | 0 | 敵方 遠程/全範圍 (1體) | 流血觸發機率: 0.25<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>一段傷害倍率: 0.8<br>二段傷害倍率: 0.25<br>隨機連擊次數: 3.0<br>每級一段傷害倍率: +0.02<br>每級二段傷害倍率: +0.01 |
| `death_shoot` | **致命射擊** | 主動 | 物理傷害 | 160% | 3 回合 | -3 | 敵方 遠程/全範圍 (1體) | 斬殺額外暴擊血線閥值: 0.75<br>每級傷害係數/倍率: +0.06 |
| `rampage_wings` | **狂暴龍翼** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 暴擊率 (%): 40.0<br>持續回合數: 10.0<br>每級暴擊率 (%): +4.0 |

#### 🔹 hero_archer_5 - 遊俠 (弓箭手) (傳說 (橘))
- **基本資料**：種族 `蛙人族` | 性別 `男` | 稀有度星級 `4.0`
- **初始裝備**：main_hand: `bow_005`, off_hand: `quiver_005`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lightshot` | **聖光耀射** | 主動 | 物理傷害 | 50% | 5 回合 | 1 | 敵方 遠程/全範圍 (1體) | 每級傷害係數/倍率: +0.025 |
| `toxic_arrow` | **劇毒浸染箭** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 遠程/全範圍 (1體) | 中毒層數上限: 5.0<br>中毒基礎層數: 1.0<br>每級傷害係數/倍率: +0.04 |
| `swift_shot` | **迅捷射擊** | 主動 | 物理傷害 | 160% | 3 回合 | -3 | 敵方 遠程/全範圍 (1體) | 獲得行動點機率: 0.75<br>獲得行動點數量: 1.0<br>每級傷害係數/倍率: +0.06 |
| `blade_bow` | **刃弓疾斬** | 主動 | 物理傷害 | - | 5 回合 | -3 | 敵方 近戰目標 (1體) | 一段傷害倍率: 1.0<br>二段傷害倍率: 1.4<br>每級一段傷害倍率: +0.06<br>每級二段傷害倍率: +0.06 |
| `quick_preparation` | **快速整裝 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 獲得行動點機率: 0.15<br>獲得行動點數量: 1.0<br>每級獲得行動點機率: +0.01 |

#### 🔹 hero_archer_6 - 遊俠 (弓箭手) (神話 (紅))
- **基本資料**：種族 `精靈` | 性別 `男` | 稀有度星級 `5.0`
- **初始裝備**：main_hand: `bow_hero_theron`, off_hand: `quiver_hero_theron`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lightshot` | **聖光耀射** | 主動 | 物理傷害 | 50% | 5 回合 | 1 | 敵方 遠程/全範圍 (1體) | 每級傷害係數/倍率: +0.025 |
| `mark_shoot` | **印記射擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 遠程/全範圍 (1體) | 標記層數: 5.0<br>每級傷害係數/倍率: +0.04 |
| `bandage_wounds` | **包紮傷口** | 主動 | 物理傷害 | - | 5 回合 | -1 | 友方 遠程/全範圍 (1體) | 最大生命回復率: 0.2<br>最小生命回復率: 0.1<br>每級最大生命回復率: +0.01<br>每級最小生命回復率: +0.01 |
| `multi_mark_shot` | **多重標記射擊** | 主動 | 物理傷害 | 60% | 10 回合 | -3 | 敵方 遠程/全範圍 (1體) | 最大箭矢數: 5.0<br>最小箭矢數: 3.0<br>標記觸發機率: 0.25<br>標記層數上限: 5.0<br>標記基礎層數: 3.0<br>每級傷害係數/倍率: +0.03 |
| `marked_hunter` | **獵人印記 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 暴擊觸發率: 0.2<br>每級暴擊觸發率: +0.02 |
| `deadly_pursuit` | **死神追擊** | 主動 | 物理傷害 | 200% | 7 回合 | -3 | 敵方 遠程/全範圍 (1體) | 每級傷害係數/倍率: +0.12 |

#### 🔹 hero_archer_7 - 遊俠 (弓箭手) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `龍裔` | 性別 `男` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `bow_hero_archer_7`, off_hand: `quiver_archer_7`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lightshot` | **聖光耀射** | 主動 | 物理傷害 | 50% | 5 回合 | 1 | 敵方 遠程/全範圍 (1體) | 每級傷害係數/倍率: +0.025 |
| `dragonbane_arrow` | **屠龍穿心箭** | 主動 | 物理傷害 | 140% | 5 回合 | -2 | 敵方 遠程/全範圍 (1體) | 標記層數: 3.0<br>vulnerability_count: 5.0<br>每級傷害係數/倍率: +0.05 |
| `flowing_arrow` | **流光之箭** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | reset_chance: 0.15<br>每級reset_chance: +0.01 |
| `wingrend_volley` | **破翼齊射** | 主動 | 物理傷害 | 50% | 5 回合 | -3 | 敵方 遠程/全範圍 (3體) | skill_count: 2.0<br>每級傷害係數/倍率: +0.025 |
| `draconic_doom_mark` | **龍之厄運印記** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 標記觸發機率: 0.15<br>標記層數上限: 5.0<br>標記基礎層數: 3.0<br>vulnerability_count: 5.0<br>每級標記觸發機率: +0.03 |
| `cataclysmic_arrow` | **滅世天劫箭** | 主動 | 物理傷害 | 240% | 5 回合 | -4 | 敵方 遠程/全範圍 (1體) | 增益觸發機率: 0.45<br>buff_max: 7.0<br>buff_min: 5.0<br>每級傷害係數/倍率: +0.12 |
| `critical_assault` | **致命突襲** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | beast_power_chance: 0.35<br>每級beast_power_chance: +0.05 |

#### 🔹 hero_archer_drugor - 遊俠 (弓箭手) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `獸人` | 性別 `男` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `bow_hero_archer_drugor`, off_hand: `quiver_hero_archer_drugor`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `bloodfang_mark` | **bloodfang_mark** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 遠程/全範圍 (1體) | bloodlust_count: 1.0<br>標記層數: 3.0<br>每級傷害係數/倍率: +0.02 |
| `rend_frenzy` | **rend_frenzy** | 主動 | 物理傷害 | 120% | 3 回合 | -2 | 敵方 遠程/全範圍 (1體) | bloodlust_count: 1.0<br>每級傷害係數/倍率: +0.04 |
| `blood_recycle` | **血液回收 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | bloodlust_chance: 0.45<br>bloodlust_count: 3.0<br>bloodthirst_power_count: 3.0<br>每級bloodlust_chance: +0.03 |
| `bloodrend_pursuit` | **裂血追擊** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 流血觸發機率: 0.45<br>流血層數上限: 5.0<br>流血基礎層數: 3.0<br>每級流血觸發機率: +0.03 |
| `bloodrage_awakening` | **血怒覺醒 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | bloodlust_count: 3.0<br>hp_offset_1: 0.25<br>hp_offset_2: 0.25<br>manic_count: 5.0<br>每級hp_offset_2: +-0.01 |
| `bloodburst_execution` | **爆血處決** | 主動 | 物理傷害 | 200% | 7 回合 | -3 | 敵方 遠程/全範圍 (1體) | bloodlust_chance: 0.25<br>bloodlust_count: 3.0<br>額外傷害加成: 0.5<br>每級bloodlust_chance: +0.02<br>每級傷害係數/倍率: +0.12 |
| `crimson_threshold` | **赤紅臨界 (被動)** | 被動 | 輔助/被動 | 40% | 無 CD | 0 | 敵方 單體 (1體) | 獲得行動點數量: 1.0<br>每級傷害係數/倍率: +0.06 |

#### 🔹 hero_archer_olaf - 遊俠 (弓箭手) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `維京人` | 性別 `男` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `bow_archer_olaf`, off_hand: `quiver_archer_olaf`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `guided_twinshot` | **導引雙重箭** | 主動 | 物理傷害 | 60% | 5 回合 | -1 | 敵方 遠程/全範圍 (2體) | deepsea_resonance_chance: 0.75<br>deepsea_resonance_count: 1.0<br>每級傷害係數/倍率: +0.01 |
| `anchored_shot` | **定錨強射** | 主動 | 物理傷害 | 120% | 5 回合 | -2 | 敵方 遠程/全範圍 (1體) | deepsea_resonance_count: 1.0<br>immobilize_count: 2.0<br>虛弱觸發機率: 0.45<br>weakness_count: 3.0<br>每級傷害係數/倍率: +0.04 |
| `sunken_grasp` | **沉沒之握** | 主動 | 物理傷害 | 70% | 7 回合 | -2 | 敵方 遠程/全範圍 (3體) | 虛弱觸發機率: 0.45<br>虛弱層數上限: 3.0<br>虛弱基礎層數: 1.0<br>每級傷害係數/倍率: +0.02 |
| `helmsman_strike` | **掌舵者破浪擊** | 主動 | 物理傷害 | 160% | 7 回合 | -3 | 敵方 遠程/全範圍 (1體) | damage_offset_magic: 0.3<br>drowning_chance: 0.45<br>隨機連擊次數: 3.0<br>眩暈觸發機率: 0.25<br>每級傷害係數/倍率: +0.08<br>每級damage_offset_magic: +0.02 |
| `dimensional_beacon` | **維度信標 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | mag_chance: 0.025<br>phy_chance: 0.05<br>每級mag_chance: +0.005<br>每級phy_chance: +0.01 |
| `abyssal_resonance` | **深淵共鳴 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 增益觸發機率: 0.25<br>一段傷害倍率: 0.75<br>二段傷害倍率: 1.25<br>deepsea_resonance_count: 1.0<br>phase_1_count: 3.0<br>phase_2_count: 6.0<br>phase_3_count: 9.0<br>vulnerability_count: 3.0<br>weakness_count: 3.0<br>每級一段傷害倍率: +0.05<br>每級二段傷害倍率: +0.1 |
| `tidal_pursuit` | **潮汐追襲** | 被動 | 魔法傷害 | 20% | 無 CD | 0 | 敵方 單體 (1體) | drowning_chance: 0.15<br>每級傷害係數/倍率: +0.03<br>每級drowning_chance: +0.01 |

### ⚔️ 【騎士 (聖騎士)】系列英雄 (9 位)

#### 🔹 hero_knight_1 - 騎士 (聖騎士) (普通 (白))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `0.0`
- **初始裝備**：main_hand: `spear_wooden`, off_hand: `shield_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `guardian_blow` | **守護重擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | bulwark_max: 3.0<br>bulwark_min: 1.0<br>每級傷害係數/倍率: +0.02 |

#### 🔹 hero_knight_2 - 騎士 (聖騎士) (優秀 (綠))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `1.0`
- **初始裝備**：main_hand: `spear_wooden`, off_hand: `shield_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `guardian_blow` | **守護重擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | bulwark_max: 3.0<br>bulwark_min: 1.0<br>每級傷害係數/倍率: +0.02 |
| `sanctuary_light` | **聖所之光** | 主動 | 物理傷害 | - | 5 回合 | -1 | 友方 遠程/全範圍 (1體) | bulwark_max: 3.0<br>bulwark_min: 1.0<br>最大生命值: 80.0<br>hp_min: 40.0<br>每級最大生命值: +6.0<br>每級hp_min: +3.0 |

#### 🔹 hero_knight_3 - 騎士 (聖騎士) (稀有 (藍))
- **基本資料**：種族 `精靈` | 性別 `男` | 稀有度星級 `2.0`
- **初始裝備**：main_hand: `spear_iron`, off_hand: `shield_002`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `guardian_blow` | **守護重擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | bulwark_max: 3.0<br>bulwark_min: 1.0<br>每級傷害係數/倍率: +0.02 |
| `knight_will` | **騎士意志** | 主動 | 物理傷害 | - | 5 回合 | -2 | 友方 全體 (1體) | battle_fury_chance: 0.25<br>battle_fury_max: 5.0<br>battle_fury_min: 3.0 |
| `valiant_charge` | **英勇衝鋒** | 主動 | 物理傷害 | 85% | 5 回合 | -3 | 敵方 全體 (1體) | battle_fury_max: 5.0<br>battle_fury_min: 3.0<br>每級傷害係數/倍率: +0.04 |

#### 🔹 hero_knight_4 - 騎士 (聖騎士) (史詩 (紫))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `3.0`
- **初始裝備**：main_hand: `spear_003`, off_hand: `shield_003`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `holy_strike` | **神聖打擊** | 主動 | 神聖傷害 | 120% | 3 回合 | 0 | 敵方 遠程/全範圍 (1體) | 眩暈觸發機率: 0.25<br>每級傷害係數/倍率: +0.02 |
| `sanctuary_light` | **聖所之光** | 主動 | 物理傷害 | - | 5 回合 | -1 | 友方 遠程/全範圍 (1體) | bulwark_max: 3.0<br>bulwark_min: 1.0<br>最大生命值: 80.0<br>hp_min: 40.0<br>每級最大生命值: +6.0<br>每級hp_min: +3.0 |
| `divine_light_spear` | **聖光貫穿之槍** | 主動 | 神聖傷害 | 140% | 5 回合 | -2 | 敵方 遠程/全範圍 (1體) | 虛弱觸發機率: 0.25<br>虛弱層數上限: 7.0<br>虛弱基礎層數: 5.0<br>每級傷害係數/倍率: +0.08 |
| `holy_aegis` | **神聖聖盾** | 主動 | 物理傷害 | - | 15 回合 | -3 | 友方 全體 (1體) | armor_max: 100.0<br>armor_min: 60.0<br>damage_surge_max: 2.0<br>damage_surge_min: 1.0<br>每級armor_max: +10.0<br>每級armor_min: +6.0 |

#### 🔹 hero_knight_5 - 騎士 (聖騎士) (傳說 (橘))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `4.0`
- **初始裝備**：main_hand: `spear_005`, off_hand: `shield_005`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `guardian_blow` | **守護重擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | bulwark_max: 3.0<br>bulwark_min: 1.0<br>每級傷害係數/倍率: +0.02 |
| `resilient_healing` | **韌性復甦術** | 主動 | 物理傷害 | - | 5 回合 | -1 | 友方 遠程/全範圍 (1體) | bulwark_hp: 20.0<br>bulwark_max: 5.0<br>最大生命值: 80.0<br>hp_min: 40.0<br>每級bulwark_hp: +1.0<br>每級最大生命值: +6.0<br>每級hp_min: +3.0 |
| `holy_light_blessing` | **聖光祝福** | 主動 | 物理傷害 | - | 10 回合 | -3 | 友方 全體 (1體) | armor_max: 40.0<br>armor_min: 20.0<br>battle_fury_max: 7.0<br>battle_fury_min: 5.0<br>每級armor_max: +8.0<br>每級armor_min: +4.0 |
| `holy_shackles` | **聖光桎梏** | 主動 | 神聖傷害 | 140% | 5 回合 | -2 | 敵方 遠程/全範圍 (1體) | silence_chance: 0.25<br>silence_max: 5.0<br>silence_min: 3.0<br>每級傷害係數/倍率: +0.1 |
| `light_shield` | **聖光護盾** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | bulwark_chance: 0.1<br>bulwark_max: 3.0<br>bulwark_min: 1.0<br>bulwark_round: 9.0<br>每級bulwark_chance: +0.015 |

#### 🔹 hero_knight_askar - 騎士 (聖騎士) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `6.0`
- **初始裝備**：chest: `chest_holy_siliver`, main_hand: `spear_askar`, off_hand: `shield_askar`, relic: `holy_flame_emblem`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `judgment_spear` | **審判之槍** | 主動 | 神聖傷害 | 85% | 5 回合 | -2 | 敵方 近戰目標 (1體) | attack_times: 2.0<br>silence_chance: 0.25<br>silence_max: 2.0<br>silence_min: 1.0<br>每級傷害係數/倍率: +0.02 |
| `lightbound_grace` | **光縛恩典** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.05<br>damage_bouns_1: 0.05<br>damage_bouns_2: 0.05<br>每級額外傷害加成: +0.01<br>每級damage_bouns_1: +0.01<br>每級damage_bouns_2: +0.01 |
| `holy_spear_charge` | **聖槍衝鋒** | 主動 | 神聖傷害 | 85% | 5 回合 | -3 | 敵方 全體 (1體) | battle_fury_max: 5.0<br>battle_fury_min: 3.0<br>虛弱觸發機率: 0.25<br>虛弱層數上限: 5.0<br>虛弱基礎層數: 1.0<br>每級傷害係數/倍率: +0.04 |
| `divine_cycle` | **神聖循環 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | bulwark_chance: 0.15<br>bulwark_count: 3.0<br>heal_offset_max: 0.1<br>heal_offset_min: 0.05<br>每級bulwark_chance: +0.01<br>每級heal_offset_max: +0.005<br>每級heal_offset_min: +0.005 |
| `piercing_lightflame` | **穿透聖炎** | 主動 | 神聖傷害 | 200% | 7 回合 | -2 | 敵方 遠程/全範圍 (1體) | sacred_scorch_chance: 0.25<br>sacred_scorch_max: 5.0<br>sacred_scorch_min: 3.0<br>每級傷害係數/倍率: +0.1 |
| `knight_sacred_oath` | **騎士誓約** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 暗影抗性 (%): 50.0<br>神聖傷害加深 (%): 20.0<br>神聖抗性 (%): 20.0<br>生命值: 50.0<br>物理傷害加深 (%): 5.0<br>物理抗性 (%): 5.0<br>silence_immuned: 1.0<br>每級暗影抗性 (%): +5.0<br>每級神聖傷害加深 (%): +3.0<br>每級神聖抗性 (%): +3.0<br>每級生命值: +10.0<br>每級物理傷害加深 (%): +1.0<br>每級物理抗性 (%): +1.0<br>每級silence_immuned: +1.0 |
| `sacred_afterglow` | **神聖餘暉 (被動)** | 被動 | 輔助/被動 | 60% | 無 CD | 0 | 敵方 單體 (1體) | afterglow_chance: 0.45<br>每級afterglow_chance: +0.05<br>每級傷害係數/倍率: +0.06 |

#### 🔹 hero_knight_bragos - 騎士 (聖騎士) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `矮人` | 性別 `男` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `spear_knight_bragos`, off_hand: `shield_knight_bragos`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `oathlance_brace` | **誓約長槍架勢** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 近戰目標 (1體) | ironoath_chance: 0.45<br>ironoath_max: 5.0<br>ironoath_min: 3.0<br>每級傷害係數/倍率: +0.02 |
| `oathbound_bulwark` | **誓約壁壘** | 主動 | 物理傷害 | - | 5 回合 | -1 | 友方 自身 (1體) | armor_offset_max: 0.15<br>armor_offset_min: 0.05<br>barrier_count: 3.0<br>每級armor_offset_max: +0.01<br>每級armor_offset_min: +0.01 |
| `ironwall_slam` | **鐵壁重砸** | 主動 | 物理傷害 | 160% | 5 回合 | -3 | 敵方 近戰目標 (1體) | ironoath_max: 5.0<br>ironoath_min: 3.0<br>眩暈觸發機率: 0.45<br>每級傷害係數/倍率: +0.08 |
| `iron_bastion` | **鋼鐵堡壘** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | armor_offset: 0.15<br>hp_min: 1.0<br>每級armor_offset: +0.02 |
| `deepforge_memory` | **深鍛記憶 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | armor_offset: 0.045<br>每級armor_offset: +0.003 |
| `unbroken_vow` | **不滅誓言 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | armor_offset: 0.15<br>barrier_count: 9.0<br>hp_offset: 0.45<br>每級armor_offset: +0.02 |
| `oathforge_transmute` | **oathforge_transmute** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | buff_offset: 0.05<br>ironoath_count: 3.0<br>每級buff_offset: +0.005 |

#### 🔹 hero_knight_glig - 騎士 (聖騎士) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `哥布林` | 性別 `unknown` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `spear_goblin_glig`, off_hand: `shield_goblin_glig`, special: `spceial_goblin_glig`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `scrap_toss` | **廢鐵投擲** | 主動 | 物理傷害 | - | 5 回合 | -1 | 敵方 遠程/全範圍 (1體) | 一段傷害倍率: 1.0<br>二段傷害倍率: 0.4<br>extra_chance: 0.25<br>每級一段傷害倍率: +0.02<br>每級二段傷害倍率: +0.01 |
| `scrap_combo` | **廢鐵組合連擊** | 主動 | 物理傷害 | 60% | 5 回合 | -2 | 敵方 近戰目標 (1體) | 流血觸發機率: 0.25<br>流血層數上限: 5.0<br>流血基礎層數: 3.0<br>充能層數: 1.0<br>extra_chance: 0.75<br>每級傷害係數/倍率: +0.02 |
| `pressurized_taunt` | **蒸氣加壓挑釁** | 主動 | 物理傷害 | - | 5 回合 | -3 | 友方 自身 (1體) | armor_offset: 0.15<br>damage_reduction_max: 3.0<br>damage_reduction_min: 1.0<br>provocation_max: 3.0<br>provocation_min: 1.0<br>每級armor_offset: +0.01 |
| `fuel_steamroller` | **燃料重輾衝撞** | 主動 | 物理傷害 | - | 5 回合 | -3 | 敵方 遠程/全範圍 (1體) | 一段傷害倍率: 1.6<br>二段傷害倍率: 0.4<br>fire_chance: 0.75<br>fire_max: 5.0<br>fire_min: 3.0<br>每級一段傷害倍率: +0.08<br>每級二段傷害倍率: +0.01 |
| `kinetic_salvage` | **動能回收 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.015<br>energy_charge_chance: 0.45<br>每級額外傷害加成: +0.001<br>每級energy_charge_chance: +0.03 |
| `out_control_deployment` | **失控部屬** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | ally_chance: 0.25<br>增益觸發機率: 0.75<br>buff_max: 5.0<br>buff_min: 3.0<br>一段傷害倍率: 2.0<br>二段傷害倍率: 2.0<br>disordered_directive_chance: 0.35<br>disordered_directive_max: 2.0<br>disordered_directive_min: 1.0<br>每級disordered_directive_chance: +0.04 |
| `scrap_toys` | **發條機關玩具** | 被動 | 輔助/被動 | 50% | 無 CD | 0 | 敵方 單體 (1體) | active_count: 5.0<br>count: 1.0<br>生成/召喚機率: 0.15<br>fire_chance: 0.45<br>fire_max: 5.0<br>fire_min: 1.0<br>每級生成/召喚機率: +0.01<br>每級傷害係數/倍率: +0.05 |

#### 🔹 hero_knight_yolda - 騎士 (聖騎士) (神話 (紅))
- **基本資料**：種族 `暴走巨熊` | 性別 `unknown` | 稀有度星級 `5.0`
- **初始裝備**：main_hand: `spear_bear_yolda`, off_hand: `shield_bear_yolda`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `guardian_blow` | **守護重擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | bulwark_max: 3.0<br>bulwark_min: 1.0<br>每級傷害係數/倍率: +0.02 |
| `sanctuary_light` | **聖所之光** | 主動 | 物理傷害 | - | 5 回合 | -1 | 友方 遠程/全範圍 (1體) | bulwark_max: 3.0<br>bulwark_min: 1.0<br>最大生命值: 80.0<br>hp_min: 40.0<br>每級最大生命值: +6.0<br>每級hp_min: +3.0 |
| `snowball_toss` | **擲雪球** | 主動 | 冰霜傷害 | 60% | 5 回合 | 1 | 敵方 遠程/全範圍 (1體) | 額外傷害加成: 0.2<br>冰凍觸發機率: 0.45<br>每級傷害係數/倍率: +0.04 |
| `frost_control` | **寒冷掌控** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 冰霜傷害加深 (%): 20.0<br>冰霜抗性 (%): 40.0<br>魔法抗性 (%): 10.0<br>物理抗性 (%): 10.0<br>每級冰霜傷害加深 (%): +2.0<br>每級冰霜抗性 (%): +4.0 |
| `avalanche_charge` | **雪崩衝撞** | 主動 | 物理傷害 | 125% | 10 回合 | -3 | 敵方 全體 (1體) | 冰凍觸發機率: 0.25<br>每級傷害係數/倍率: +0.06 |
| `great_bear_strength` | **巨熊神力 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 增益觸發機率: 0.1<br>critical_strike_max: 3.0<br>critical_strike_min: 1.0<br>damage_surge_max: 2.0<br>damage_surge_min: 1.0<br>每級增益觸發機率: +0.015 |

### ⚔️ 【法師 (元素使)】系列英雄 (9 位)

#### 🔹 hero_mage_1 - 法師 (元素使) (普通 (白))
- **基本資料**：種族 `人類` | 性別 `女` | 稀有度星級 `0.0`
- **初始裝備**：main_hand: `staff_001`, off_hand: `book_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `scorching_touch` | **scorching_touch** | 主動 | 火焰傷害 | 50% | 5 回合 | 1 | 敵方 近戰目標 (1體) | fire_chance: 0.75<br>fire_max: 5.0<br>fire_min: 3.0<br>每級傷害係數/倍率: +0.02 |

#### 🔹 hero_mage_2 - 法師 (元素使) (優秀 (綠))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `1.0`
- **初始裝備**：main_hand: `staff_001`, off_hand: `book_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `scorching_touch` | **scorching_touch** | 主動 | 火焰傷害 | 50% | 5 回合 | 1 | 敵方 近戰目標 (1體) | fire_chance: 0.75<br>fire_max: 5.0<br>fire_min: 3.0<br>每級傷害係數/倍率: +0.02 |
| `flame_dart` | **烈焰飛鏢** | 主動 | 火焰傷害 | 45% | 5 回合 | 0 | 敵方 遠程/全範圍 (3體) | fire_chance: 0.25<br>fire_count: 2.0<br>每級傷害係數/倍率: +0.02 |

#### 🔹 hero_mage_3 - 法師 (元素使) (稀有 (藍))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `2.0`
- **初始裝備**：main_hand: `staff_002`, off_hand: `book_002`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `frostbolt` | **寒冰箭** | 主動 | 冰霜傷害 | 120% | 3 回合 | 0 | 敵方 遠程/全範圍 (1體) | 冰凍觸發機率: 0.25<br>每級傷害係數/倍率: +0.02 |
| `frost_shield` | **冰霜護盾** | 主動 | 物理傷害 | - | 5 回合 | -1 | 友方 遠程/全範圍 (1體) | armor_max: 80.0<br>armor_min: 40.0<br>frost_barrier_round: 3.0<br>每級armor_max: +4.0<br>每級armor_min: +2.0 |
| `fireball` | **火球術** | 主動 | 火焰傷害 | 150% | 5 回合 | 0 | 敵方 遠程/全範圍 (1體) | fire_chance: 0.45<br>fire_round: 3.0<br>每級傷害係數/倍率: +0.1 |

#### 🔹 hero_mage_4 - 法師 (元素使) (史詩 (紫))
- **基本資料**：種族 `精靈` | 性別 `男` | 稀有度星級 `3.0`
- **初始裝備**：main_hand: `staff_003`, off_hand: `book_003`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `scorching_touch` | **scorching_touch** | 主動 | 火焰傷害 | 50% | 5 回合 | 1 | 敵方 近戰目標 (1體) | fire_chance: 0.75<br>fire_max: 5.0<br>fire_min: 3.0<br>每級傷害係數/倍率: +0.02 |
| `flame_dart` | **烈焰飛鏢** | 主動 | 火焰傷害 | 45% | 5 回合 | 0 | 敵方 遠程/全範圍 (3體) | fire_chance: 0.25<br>fire_count: 2.0<br>每級傷害係數/倍率: +0.02 |
| `fireball` | **火球術** | 主動 | 火焰傷害 | 150% | 5 回合 | 0 | 敵方 遠程/全範圍 (1體) | fire_chance: 0.45<br>fire_round: 3.0<br>每級傷害係數/倍率: +0.1 |
| `blaze_wrath` | **熾烈之怒** | 主動 | 火焰傷害 | 80% | 7 回合 | -3 | 敵方 遠程/全範圍 (1體) | fire_chance: 0.25<br>fire_max: 5.0<br>fire_min: 1.0<br>fire_offset: 0.25<br>隨機連擊次數: 2.0<br>每級傷害係數/倍率: +0.02 |

#### 🔹 hero_mage_5 - 法師 (元素使) (傳說 (橘))
- **基本資料**：種族 `人類` | 性別 `女` | 稀有度星級 `4.0`
- **初始裝備**：main_hand: `staff_mage_5`, off_hand: `book_mage_5`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `frostbolt` | **寒冰箭** | 主動 | 冰霜傷害 | 120% | 3 回合 | 0 | 敵方 遠程/全範圍 (1體) | 冰凍觸發機率: 0.25<br>每級傷害係數/倍率: +0.02 |
| `frostshot` | **冰霜凝結箭** | 主動 | 冰霜傷害 | 25% | 5 回合 | 1 | 敵方 遠程/全範圍 (3體) | 能量獲得機率: 0.25<br>每級傷害係數/倍率: +0.02 |
| `mass_frost_shield` | **群體冰霜護盾** | 主動 | 物理傷害 | - | 10 回合 | -3 | 友方 全體 (1體) | armor_max: 60.0<br>armor_min: 30.0<br>frost_barrier_max: 7.0<br>frost_barrier_min: 5.0<br>每級armor_max: +6.0<br>每級armor_min: +3.0 |
| `frost_control` | **寒冷掌控** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 冰霜傷害加深 (%): 20.0<br>冰霜抗性 (%): 40.0<br>魔法抗性 (%): 10.0<br>物理抗性 (%): 10.0<br>每級冰霜傷害加深 (%): +2.0<br>每級冰霜抗性 (%): +4.0 |
| `glacial_impale` | **冰川貫穿** | 主動 | 冰霜傷害 | 80% | 7 回合 | -3 | 敵方 遠程/全範圍 (3體) | 冰凍觸發機率: 0.25<br>每級傷害係數/倍率: +0.03 |

#### 🔹 hero_mage_6 - 法師 (元素使) (神話 (紅))
- **基本資料**：種族 `夜幕幽裔` | 性別 `男` | 稀有度星級 `5.0`
- **初始裝備**：main_hand: `staff_mage_6`, off_hand: `book_mage_6`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `soulfire_maw` | **魂火巨口** | 主動 | 火焰傷害 | 60% | 5 回合 | 1 | 敵方 遠程/全範圍 (1體) | energy_count: 1.0<br>每級傷害係數/倍率: +0.02 |
| `flame_dart` | **烈焰飛鏢** | 主動 | 火焰傷害 | 45% | 5 回合 | 0 | 敵方 遠程/全範圍 (3體) | fire_chance: 0.25<br>fire_count: 2.0<br>每級傷害係數/倍率: +0.02 |
| `flamebound_sacrifice` | **flamebound_sacrifice** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.05<br>fire_max: 9.0<br>fire_min: 7.0<br>hp_offset: 0.15<br>每級額外傷害加成: +0.01<br>每級hp_offset: +0.01 |
| `ember_infusion` | **餘燼灌注 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.03<br>每級額外傷害加成: +0.002 |
| `fire_control` | **火焰掌控 (被動)** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 火焰傷害加深 (%): 20.0<br>火焰抗性 (%): 40.0<br>魔法抗性 (%): 10.0<br>物理抗性 (%): 10.0<br>每級火焰傷害加深 (%): +2.0<br>每級火焰抗性 (%): +4.0 |
| `rolling_fireball` | **滾動巨炎球** | 主動 | 火焰傷害 | 200% | 10 回合 | -3 | 敵方 全體 (1體) | fire_chance: 0.25<br>fire_max: 5.0<br>fire_min: 3.0<br>hp_offset: 0.2<br>每級傷害係數/倍率: +0.15 |

#### 🔹 hero_mage_7 - 法師 (元素使) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `樹精/樹人` | 性別 `男` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `staff_mage_7`, off_hand: `book_mage_7`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `root_snare` | **纏繞根鬚** | 主動 | 自然傷害 | 120% | 5 回合 | -1 | 敵方 遠程/全範圍 (1體) | immobilize_chance: 0.25<br>immobilize_max: 3.0<br>immobilize_min: 1.0<br>每級傷害係數/倍率: +0.02 |
| `ancient_resilience` | **遠古韌性 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.1<br>hp_offset: 0.3<br>red_chance: 0.4<br>每級額外傷害加成: +0.005<br>每級red_chance: +0.01 |
| `forest_wrath` | **森林之怒** | 主動 | 自然傷害 | 60% | 3 回合 | -3 | 敵方 遠程/全範圍 (3體) | heal_offset_max: 0.05<br>heal_offset_min: 0.01<br>每級傷害係數/倍率: +0.02 |
| `nature_control` | **自然掌控 (被動)** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 魔法抗性 (%): 10.0<br>自然傷害加深 (%): 20.0<br>自然抗性 (%): 40.0<br>物理抗性 (%): 10.0<br>每級自然傷害加深 (%): +2.0<br>每級自然抗性 (%): +4.0 |
| `witherbind` | **枯萎束縛** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | wither_chance: 0.1<br>wither_max: 3.0<br>wither_min: 1.0<br>每級wither_chance: +0.01 |
| `withering_touch` | **枯萎觸碰** | 主動 | 自然傷害 | 200% | 10 回合 | -2 | 敵方 遠程/全範圍 (1體) | wither_max: 5.0<br>wither_min: 3.0<br>每級傷害係數/倍率: +0.12 |
| `thornstorm` | **荊棘風暴** | 被動 | 自然傷害 | 30% | 無 CD | 0 | 敵方 單體 (1體) | active_chance: 0.45<br>流血觸發機率: 0.25<br>流血層數上限: 5.0<br>流血基礎層數: 3.0<br>count_max: 5.0<br>count_min: 3.0<br>每級active_chance: +0.03<br>每級傷害係數/倍率: +0.01 |

#### 🔹 hero_mage_ecasia - 法師 (元素使) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `精靈` | 性別 `女` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `staff_mage_ecasia`, off_hand: `book_mage_ecasia`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `frostscar_spike` | **冰痕之刺** | 主動 | 物理傷害 | 50% | 10 回合 | -1 | 敵方 遠程/全範圍 (1體) | 冰凍觸發機率: 0.15<br>霜痕層數上限: 3.0<br>霜痕基礎層數: 2.0<br>每級傷害係數/倍率: +0.02 |
| `shardspire_entombment` | **霜棘冰葬** | 主動 | 物理傷害 | 40% | 5 回合 | -2 | 敵方 遠程/全範圍 (2體) | 增益觸發機率: 0.15<br>每級傷害係數/倍率: +0.01 |
| `shardspire_cataclysm` | **霜棘殞滅** | 主動 | 物理傷害 | 25% | 7 回合 | -3 | 敵方 全體 (5體) | 增益觸發機率: 0.15<br>每級傷害係數/倍率: +0.01 |
| `frost_control` | **寒冷掌控** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 冰霜傷害加深 (%): 20.0<br>冰霜抗性 (%): 40.0<br>魔法抗性 (%): 10.0<br>物理抗性 (%): 10.0<br>每級冰霜傷害加深 (%): +2.0<br>每級冰霜抗性 (%): +4.0 |
| `icy_soul_echo` | **冰魂迴響 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 獲得行動點機率: 0.15<br>能量獲得機率: 0.35<br>每級獲得行動點機率: +0.01<br>每級能量獲得機率: +0.01 |
| `frostglyph_aegis` | **霜紋庇護** | 主動 | 物理傷害 | 200% | 7 回合 | -1 | 友方 遠程/全範圍 (1體) | 每級傷害係數/倍率: +0.2 |
| `icethorn_demise` | **冰刺終局 (被動)** | 被動 | 輔助/被動 | 120% | 無 CD | 0 | 敵方 單體 (1體) | 霜痕觸發機率: 0.25<br>霜痕附加層數: 5.0<br>每級傷害係數/倍率: +0.07 |

#### 🔹 hero_mage_nobiz - 法師 (元素使) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `哥布林` | 性別 `男` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `staff_mage_nobiz`, off_hand: `book_mage_nobiz`, special: `spceial_nobiz_aircraft`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `chaotic_sparkshot` | **混沌火花射擊** | 主動 | 魔法傷害 | 120% | 5 回合 | -1 | 敵方 遠程/全範圍 (1體) | damage_offset_extra: 0.5<br>darkness_max: 5.0<br>darkness_min: 3.0<br>energy_charge_max: 3.0<br>energy_charge_min: 1.0<br>每級傷害係數/倍率: +0.02 |
| `tinker_reboot` | **修補重啟 (被動)** | 主動 | 物理傷害 | - | 5 回合 | -2 | 友方 自身 (1體) | 充能層數: 3.0<br>heal_offset_max: 0.15<br>heal_offset_min: 0.05<br>每級heal_offset_max: +0.01<br>每級heal_offset_min: +0.01 |
| `scrapline_reboot` | **廢料線重啟 (被動)** | 被動 | 輔助/被動 | 35% | 無 CD | 0 | 敵方 單體 (1體) | 充能層數: 1.0<br>每級傷害係數/倍率: +0.04 |
| `gearburst_surge` | **齒輪爆發增幅** | 主動 | 魔法傷害 | 80% | 5 回合 | -2 | 敵方 全體 (1體) | 額外傷害加成: 0.5<br>充能層數: 3.0<br>每級傷害係數/倍率: +0.04 |
| `residual_overcharge` | **殘餘過載 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | energy_charge_chance: 0.15<br>充能層數: 1.0<br>hp_offset: 0.5<br>每級energy_charge_chance: +0.01 |
| `gear_cycle_loop` | **齒輪循環 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | beast_power_count: 1.0<br>增益觸發機率: 0.25<br>check_count: 4.0<br>充能層數: 1.0<br>每級增益觸發機率: +0.02 |
| `gearfire_barrage` | **齒輪彈雨掃射** | 主動 | 物理傷害 | - | 10 回合 | -3 | 敵方 遠程/全範圍 (3體) | 一段傷害倍率: 0.2<br>二段傷害倍率: 0.8<br>fire_chance: 0.45<br>fire_max: 5.0<br>fire_min: 3.0<br>每級一段傷害倍率: +0.02<br>每級二段傷害倍率: +0.04 |

### ⚔️ 【牧師 (神官)】系列英雄 (9 位)

#### 🔹 hero_priest_1 - 牧師 (神官) (普通 (白))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `0.0`
- **初始裝備**：main_hand: `scepter_priest_1`, off_hand: `book_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lesser_heal` | **初級治療術** | 主動 | 物理傷害 | - | 3 回合 | -1 | 友方 遠程/全範圍 (1體) | buff_heal_chance: 0.25<br>buff_heal_max: 3.0<br>buff_heal_min: 1.0<br>heal_offset_max: 0.2<br>heal_offset_min: 0.1<br>每級heal_offset_max: +0.01<br>每級heal_offset_min: +0.01 |

#### 🔹 hero_priest_2 - 牧師 (神官) (優秀 (綠))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `1.0`
- **初始裝備**：main_hand: `scepter_priest_1`, off_hand: `book_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lesser_heal` | **初級治療術** | 主動 | 物理傷害 | - | 3 回合 | -1 | 友方 遠程/全範圍 (1體) | buff_heal_chance: 0.25<br>buff_heal_max: 3.0<br>buff_heal_min: 1.0<br>heal_offset_max: 0.2<br>heal_offset_min: 0.1<br>每級heal_offset_max: +0.01<br>每級heal_offset_min: +0.01 |
| `holy_strike` | **神聖打擊** | 主動 | 神聖傷害 | 120% | 3 回合 | 0 | 敵方 遠程/全範圍 (1體) | 眩暈觸發機率: 0.25<br>每級傷害係數/倍率: +0.02 |

#### 🔹 hero_priest_3 - 牧師 (神官) (稀有 (藍))
- **基本資料**：種族 `人類` | 性別 `女` | 稀有度星級 `2.0`
- **初始裝備**：main_hand: `scepter_priest_2`, off_hand: `book_002`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `lesser_heal` | **初級治療術** | 主動 | 物理傷害 | - | 3 回合 | -1 | 友方 遠程/全範圍 (1體) | buff_heal_chance: 0.25<br>buff_heal_max: 3.0<br>buff_heal_min: 1.0<br>heal_offset_max: 0.2<br>heal_offset_min: 0.1<br>每級heal_offset_max: +0.01<br>每級heal_offset_min: +0.01 |
| `blessing_light` | **聖光祈福** | 主動 | 物理傷害 | - | 3 回合 | -2 | 友方 遠程/全範圍 (1體) | blessing_chance: 0.25<br>blessing_round: 3.0 |
| `mass_healing` | **群體治療術** | 主動 | 物理傷害 | - | 10 回合 | -3 | 友方 全體 (1體) | buff_heal_chance: 0.25<br>buff_heal_max: 3.0<br>buff_heal_min: 1.0<br>heal_offset_max: 0.2<br>heal_offset_min: 0.1<br>每級heal_offset_max: +0.01<br>每級heal_offset_min: +0.01 |

#### 🔹 hero_priest_4 - 牧師 (神官) (史詩 (紫))
- **基本資料**：種族 `骷髏` | 性別 `男` | 稀有度星級 `3.0`
- **初始裝備**：main_hand: `scepter_priest_3`, off_hand: `book_003`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `curse_agony` | **痛苦折磨詛咒** | 主動 | 暗影傷害 | 120% | 5 回合 | -1 | 敵方 遠程/全範圍 (1體) | count_max: 3.0<br>count_min: 2.0<br>每級傷害係數/倍率: +0.02 |
| `touch_void` | **虛空之觸** | 主動 | 暗影傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | darkness_chance: 0.25<br>darkness_count: 3.0<br>restore_rate: 0.25<br>每級傷害係數/倍率: +0.04 |
| `dark_sanctuary` | **暗影庇護所** | 主動 | 物理傷害 | - | 5 回合 | -2 | 友方 遠程/全範圍 (1體) | armor_offset: 0.2<br>darkness_max: 6.0<br>darkness_min: 3.0<br>每級armor_offset: +0.015 |
| `mass_curse` | **群體詛咒** | 主動 | 暗影傷害 | 80% | 7 回合 | -3 | 敵方 全體 (1體) | count_max: 3.0<br>count_min: 2.0<br>每級傷害係數/倍率: +0.04 |

#### 🔹 hero_priest_5 - 牧師 (神官) (傳說 (橘))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `4.0`
- **初始裝備**：main_hand: `scepter_priest_5`, off_hand: `book_priest_5`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `divine_verdict` | **神聖裁決** | 主動 | 神聖傷害 | 120% | 3 回合 | 0 | 敵方 遠程/全範圍 (1體) | silence_chance: 0.25<br>silence_round: 2.0<br>每級傷害係數/倍率: +0.02 |
| `holy_strike` | **神聖打擊** | 主動 | 神聖傷害 | 120% | 3 回合 | 0 | 敵方 遠程/全範圍 (1體) | 眩暈觸發機率: 0.25<br>每級傷害係數/倍率: +0.02 |
| `mass_healing` | **群體治療術** | 主動 | 物理傷害 | - | 10 回合 | -3 | 友方 全體 (1體) | buff_heal_chance: 0.25<br>buff_heal_max: 3.0<br>buff_heal_min: 1.0<br>heal_offset_max: 0.2<br>heal_offset_min: 0.1<br>每級heal_offset_max: +0.01<br>每級heal_offset_min: +0.01 |
| `heaven_toll` | **天堂鳴鐘** | 主動 | 神聖傷害 | 100% | 7 回合 | -3 | 敵方 全體 (1體) | 眩暈觸發機率: 0.25<br>每級傷害係數/倍率: +0.05 |
| `dreadlight_echo` | **恐懼光芒迴響** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | dreadlight_mark_chance: 0.15<br>dreadlight_mark_max: 3.0<br>dreadlight_mark_min: 1.0<br>每級dreadlight_mark_chance: +0.01 |

#### 🔹 hero_priest_6 - 牧師 (神官) (神話 (紅))
- **基本資料**：種族 `幽靈/亡魂` | 性別 `unknown` | 稀有度星級 `5.0`
- **初始裝備**：main_hand: `scepter_priest_6`, off_hand: `book_priest_6`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `curse_agony` | **痛苦折磨詛咒** | 主動 | 暗影傷害 | 120% | 5 回合 | -1 | 敵方 遠程/全範圍 (1體) | count_max: 3.0<br>count_min: 2.0<br>每級傷害係數/倍率: +0.02 |
| `void_fingers` | **虛空指引** | 主動 | 暗影傷害 | 80% | 7 回合 | 1 | 敵方 遠程/全範圍 (1體) | energy_count: 1.0<br>每級傷害係數/倍率: +0.02 |
| `dark_sanctuary` | **暗影庇護所** | 主動 | 物理傷害 | - | 5 回合 | -2 | 友方 遠程/全範圍 (1體) | armor_offset: 0.2<br>darkness_max: 6.0<br>darkness_min: 3.0<br>每級armor_offset: +0.015 |
| `darkness_implosion` | **暗影內爆** | 主動 | 暗影傷害 | 100% | 7 回合 | -3 | 敵方 全體 (1體) | 能量獲得機率: 0.25<br>energy_count: 1.0<br>每級傷害係數/倍率: +0.05 |
| `soul_rend` | **靈魂撕裂** | 主動 | 暗影傷害 | 200% | 7 回合 | -3 | 敵方 近戰目標 (1體) | vital_blockade_max: 7.0<br>vital_blockade_min: 5.0<br>每級傷害係數/倍率: +0.1 |
| `departed_oath` | **逝者誓約** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | darkness_max: 7.0<br>darkness_min: 5.0<br>energy_count: 1.0<br>治療係數/倍率: 0.4<br>heal_times: 3.0<br>hp_offset: 0.5<br>每級治療係數/倍率: +0.04 |

#### 🔹 hero_priest_7 - 牧師 (神官) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `獸人` | 性別 `unknown` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `scepter_priest_7`, off_hand: `book_priest_7`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shellcurse` | **甲殼詛咒** | 主動 | 暗影傷害 | 100% | 5 回合 | -1 | 敵方 遠程/全範圍 (1體) | brooding_egg_round: 3.0<br>每級傷害係數/倍率: +0.02 |
| `broodmother_command_hero` | **母巢之令** | 主動 | 毒素傷害 | 45% | 5 回合 | -2 | 敵方 遠程/全範圍 (3體) | 中毒層數上限: 3.0<br>中毒基礎層數: 1.0<br>每級傷害係數/倍率: +0.02 |
| `toxic_plague` | **劇毒瘟疫** | 主動 | 毒素傷害 | 85% | 5 回合 | -3 | 敵方 全體 (1體) | 中毒層數上限: 3.0<br>中毒基礎層數: 1.0<br>每級傷害係數/倍率: +0.04 |
| `venomous_wail` | **毒液哀嚎** | 主動 | 毒素傷害 | 80% | 7 回合 | -3 | 敵方 全體 (1體) | buff_max: 6.0<br>buff_min: 4.0<br>egg_chance: 0.15<br>每級傷害係數/倍率: +0.04<br>每級egg_chance: +0.01 |
| `poison_control` | **毒術掌控 (被動)** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 魔法抗性 (%): 10.0<br>物理抗性 (%): 10.0<br>毒素傷害加深 (%): 20.0<br>毒素抗性 (%): 40.0<br>每級毒素傷害加深 (%): +2.0<br>每級毒素抗性 (%): +4.0 |
| `brooding_cycle` | **育卵輪迴** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.1<br>egg_chance: 0.15<br>每級額外傷害加成: +0.01<br>每級egg_chance: +0.01 |
| `brood_awakening` | **巢穴覺醒 (被動)** | 被動 | 輔助/被動 | 100% | 無 CD | 0 | 敵方 單體 (1體) | 能量獲得機率: 0.25<br>中毒觸發機率: 0.25<br>中毒層數上限: 3.0<br>中毒基礎層數: 1.0<br>spider_round: 5.0<br>每級傷害係數/倍率: +0.075<br>每級中毒觸發機率: +0.02 |

#### 🔹 hero_priest_aldrian - 牧師 (神官) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `人類` | 性別 `unknown` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `scepter_priest_aldrian`, off_hand: `book_priest_aldrian`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `benediction_fountain` | **祝福之泉** | 主動 | 物理傷害 | - | 7 回合 | -1 | 友方 遠程/全範圍 (1體) | blessing_count: 3.0<br>heal_offset_1: 0.15<br>heal_offset_2: 0.1<br>持續回合數: 3.0<br>每級heal_offset_1: +0.01<br>每級heal_offset_2: +0.005 |
| `divine_revelation_smite` | **啟示神罰** | 主動 | 神聖傷害 | 120% | 5 回合 | -2 | 敵方 遠程/全範圍 (1體) | damage_offset_extra: 0.5<br>每級傷害係數/倍率: +0.04 |
| `radiance_purity` | **純淨光輝** | 主動 | 物理傷害 | - | 7 回合 | -1 | 友方 遠程/全範圍 (1體) | extra_chance: 0.25<br>heal_offset_max: 0.15<br>heal_offset_min: 0.05<br>remove_count: 2.0<br>remove_count_extra: 1.0<br>每級extra_chance: +0.02<br>每級heal_offset_max: +0.01<br>每級heal_offset_min: +0.05 |
| `heaven_Judicium` | **天堂審判 (被動)** | 主動 | 神聖傷害 | 60% | 5 回合 | -2 | 敵方 全體 (1體) | dreadlight_mark_chance: 0.45<br>dreadlight_mark_max: 3.0<br>dreadlight_mark_min: 1.0<br>times: 3.0<br>每級傷害係數/倍率: +0.02 |
| `ancient_ecclesiarch` | **遠古大主教之魂** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | damage_bouns_1: 0.15<br>damage_bouns_2: 0.15<br>每級damage_bouns_1: +0.01<br>每級damage_bouns_2: +0.01 |
| `dawnlight_renewal` | **晨光復甦 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | buff_heal_max: 3.0<br>buff_heal_min: 1.0<br>heal_chance: 0.35<br>heal_offset_max: 0.15<br>heal_offset_min: 0.05<br>每級heal_chance: +0.02 |
| `apostolic_revival` | **使徒復生 (被動)** | 主動 | 物理傷害 | - | 20 回合 | -3 | 友方 陣亡目標 (1體) | blessing_count: 6.0<br>治療係數/倍率: 0.45<br>每級blessing_count: +1.0<br>每級治療係數/倍率: +0.05 |

#### 🔹 hero_priest_bathory - 牧師 (神官) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `惡魔` | 性別 `unknown` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `scepter_priest_bathory`, off_hand: `book_priest_bathory`, special: `spceial_demon_bathory`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shadow_stitching` | **暗影縫合** | 主動 | 物理傷害 | - | 3 回合 | 1 | 友方 遠程/全範圍 (1體) | heal_bouns: 0.05<br>治療係數/倍率: 0.05<br>vital_blockade_count: 3.0<br>每級heal_bouns: +0.005 |
| `scarlet_meditation` | **猩紅冥想 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | vital_blockade_chance: 0.45<br>vital_blockade_count: 1.0<br>每級vital_blockade_chance: +0.03 |
| `flesh_altar` | **血肉祭壇** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.01<br>每級額外傷害加成: +0.001 |
| `soul_rending_roar` | **噬魂咆哮** | 主動 | 暗影傷害 | 100% | 7 回合 | -3 | 敵方 全體 (1體) | vital_blockade_count: 5.0<br>虛弱層數上限: 7.0<br>虛弱基礎層數: 5.0<br>每級傷害係數/倍率: +0.05 |
| `remote_eecortication` | **remote_eecortication** | 主動 | 物理傷害 | 80% | 5 回合 | -2 | 敵方 遠程/全範圍 (3體) | flayed_chance: 0.75<br>每級傷害係數/倍率: +0.02 |
| `hell_pact_reset` | **地獄契約重置 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | active_chance: 0.25<br>active_round: 5.0<br>buff_max: 5.0<br>buff_min: 1.0<br>每級active_chance: +0.05 |
| `martyr_rawness` | **殉道之勇 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | active_chance: 0.15<br>vital_blockade_max: 3.0<br>vital_blockade_min: 1.0<br>每級active_chance: +0.03 |

### ⚔️ 【刺客 (盜賊)】系列英雄 (9 位)

#### 🔹 hero_rogue_1 - 刺客 (盜賊) (普通 (白))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `0.0`
- **初始裝備**：main_hand: `dagger_001`, off_hand: `dagger_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `toxic_strike` | **浸毒打擊** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 近戰目標 (1體) | poison_round: 3.0<br>每級傷害係數/倍率: +0.02 |

#### 🔹 hero_rogue_2 - 刺客 (盜賊) (優秀 (綠))
- **基本資料**：種族 `精靈` | 性別 `男` | 稀有度星級 `1.0`
- **初始裝備**：main_hand: `dagger_001`, off_hand: `dagger_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `toxic_strike` | **浸毒打擊** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 近戰目標 (1體) | poison_round: 3.0<br>每級傷害係數/倍率: +0.02 |
| `sinister_strike` | **邪惡攻擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | 獲得行動點機率: 0.75<br>每級傷害係數/倍率: +0.04 |

#### 🔹 hero_rogue_3 - 刺客 (盜賊) (稀有 (藍))
- **基本資料**：種族 `人類` | 性別 `女` | 稀有度星級 `2.0`
- **初始裝備**：main_hand: `dagger_002`, off_hand: `dagger_002`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `toxic_strike` | **浸毒打擊** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 近戰目標 (1體) | poison_round: 3.0<br>每級傷害係數/倍率: +0.02 |
| `sinister_strike` | **邪惡攻擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | 獲得行動點機率: 0.75<br>每級傷害係數/倍率: +0.04 |
| `stealthy_ambush` | **潛行伏擊** | 主動 | 物理傷害 | - | 5 回合 | 0 | 友方 自身 (1體) | buff_dodge_chance: 0.25<br>buff_dodge_max: 5.0<br>buff_dodge_min: 3.0<br>stealth_max: 1.0<br>stealth_min: 1.0 |

#### 🔹 hero_rogue_4 - 刺客 (盜賊) (史詩 (紫))
- **基本資料**：種族 `夜幕幽裔` | 性別 `男` | 稀有度星級 `3.0`
- **初始裝備**：main_hand: `dagger_003`, off_hand: `dagger_003`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shadow_embrace` | **暗影擁抱 (被動)** | 主動 | 物理傷害 | - | 7 回合 | 1 | 友方 自身 (1體) | 增益觸發機率: 0.45<br>buff_max: 5.0<br>buff_min: 3.0<br>每級增益觸發機率: +0.03 |
| `sinister_strike` | **邪惡攻擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | 獲得行動點機率: 0.75<br>每級傷害係數/倍率: +0.04 |
| `stealthy_ambush` | **潛行伏擊** | 主動 | 物理傷害 | - | 5 回合 | 0 | 友方 自身 (1體) | buff_dodge_chance: 0.25<br>buff_dodge_max: 5.0<br>buff_dodge_min: 3.0<br>stealth_max: 1.0<br>stealth_min: 1.0 |
| `backstab` | **背刺** | 主動 | 物理傷害 | 170% | 5 回合 | -3 | 敵方 遠程/全範圍 (1體) | 流血層數上限: 5.0<br>流血基礎層數: 3.0<br>每級傷害係數/倍率: +0.1 |

#### 🔹 hero_rogue_5 - 刺客 (盜賊) (傳說 (橘))
- **基本資料**：種族 `骷髏` | 性別 `男` | 稀有度星級 `4.0`
- **初始裝備**：main_hand: `dagger_rogue_5`, off_hand: `dagger_rogue_5`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `toxic_strike` | **浸毒打擊** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 近戰目標 (1體) | poison_round: 3.0<br>每級傷害係數/倍率: +0.02 |
| `bone_dart` | **白骨飛鏢** | 主動 | 物理傷害 | 60% | 3 回合 | 0 | 敵方 遠程/全範圍 (2體) | 中毒觸發機率: 0.25<br>中毒層數上限: 3.0<br>中毒基礎層數: 1.0<br>虛弱觸發機率: 0.25<br>虛弱層數上限: 2.0<br>虛弱基礎層數: 1.0<br>每級傷害係數/倍率: +0.02 |
| `venomous_veil` | **毒霧面紗** | 主動 | 毒素傷害 | 85% | 5 回合 | -3 | 敵方 全體 (1體) | 中毒觸發機率: 0.25<br>中毒層數上限: 5.0<br>中毒基礎層數: 3.0<br>stealth_round: 1.0<br>每級傷害係數/倍率: +0.04 |
| `backstab` | **背刺** | 主動 | 物理傷害 | 170% | 5 回合 | -3 | 敵方 遠程/全範圍 (1體) | 流血層數上限: 5.0<br>流血基礎層數: 3.0<br>每級傷害係數/倍率: +0.1 |
| `venom_recycle` | **毒素萃取回收 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 能量獲得機率: 0.45<br>每級能量獲得機率: +0.04 |

#### 🔹 hero_rogue_6 - 刺客 (盜賊) (神話 (紅))
- **基本資料**：種族 `不死族` | 性別 `男` | 稀有度星級 `5.0`
- **初始裝備**：main_hand: `dagger_rogue_6`, off_hand: `dagger_rogue_6`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `marking_dagger` | **標記飛匕** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 遠程/全範圍 (1體) | death_mark_round: 1.0<br>每級傷害係數/倍率: +0.02 |
| `shadowfang_toss` | **影牙投擲** | 主動 | 物理傷害 | 120% | 7 回合 | -1 | 敵方 遠程/全範圍 (1體) | 流血觸發機率: 0.25<br>流血層數上限: 5.0<br>流血基礎層數: 3.0<br>death_mark_max: 1.0<br>silence_round: 3.0<br>每級傷害係數/倍率: +0.04 |
| `stealthy_ambush` | **潛行伏擊** | 主動 | 物理傷害 | - | 5 回合 | 0 | 友方 自身 (1體) | buff_dodge_chance: 0.25<br>buff_dodge_max: 5.0<br>buff_dodge_min: 3.0<br>stealth_max: 1.0<br>stealth_min: 1.0 |
| `silent_execution` | **無聲處決** | 主動 | 物理傷害 | 170% | 5 回合 | -3 | 敵方 遠程/全範圍 (1體) | 額外傷害加成: 0.5<br>每級傷害係數/倍率: +0.1 |
| `death_omen` | **死亡預兆** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | death_mark_chance: 0.15<br>每級death_mark_chance: +0.01 |
| `deathbound_pressure` | **deathbound_pressure** | 主動 | 物理傷害 | 245% | 10 回合 | -2 | 敵方 遠程/全範圍 (1體) | 額外傷害加成: 0.1<br>kill_chance: 0.1<br>每級傷害係數/倍率: +0.12 |

#### 🔹 hero_rogue_7 - 刺客 (盜賊) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `精靈` | 性別 `女` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `dagger_rogue_7`, off_hand: `dagger_rogue_7`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `oath_blade` | **誓約之刃** | 主動 | 物理傷害 | - | 7 回合 | -1 | 敵方 遠程/全範圍 (1體) | 增益觸發機率: 0.75<br>一段傷害倍率: 0.6<br>二段傷害倍率: 0.2<br>每級一段傷害倍率: +0.02<br>每級二段傷害倍率: +0.02 |
| `duskblade_return` | **暮刃歸宗 (被動)** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 遠程/全範圍 (1體) | 暴擊觸發率: 0.5<br>持續回合數: 3.0<br>每級傷害係數/倍率: +0.04 |
| `moonshadow_slash` | **月影斬** | 主動 | 物理傷害 | - | 5 回合 | -2 | 敵方 近戰目標 (1體) | 一段傷害倍率: 1.6<br>二段傷害倍率: 0.5<br>silence_chance: 0.45<br>每級一段傷害倍率: +0.06 |
| `shadow_protection` | **暗影守護** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | buff_dodge_chance: 0.45<br>buff_dodge_max: 5.0<br>buff_dodge_min: 3.0<br>每級buff_dodge_chance: +0.03 |
| `lunar_judgment` | **月之裁決** | 被動 | 輔助/被動 | 50% | 無 CD | 0 | 敵方 單體 (1體) | darkness_chance: 0.45<br>darkness_max: 3.0<br>darkness_min: 1.0<br>hp_offset: 0.5<br>每級傷害係數/倍率: +0.05 |
| `twilight_dominion` | **暮光支配 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.15<br>stealth_chance: 0.15<br>每級額外傷害加成: +0.01<br>每級stealth_chance: +0.01 |
| `lunar_bladefall` | **月刃天降** | 主動 | 物理傷害 | - | 7 回合 | -3 | 敵方 全體 (1體) | count: 5.0<br>一段傷害倍率: 0.7<br>二段傷害倍率: 0.4<br>hp_offset: 0.3<br>每級一段傷害倍率: +0.03<br>每級二段傷害倍率: +0.03 |

#### 🔹 hero_rogue_sien - 刺客 (盜賊) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `dagger_rotue_sien`, off_hand: `dagger_rotue_sien`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `darkfeather_flurry` | **darkfeather_flurry** | 主動 | 物理傷害 | 50% | 5 回合 | -1 | 敵方 全體 (1體) | death_mark_chance: 0.25<br>每級傷害係數/倍率: +0.01 |
| `nightcrow_pierce` | **夜鴉穿刺** | 主動 | 物理傷害 | 120% | 5 回合 | -2 | 敵方 遠程/全範圍 (1體) | damage_offset_darkness: 0.5<br>death_mark_chance: 0.75<br>每級傷害係數/倍率: +0.04 |
| `ravenfeather_hunt` | **鴉羽追獵** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | reset_chance: 0.35<br>每級reset_chance: +0.02 |
| `darkfeather_impale` | **darkfeather_impale** | 主動 | 物理傷害 | 60% | 5 回合 | -2 | 敵方 遠程/全範圍 (1體) | 每級傷害係數/倍率: +0.02 |
| `shadowstep_resurgence` | **影步復甦 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | buff_dodge_chance: 0.15<br>buff_dodge_check_count: 3.0<br>buff_dodge_count: 7.0<br>每級buff_dodge_chance: +0.01 |
| `nightcrow_ascension` | **夜鴉飛昇 (被動)** | 主動 | 物理傷害 | - | 10 回合 | -2 | 友方 自身 (1體) | skill_chance: 0.0<br>每級skill_chance: +0.1 |
| `deathmark_verdict` | **死印判決** | 被動 | 輔助/被動 | 100% | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.05<br>extra_chance: 0.45<br>每級傷害係數/倍率: +0.05<br>每級extra_chance: +0.03 |

#### 🔹 hero_rogue_vilzaan - 刺客 (盜賊) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `惡魔` | 性別 `unknown` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `dagger_demon_vilzaan`, off_hand: `dagger_demon_vilzaan`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shadow_embrace` | **暗影擁抱 (被動)** | 主動 | 物理傷害 | - | 7 回合 | 1 | 友方 自身 (1體) | 增益觸發機率: 0.45<br>buff_max: 5.0<br>buff_min: 3.0<br>每級增益觸發機率: +0.03 |
| `oath_blade` | **誓約之刃** | 主動 | 物理傷害 | - | 7 回合 | -1 | 敵方 遠程/全範圍 (1體) | 增益觸發機率: 0.75<br>一段傷害倍率: 0.6<br>二段傷害倍率: 0.2<br>每級一段傷害倍率: +0.02<br>每級二段傷害倍率: +0.02 |
| `abyssal_lunge` | **深淵穿刺突進** | 主動 | 物理傷害 | 160% | 5 回合 | -2 | 敵方 遠程/全範圍 (1體) | abyss_seed_max: 3.0<br>abyss_seed_min: 1.0<br>每級傷害係數/倍率: +0.06 |
| `abyss_sunder` | **深淵撕裂** | 主動 | 物理傷害 | 160% | 7 回合 | -2 | 敵方 遠程/全範圍 (1體) | abyss_seed_count: 3.0<br>驅散機率: 0.75<br>每級傷害係數/倍率: +0.08 |
| `abyssal_mutation` | **深淵異變** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | abyss_seed_max: 3.0<br>abyss_seed_min: 1.0<br>額外傷害加成: 0.05<br>hp_offset_bouns: 0.15<br>每級額外傷害加成: +0.01<br>每級hp_offset_bouns: +0.01 |
| `mutant_flame_stalk` | **mutant_flame_stalk** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | active_chance: 0.15<br>active_round: 5.0<br>額外傷害加成: 0.15<br>stealth_chance: 0.15<br>每級active_round: +1.0 |
| `abysscreep_mutation` | **深淵蔓延異變 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 增益觸發機率: 0.25<br>一段傷害倍率: 1.5<br>二段傷害倍率: 1.0<br>三段傷害倍率: 1.0<br>debuff_chance: 0.45<br>debuff_max: 5.0<br>debuff_min: 1.0<br>每級增益觸發機率: +0.02<br>每級一段傷害倍率: +0.05<br>每級二段傷害倍率: +0.05<br>每級三段傷害倍率: +0.05 |

### ⚔️ 【戰士 (狂戰士)】系列英雄 (9 位)

#### 🔹 hero_warrior_1 - 戰士 (狂戰士) (普通 (白))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `0.0`
- **初始裝備**：main_hand: `sword_001`, off_hand: `shield_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `thump` | **重踏痛擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | 眩暈觸發機率: 0.25<br>每級傷害係數/倍率: +0.02 |

#### 🔹 hero_warrior_2 - 戰士 (狂戰士) (優秀 (綠))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `1.0`
- **初始裝備**：main_hand: `sword_001`, off_hand: `shield_001`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `thump` | **重踏痛擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | 眩暈觸發機率: 0.25<br>每級傷害係數/倍率: +0.02 |
| `taunt_skill` | **嘲諷怒吼** | 主動 | 物理傷害 | - | 5 回合 | -1 | 敵方 全體 (1體) | armor_bouns: 0.1<br>min_armor: 30.0<br>每級armor_bouns: +0.01 |

#### 🔹 hero_warrior_3 - 戰士 (狂戰士) (稀有 (藍))
- **基本資料**：種族 `人類` | 性別 `男` | 稀有度星級 `2.0`
- **初始裝備**：main_hand: `sword_002`, off_hand: `shield_002`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `defense_blow` | **防禦重擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | protection_max: 5.0<br>protection_min: 3.0<br>每級傷害係數/倍率: +0.02 |
| `bloody_blow` | **血腥打擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | bleed_round: 3.0<br>每級傷害係數/倍率: +0.02 |
| `mass_defense` | **群體防禦祈禱** | 主動 | 物理傷害 | - | 10 回合 | -3 | 友方 全體 (1體) | armor_max: 40.0<br>armor_min: 20.0<br>protection_max: 7.0<br>protection_min: 5.0<br>每級armor_max: +8.0<br>每級armor_min: +4.0 |

#### 🔹 hero_warrior_4 - 戰士 (狂戰士) (史詩 (紫))
- **基本資料**：種族 `精靈` | 性別 `女` | 稀有度星級 `3.0`
- **初始裝備**：main_hand: `sword_003`, off_hand: `shield_003`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `defense_blow` | **防禦重擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | protection_max: 5.0<br>protection_min: 3.0<br>每級傷害係數/倍率: +0.02 |
| `taunt_skill` | **嘲諷怒吼** | 主動 | 物理傷害 | - | 5 回合 | -1 | 敵方 全體 (1體) | armor_bouns: 0.1<br>min_armor: 30.0<br>每級armor_bouns: +0.01 |
| `mass_defense` | **群體防禦祈禱** | 主動 | 物理傷害 | - | 10 回合 | -3 | 友方 全體 (1體) | armor_max: 40.0<br>armor_min: 20.0<br>protection_max: 7.0<br>protection_min: 5.0<br>每級armor_max: +8.0<br>每級armor_min: +4.0 |
| `concussion_blast` | **震盪爆破** | 主動 | 物理傷害 | 85% | 5 回合 | -3 | 敵方 全體 (1體) | 眩暈觸發機率: 0.25<br>每級傷害係數/倍率: +0.05 |

#### 🔹 hero_warrior_5 - 戰士 (狂戰士) (傳說 (橘))
- **基本資料**：種族 `矮人` | 性別 `男` | 稀有度星級 `4.0`
- **初始裝備**：main_hand: `axe_warrior_5`, off_hand: `shield_warrior_5`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `bloody_blow` | **血腥打擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | bleed_round: 3.0<br>每級傷害係數/倍率: +0.02 |
| `bloodlust_combo` | **嗜血連擊** | 主動 | 物理傷害 | 60% | 3 回合 | 0 | 敵方 近戰目標 (1體) | 流血觸發機率: 0.25<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>combo_times: 2.0<br>每級傷害係數/倍率: +0.02 |
| `deep_wounds` | **深度重傷** | 主動 | 物理傷害 | 150% | 5 回合 | -3 | 敵方 近戰目標 (1體) | bleed_offset: 0.5<br>每級傷害係數/倍率: +0.1 |
| `trauma_blow` | **創傷猛擊** | 主動 | 物理傷害 | 170% | 5 回合 | -3 | 敵方 近戰目標 (1體) | trauma_chance: 1.0<br>trauma_count: 2.0<br>每級傷害係數/倍率: +0.1 |
| `blood_extraction` | **blood_extraction** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | restore_chance: 1.0<br>restore_rate: 0.05<br>每級restore_rate: +0.005 |

#### 🔹 hero_warrior_6 - 戰士 (狂戰士) (神話 (紅))
- **基本資料**：種族 `骷髏` | 性別 `男` | 稀有度星級 `5.0`
- **初始裝備**：main_hand: `sword_warrior_6`, off_hand: `shield_warrior_6`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `defensive_strike` | **防衛反擊** | 主動 | 物理傷害 | 120% | 3 回合 | 0 | 敵方 近戰目標 (1體) | armor_offset: 0.5<br>每級傷害係數/倍率: +0.02 |
| `provoked_fury` | **激怒狂暴** | 主動 | 物理傷害 | - | 7 回合 | -1 | 敵方 遠程/全範圍 (1體) | armor_max: 60.0<br>armor_min: 30.0<br>provocation_round: 3.0<br>weakness_level_chance: 0.25<br>虛弱層數上限: 5.0<br>虛弱基礎層數: 3.0<br>每級armor_max: +6.0<br>每級armor_min: +3.0 |
| `mass_defense` | **群體防禦祈禱** | 主動 | 物理傷害 | - | 10 回合 | -3 | 友方 全體 (1體) | armor_max: 40.0<br>armor_min: 20.0<br>protection_max: 7.0<br>protection_min: 5.0<br>每級armor_max: +8.0<br>每級armor_min: +4.0 |
| `protection_wall` | **守護之牆** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | armor_offset: 0.3<br>每級armor_offset: +0.02 |
| `armor_quake` | **碎甲重震** | 主動 | 物理傷害 | 200% | 5 回合 | -3 | 敵方 遠程/全範圍 (1體) | armor_max: 300.0<br>armor_offset: 0.5<br>每級傷害係數/倍率: +0.1 |
| `bone_guardian` | **白骨守衛** | 主動 | 物理傷害 | - | 20 回合 | -3 | 友方 自身 (1體) | armor_offset: 0.4<br>持續回合數: 10.0<br>total_res: 40.0<br>每級armor_offset: +0.03<br>每級total_res: +3.0 |

#### 🔹 hero_warrior_7 - 戰士 (狂戰士) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `樹精/樹人` | 性別 `男` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `sword_warrior_7`, off_hand: `shield_warrior_7`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `withered_wood_strike` | **枯木猛擊** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 近戰目標 (1體) | immobilize_chance: 0.25<br>immobilize_max: 2.0<br>immobilize_min: 1.0<br>每級傷害係數/倍率: +0.02 |
| `provoked_fury` | **激怒狂暴** | 主動 | 物理傷害 | - | 7 回合 | -1 | 敵方 遠程/全範圍 (1體) | armor_max: 60.0<br>armor_min: 30.0<br>provocation_round: 3.0<br>weakness_level_chance: 0.25<br>虛弱層數上限: 5.0<br>虛弱基礎層數: 3.0<br>每級armor_max: +6.0<br>每級armor_min: +3.0 |
| `life_source` | **生命之源 (被動)** | 主動 | 物理傷害 | - | 15 回合 | 3 | 友方 自身 (1體) | hp_offset: 0.1<br>每級hp_offset: +0.01 |
| `woodland_aegis` | **林地守護** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 生命值: 20.0<br>物理抗性 (%): 10.0<br>每級生命值: +10.0<br>每級物理抗性 (%): +1.0 |
| `restoration_sprite` | **復甦妖精** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | hp_offset: 0.25<br>sprite_chance: 0.5<br>每級hp_offset: +0.025<br>每級sprite_chance: +0.03 |
| `earthquake_slam` | **地裂震擊** | 主動 | 物理傷害 | 300% | 10 回合 | -3 | 敵方 全體 (1體) | 眩暈觸發機率: 0.25<br>每級傷害係數/倍率: +0.2<br>每級眩暈觸發機率: +0.02 |
| `tree_sprite_rebirth` | **樹靈重生 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | attr_bouns: 0.25<br>rebirth_chance: 0.4<br>每級rebirth_chance: +0.06 |

#### 🔹 hero_warrior_hildrena - 戰士 (狂戰士) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `維京人` | 性別 `女` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `axe_warrior_hildrena`, off_hand: `shield_warrior_hildrena`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shieldbound_cleave` | **盾衛順劈** | 主動 | 物理傷害 | 120% | 5 回合 | -2 | 敵方 近戰目標 (1體) | buff_block_max: 5.0<br>buff_block_min: 3.0<br>每級傷害係數/倍率: +0.02 |
| `ironwall_provocation` | **鐵壁嘲諷** | 主動 | 物理傷害 | - | 5 回合 | -2 | 敵方 全體 (1體) | armor_offset: 0.05<br>buff_block_times: 3.0<br>provocation_max: 2.0<br>provocation_min: 1.0<br>每級armor_offset: +0.01 |
| `iron_resolve` | **鋼鐵堅毅 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | hp_offset: 0.3<br>每級hp_offset: +0.02 |
| `shield_heart` | **盾之心 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 治療係數/倍率: 0.03<br>每級治療係數/倍率: +0.002 |
| `shieldwall_instinct` | **盾牆本能 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | buff_block_count: 1.0<br>增益觸發機率: 0.45<br>protection_count: 3.0<br>每級增益觸發機率: +0.03 |
| `shieldwrath_breaker` | **盾怒破滅擊** | 主動 | 物理傷害 | 180% | 7 回合 | -2 | 敵方 近戰目標 (1體) | 流血觸發機率: 0.45<br>流血層數上限: 5.0<br>流血基礎層數: 3.0<br>damage_offset_shield: 1.0<br>眩暈觸發機率: 0.75<br>每級傷害係數/倍率: +0.06<br>每級damage_offset_shield: +0.05 |
| `warshield_stance` | **戰盾姿態** | 主動 | 物理傷害 | - | 10 回合 | -3 | 友方 自身 (1體) | buff_block_max: 7.0<br>buff_block_min: 5.0<br>額外傷害加成: 0.35<br>持續回合數: 5.0<br>每級額外傷害加成: +0.04 |

#### 🔹 hero_warrior_kraghul - 戰士 (狂戰士) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `獸人` | 性別 `男` | 稀有度星級 `6.0`
- **初始裝備**：main_hand: `axe_orc_kraghul`, off_hand: `shield_orc_kraghul`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `blood_oath_cleave` | **血誓順劈斬** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 近戰目標 (1體) | 流血觸發機率: 0.25<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>hp_rate: 0.015<br>每級傷害係數/倍率: +0.02 |
| `unrelenting_fury` | **不息怒火 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | critical_strike_max: 3.0<br>critical_strike_min: 1.0<br>sp_chance: 0.15<br>sp_count: 1.0<br>每級sp_chance: +0.01 |
| `commanding_roar` | **commanding_roar** | 主動 | 物理傷害 | - | 10 回合 | -3 | 友方 全體 (1體) | 獲得行動點機率: 0.15<br>獲得行動點數量: 1.0<br>battle_fury_max: 5.0<br>battle_fury_min: 3.0<br>每級獲得行動點機率: +0.03 |
| `executioner_edge` | **處刑者之刃 (被動)** | 主動 | 物理傷害 | 170% | 5 回合 | -3 | 敵方 全體 (1體) | 流血觸發機率: 0.25<br>流血層數上限: 5.0<br>流血基礎層數: 3.0<br>額外傷害加成: 1.0<br>hp_rate: 0.25<br>每級傷害係數/倍率: +0.1 |
| `savage_overwhelm` | **野蠻壓制** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.15<br>每級額外傷害加成: +0.02 |
| `bladestorm_quake` | **劍刃風暴震盪** | 主動 | 物理傷害 | 140% | 7 回合 | -3 | 敵方 全體 (1體) | 眩暈觸發機率: 0.45<br>每級傷害係數/倍率: +0.08 |
| `burning_rage` | **灼熱狂怒** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 冷卻回合數: 10.0<br>damage_bouns_1: 0.5<br>damage_bouns_2: 0.25<br>damage_round: 5.0<br>每級damage_bouns_1: +0.05<br>每級damage_bouns_2: +-0.01 |

### ⚔️ 【戰寵 (靈獸)】系列英雄 (6 位)

#### 🔹 pet_healing_flashling - 戰寵 (靈獸) (史詩 (紫))
- **基本資料**：種族 `魔藥侏儒` | 性別 `unknown` | 稀有度星級 `3.0`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `glimmer_heal` | **微光治癒** | 主動 | 物理傷害 | - | 3 回合 | -2 | 友方 遠程/全範圍 (1體) | 能量獲得機率: 0.25<br>energy_count: 1.0<br>最大生命值: 50.0<br>hp_min: 30.0<br>每級最大生命值: +5.0<br>每級hp_min: +3.0 |
| `gleaming_gift` | **閃耀贈禮** | 主動 | 物理傷害 | - | 5 回合 | -1 | 友方 遠程/全範圍 (1體) | 能量獲得機率: 0.15<br>energy_count: 1.0<br>extra_energy_count: 1.0<br>每級能量獲得機率: +0.01 |
| `instant_droplet` | **瞬發水滴** | 主動 | 物理傷害 | - | 5 回合 | -3 | 友方 遠程/全範圍 (1體) | 能量獲得機率: 0.25<br>energy_count: 1.0<br>最大生命值: 100.0<br>hp_min: 80.0<br>每級最大生命值: +5.0<br>每級hp_min: +4.0 |
| `breath_infusion` | **龍息灌注 (被動)** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 治療效果提升 (%): 20.0<br>每級治療效果提升 (%): +3.0 |

#### 🔹 pet_hound_boneclaw - 戰寵 (靈獸) (傳說 (橘))
- **基本資料**：種族 `巨狼族` | 性別 `unknown` | 稀有度星級 `4.0`
- **初始裝備**：destruction_stone: `destruction_stone_hound_boneclaw`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `cursed_fang` | **詛咒毒牙** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 近戰目標 (1體) | 虛弱觸發機率: 0.25<br>虛弱層數上限: 3.0<br>虛弱基礎層數: 1.0<br>每級傷害係數/倍率: +0.02 |
| `swift_bite` | **迅捷啃咬** | 主動 | 物理傷害 | 45% | 3 回合 | -2 | 敵方 近戰目標 (1體) | 流血觸發機率: 0.25<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>每級傷害係數/倍率: +0.01 |
| `instinct_ripper` | **本能撕裂** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 流血觸發機率: 0.15<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>每級流血觸發機率: +0.01 |
| `brutal_maw` | **狂暴巨口撕咬** | 主動 | 物理傷害 | 160% | 5 回合 | -2 | 敵方 近戰目標 (1體) | trauma_chance: 0.25<br>trauma_max: 3.0<br>trauma_min: 1.0<br>每級傷害係數/倍率: +0.08 |
| `wraithbone_shell` | **幽魂骨甲** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | bleed_immuned: 1.0<br>魔法抗性 (%): 10.0<br>物理抗性 (%): 10.0<br>每級魔法抗性 (%): +1.0<br>每級物理抗性 (%): +1.0 |

#### 🔹 pet_savage_grizzly - 戰寵 (靈獸) (神話 (紅))
- **基本資料**：種族 `熊族` | 性別 `unknown` | 稀有度星級 `5.0`
- **初始裝備**：destruction_stone: `destruction_stone_bear_crit`, life_stone: `life_stone_bear`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `primal_outburst` | **原始爆發** | 主動 | 物理傷害 | - | 7 回合 | -1 | 友方 遠程/全範圍 (1體) | battle_fury_max: 5.0<br>battle_fury_min: 3.0<br>增益觸發機率: 0.25<br>critical_strike_max: 5.0<br>critical_strike_min: 3.0 |
| `rage_claw` | **狂怒利爪** | 主動 | 物理傷害 | 120% | 3 回合 | -2 | 敵方 近戰目標 (1體) | critical_strike_max: 5.0<br>critical_strike_min: 3.0<br>每級傷害係數/倍率: +0.04 |
| `wild_will` | **荒野意志 (被動)** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 暴擊率 (%): 10.0<br>物理傷害加深 (%): 10.0<br>每級暴擊率 (%): +1.0<br>每級物理傷害加深 (%): +1.0 |
| `rampaging_claws` | **暴走狂爪** | 主動 | 物理傷害 | 100% | 5 回合 | -3 | 敵方 近戰目標 (1體) | 流血觸發機率: 0.25<br>流血層數上限: 3.0<br>流血基礎層數: 1.0<br>額外傷害加成: 1.0<br>每級傷害係數/倍率: +0.04 |
| `savage_overwhelm` | **野蠻壓制** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.15<br>每級額外傷害加成: +0.02 |
| `savage_charge` | **野蠻衝撞** | 主動 | 物理傷害 | 140% | 10 回合 | -3 | 敵方 全體 (1體) | 眩暈觸發機率: 0.25<br>每級傷害係數/倍率: +0.06 |

#### 🔹 pet_slateshard_bruiser - 戰寵 (靈獸) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `冰霜元素` | 性別 `unknown` | 稀有度星級 `6.0`
- **初始裝備**：destruction_stone: `destruction_stone_froststeel`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `froststeel_grasp` | **霜鋼抓握** | 主動 | 物理傷害 | 120% | 5 回合 | -1 | 敵方 近戰目標 (1體) | 虛弱觸發機率: 0.25<br>虛弱層數上限: 5.0<br>虛弱基礎層數: 1.0<br>每級傷害係數/倍率: +0.02 |
| `froststeel_charge` | **霜鋼衝擊** | 主動 | 物理傷害 | - | 5 回合 | -2 | 敵方 近戰目標 (1體) | 一段傷害倍率: 1.2<br>二段傷害倍率: 0.3<br>冰凍觸發機率: 0.15<br>眩暈觸發機率: 0.15<br>每級一段傷害倍率: +0.04<br>每級二段傷害倍率: +0.02 |
| `frozen_plating` | **極凍裝甲 (被動)** | 主動 | 物理傷害 | - | 10 回合 | -1 | 友方 遠程/全範圍 (1體) | armor_offset: 0.1<br>frost_barrier_count: 5.0<br>protection_count: 5.0<br>每級armor_offset: +0.015 |
| `shatterline_burst` | **碎裂線爆發** | 主動 | 物理傷害 | 85% | 5 回合 | -3 | 敵方 全體 (1體) | vulnerability_chance: 0.25<br>vulnerability_max: 5.0<br>vulnerability_min: 1.0<br>每級傷害係數/倍率: +0.05 |
| `iceline_afterblow` | **iceline_afterblow** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 霜痕觸發機率: 0.15<br>每級霜痕觸發機率: +0.01 |
| `froststeel_constitution` | **霜鋼體質 (被動)** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 額外傷害加成: 0.1<br>damage_bouns_1: 0.15<br>damage_bouns_2: 0.25<br>damage_bouns_3: 0.35<br>hp_offset_1: 0.75<br>hp_offset_2: 0.5<br>hp_offset_3: 0.25<br>每級damage_bouns_1: +0.01<br>每級damage_bouns_2: +0.02<br>每級damage_bouns_3: +0.03 |
| `frostquake_resonance` | **霜震共鳴** | 被動 | 冰霜傷害 | 50% | 無 CD | 0 | 敵方 單體 (1體) | extra_chance: 0.35<br>冰凍觸發機率: 0.05<br>每級extra_chance: +0.04 |

#### 🔹 pet_slime_flame - 戰寵 (靈獸) (稀有 (藍))
- **基本資料**：種族 `史萊姆` | 性別 `unknown` | 稀有度星級 `2.0`
- **初始裝備**：elemental_stone: `elemental_stone_slime`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `support_fire` | **火力支援 (被動)** | 主動 | 火焰傷害 | 120% | 5 回合 | -1 | 敵方 遠程/全範圍 (1體) | fire_chance: 0.25<br>fire_max: 3.0<br>fire_min: 1.0<br>每級傷害係數/倍率: +0.02 |
| `fireball` | **火球術** | 主動 | 火焰傷害 | 150% | 5 回合 | 0 | 敵方 遠程/全範圍 (1體) | fire_chance: 0.45<br>fire_round: 3.0<br>每級傷害係數/倍率: +0.1 |
| `self_destruction` | **自毀爆炸** | 主動 | 火焰傷害 | 160% | 5 回合 | -3 | 敵方 全體 (1體) | fire_chance: 0.85<br>fire_max: 5.0<br>fire_min: 3.0<br>每級傷害係數/倍率: +0.06 |

#### 🔹 pet_voidsilver_sentinel - 戰寵 (靈獸) (超越/不朽 VII階 (彩紅))
- **基本資料**：種族 `虛空後裔` | 性別 `unknown` | 稀有度星級 `6.0`
- **初始裝備**：fortitude_stone: `fortitude_stone_silver`
- **配備技能列表**：

| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shield_slam` | **盾牌猛擊** | 主動 | 物理傷害 | 100% | 5 回合 | -1 | 敵方 近戰目標 (1體) | 眩暈觸發機率: 0.45<br>每級傷害係數/倍率: +0.02 |
| `silver_barrier_slam` | **白銀重盾猛擊** | 主動 | 物理傷害 | - | 3 回合 | -2 | 敵方 近戰目標 (1體) | 一段傷害倍率: 1.0<br>二段傷害倍率: 0.5<br>protection_max: 5.0<br>protection_min: 3.0<br>每級一段傷害倍率: +0.04<br>每級二段傷害倍率: +0.05 |
| `mass_defense` | **群體防禦祈禱** | 主動 | 物理傷害 | - | 10 回合 | -3 | 友方 全體 (1體) | armor_max: 40.0<br>armor_min: 20.0<br>protection_max: 7.0<br>protection_min: 5.0<br>每級armor_max: +8.0<br>每級armor_min: +4.0 |
| `mass_provoked_fury` | **全體狂怒挑釁** | 主動 | 物理傷害 | - | 10 回合 | -3 | 敵方 全體 (1體) | armor_max: 100.0<br>armor_min: 50.0<br>provocation_round: 3.0<br>虛弱層數上限: 5.0<br>虛弱基礎層數: 3.0<br>每級armor_max: +20.0<br>每級armor_min: +15.0 |
| `silver_aegis` | **白銀庇護** | 被動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | damage_bouns_1: 0.15<br>damage_bouns_2: 0.05<br>每級damage_bouns_1: +0.01<br>每級damage_bouns_2: +0.005 |
| `voidwall_conversion` | **虛空之牆轉換 (被動)** | 主動 | 物理傷害 | - | 10 回合 | -2 | 友方 遠程/全範圍 (1體) | armor_offset: 0.4<br>每級armor_offset: +0.06 |
| `silver_barrier` | **白銀屏障** | 主動 | 輔助/被動 | - | 無 CD | 0 | 敵方 單體 (1體) | 暗影抗性 (%): 100.0<br>魔法抗性 (%): 50.0<br>物理抗性 (%): 50.0<br>每級暗影抗性 (%): +10.0<br>每級魔法抗性 (%): +5.0<br>每級物理抗性 (%): +5.0 |
