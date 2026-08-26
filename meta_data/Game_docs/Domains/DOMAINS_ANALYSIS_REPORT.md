# 🗺️ Blackfire Crusade 冒險領地 (Domains) 全景深度解析與隱藏英雄解鎖指南

> 本文件依據遊戲底層資源 `meta_data/raw_tres/meta_datas.tres` 完整解析 5 大冒險領地 (Domains)、解鎖任務鏈、BOSS 群、神級裝備設計圖與 5 位隱藏 VII 階神話英雄解鎖機制。

---

## 🌟 核心亮點：全遊戲 5 位「擊敗 BOSS 隱藏解鎖英雄」總表

在《Blackfire Crusade》中，最強的 **VII 階 (稀有度 6.0)** 英雄**無法在酒館普通抽卡池中直接抽到**。玩家必須在領地或領主討伐中擊敗特定 BOSS 達成解鎖條件，隨後才能在酒館兌換處 (`exchange_datas`) 正式獲得！

| 隱藏英雄名稱 | 英雄 ID | 職業 | 種族 | 所屬關卡 / 領地 | 解鎖對應 BOSS | 核心特色與技能組 |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **寒噬女巫 · 艾卡希雅** | `hero_mage_ecasia` | 法師 | 精靈 (女) | **Domain 2【冷誓要塞】** | `elf_mage_ecasia` (艾卡希雅) | 頂級冰霜控場，大範圍霜棘殞滅、冰痕之刺、霜紋庇護護盾 |
| **深淵暗影 · 維爾贊** | `hero_rogue_vilzaan` | 刺客 | 惡魔 | **Domain 3【深淵獸巢】** | `demon_vilzaan` (維爾贊) | 深淵異變爆發、深淵穿刺突進、暗影擁抱、誓約之刃 |
| **破浪狂弓 · 奧拉夫** | `hero_archer_olaf` | 遊俠 | 維京 (男) | **Domain 4【沉潮廢墟】** | `viking_olaf` (奧拉夫) | 導引雙重箭、定錨強射、沉沒之握、潮汐追襲 |
| **機甲技師 · 格利格** | `hero_knight_glig` | 騎士 | 哥布林 | **Domain 5【紊亂鐵工廠】** | `goblin_glig` (格利格) | 廢鐵連擊、蒸氣加壓挑釁、燃料重輾衝撞、動能回收 |
| **碎骨狂戰 · 克拉格胡爾** | `hero_warrior_kraghul` | 戰士 | 獸人 (男) | **首領討伐 (Lord Boss)** | `orc_kraghul` (克拉格胡爾) | 血誓順劈斬、野蠻壓制、劍刃風暴、不息怒火、處刑者之刃 |

---

## ⚔️ 五大冒險領地 (Domains) 逐區深度剖析

---

### 🏛️ Domain 1：黃金帝國 (`golden_empire`)
- **建議挑戰等級**：**Lv. 49 ~ Lv. 69**
- **入場憑證 (門票)**：古老金幣 (`ancient_coin` x1)
- **前置解鎖任務**：完成主線第 6 關【冰凍峽谷 (`frozen_gorge`)】後，在血之祭壇接取 `blood_altar_golden_empire` 任務。
- **專屬兌換商店 (`exchange_dic`)**：
  - 黃金帝國寶箱 (`chest_golden_empire`): 128 代幣
  - 黃金重盾設計圖 (`design_shield_gold`): 256 代幣
  - 黃金長矛設計圖 (`design_spear_gold`): 256 代幣
  - 鍍金封印卷軸 / 耀光作戰魔藥
- **區域四大 BOSS**：
  1. `elf_mythril_hag` (秘銀巫婆)：掉落黃金腰帶設計圖、暴擊抗性卷軸
  2. `human_golden_tulakh` (黃金屠拉克)：掉落黃金護手設計圖、幸運卷軸
  3. `undead_altalim` (阿爾塔林)：掉落黃金頭盔設計圖、傷害加成卷軸
  4. `voidborn_goldwall_guardian` (金牆守衛)：掉落黃金胸甲設計圖、格擋卷軸
- **📦 黃金帝國寶箱 (`chest_golden_empire`) 開箱機制與掉落物清單**：
  - **開箱機制**：屬於 `domain_chest` 類別，**每開啟 1 個寶箱保證連續觸發 10 次獨立隨機抽取 (`count: 10.0`)**。
  - **12 大專屬珍寶獎池 (`treasures`) 與掉落機率**：
    | 獎勵道具 ID | 道具名稱 / 類型 | 品階 | 單抽機率 | 📦 開 1 箱(10抽) 出貨率 | 作用與價值 |
    | :--- | :--- | :---: | :---: | :---: | :--- |
    | **`relic_gilded_heartcore`** | **鍍金心核遺物** | 🌟 5 階 (金) | ~6% | **$\approx 46\%$** | 頂級專屬聖物，大幅提升全隊攻防屬性 |
    | **`ring_radiance`** | **光輝之戒** | 🌟 5 階 (金) | ~6% | **$\approx 46\%$** | 5 階頂級飾品，提供高額生命與物理抗性 |
    | **`design_feet_gold`** | **黃金戰靴圖紙** | 🌟 5 階 (金) | ~6% | **$\approx 46\%$** | 解鎖鐵匠鋪 5 階黃金重甲戰靴合成配方 |
    | **`dragonblood_gem`** | **龍血寶石** | 🌟 5 階 (金) | ~5% | **$\approx 40\%$** | 頂級裝備附魔與祭壇進階極稀有材料 |
    | **`ingot_gold`** | **黃金錠** | 4 階 (紫) | ~10% | **$\approx 65\%$** | 鍛造 5~6 階金色裝備與飾品核心金屬 |
    | **`gold_fragments`** | **黃金碎片** | 3 階 (藍) | ~12% | **$\approx 72\%$** | 珠寶加工與工坊基礎材料 |
    | **`design_radiant_war_potion`** | **光輝作戰藥水圖紙** | 4 階 (紫) | ~8% | **$\approx 56\%$** | 解鎖鍊金工坊合成光輝作戰藥水配方 |
    | **`radiant_war_potion`** | **光輝作戰藥水** | 4 階 (紫) | ~8% | **$\approx 56\%$** | 短時間內大幅提升全隊攻擊與暴擊 |
    | **`gilded_seal_scroll`** | **鍍金封印卷軸** | 4 階 (紫) | ~10% | **$\approx 65\%$** | 技能解鎖與封印強化卷軸 |
    | **`scroll_hp_2`** | **生命強化卷軸 II** | 3 階 (藍) | ~10% | **$\approx 65\%$** | 永久提升角色最大生命值 |
    | **`scroll_dodge_1`** | **閃避強化卷軸 I** | 2 階 (綠) | ~10% | **$\approx 65\%$** | 提升英雄基礎閃避率 |
    | **`ancient_coin`** | **古代金幣** | 特殊代幣 | ~15% | **$\approx 80\%$** | 區域專屬代幣，可在兌換所換取指定圖紙 |

---

### ❄️ Domain 2：冷誓要塞 (`coldoath_citadel`)
- **建議挑戰等級**：**Lv. 69 ~ Lv. 89**
- **入場憑證 (門票)**：霜縛印記 (`frostbound_sigil` x1)
- **前置解鎖任務**：通關主線第 7 關【被遺忘的荒原 (`forgotten_wasteland`)】後，在城鎮血之祭司處接取 `blood_altar_coldoath_citadel` 任務。
- **專屬兌換商店 (`exchange_dic`)**：
  - 冷誓要塞寶箱 (`chest_coldoath_citadel`): 256 代幣
  - 霜誓聖油設計圖 (`design_chrism_frostoath`): 256 代幣
  - 霜誓項鍊設計圖 (`design_necklace_frostoath`): 512 代幣
  - 破雪魔藥 / 投擲寒霜戰錘
- **區域三大 BOSS**：
  1. 🌟 **`elf_mage_ecasia` (寒噬女巫 · 艾卡希雅)**：
     - **擊敗獎勵**：**解鎖 VII 階法師英雄【寒噬女巫 · 艾卡希雅】** (`hero_mage_ecasia`)！
     - **掉落裝備**：誓約頭部設計圖、霜息殘頁、誓約之錠、艾卡希雅法杖/法典
  2. `dragon_azulos` (霜龍阿祖洛斯)：掉落誓約護手設計圖、毀滅之石、冰霜龍心
  3. `golem_haldren` (冰霜魔像哈爾登)：掉落誓約腰帶、霜誓徽記、誓約之鎖鏈環

---

### 🐙 Domain 3：深淵獸巢 (`abyssbeast_lair`)
- **建議挑戰等級**：**Lv. 79 ~ Lv. 99**
- **入場憑證 (門票)**：巢穴地圖殘片 (`nest_fragment_map` x1)
- **前置解鎖任務**：通關主線第 8 關【熾熱火山 (`fiery_volcano`)】後接取 `blood_altar_abyssbeast_lair`。
- **專屬兌換商店 (`exchange_dic`)**：
  - 深淵獸巢寶箱 (`chest_abyssbeast_lair`): 256 代幣
  - 深淵元素聖油設計圖 (`design_chrism_abyss_elemental`): 256 代幣
  - 深淵獸之戒設計圖 (`design_ring_abyssbeast`): 512 代幣
  - 深淵魔藥 / 深淵巢主聖油
- **區域四大 BOSS**：
  1. 🌟 **`demon_vilzaan` (深淵惡魔 · 維爾贊)**：
     - **擊敗獎勵**：**解鎖 VII 階刺客英雄【深淵暗影 · 維爾贊】** (`hero_rogue_vilzaan`)！
     - **掉落裝備**：深淵獸巢手套設計圖、維爾贊雙匕
  2. `abysscrawler_gorvath` (淵行者戈爾瓦斯)：掉落戈爾瓦斯寶箱、深淵觸鬚標本
  3. `abysscrawler_irmaja` (淵行者伊爾瑪亞)：掉落畸變母巢之心、伊爾瑪亞腰帶
  4. `behemoth_kazlom` (巨獸卡茲洛姆)：掉落卡茲洛姆巨角之首、深淵生長甲殼

---

### 🌊 Domain 4：沉潮廢墟 (`sunkentide_ruins`)
- **建議挑戰等級**：**Lv. 89 ~ Lv. 109**
- **入場憑證 (門票)**：生鏽羅盤 (`rusted_compass` x1)
- **前置解鎖任務**：通關主線第 9 關【亡者領域 (`domain_dead`)】後接取 `blood_altar_sunkentide_ruins`。
- **專屬兌換商店 (`exchange_dic`)**：
  - 沉潮廢墟寶箱 (`chest_sunkentide_ruins`): 256 代幣
  - 相位螺旋腰帶設計圖 (`design_waist_phase_spiral`): 512 代幣
  - 窒息深淵之戒 (`ring_suffocating_deep`): 1024 代幣
  - 水魄守護魔藥 / 深潛者體液魔藥
- **區域三大 BOSS**：
  1. 🌟 **`viking_olaf` (維京掠奪者 · 奧拉夫)**：
     - **擊敗獎勵**：**解鎖 VII 階遊俠英雄【破浪狂弓 · 奧拉夫】** (`hero_archer_olaf`)！
     - **掉落裝備**：殞落遠征護手、奧拉夫戰弓、奧拉夫箭袋
  2. `abysseroded_leviathan` (深蝕利維坦)：掉落殞落遠征胸甲、生命之石、維度碎片、相位鱗片
  3. `gillborn_selkuun` (鰓生者塞爾昆)：掉落塞爾昆法典設計圖、塞爾昆法杖

---

### ⚙️ Domain 5：紊亂鐵工廠 (`disordered_ironworks`)
- **建議挑戰等級**：**Lv. 99 ~ Lv. 119**
- **入場憑證 (門票)**：穿孔磁卡 (`punched_magnetic_card` x1)
- **前置解鎖任務**：通關主線第 10 關【地獄之門 (`gate_hell`)】後接取 `blood_altar_disordered_ironworks`。
- **專屬兌換商店 (`exchange_dic`)**：
  - 紊亂鐵工廠寶箱 (`chest_disordered_ironworks`): 256 代幣
  - 混沌傳動耳環 (`earing_chaotic_drive`): 1024 代幣
  - 守衛外殼飾品 (`accessory_guard_casing`): 1024 代幣
  - 穿甲炸彈 / 緊急協議底劑
- **區域五大 BOSS**：
  1. 🌟 **`goblin_glig` (哥布林技師 · 格利格)**：
     - **擊敗獎勵**：**解鎖 VII 階騎士英雄【機甲技師 · 格利格】** (`hero_knight_glig`)！
     - **掉落裝備**：過載電容組、格利格長矛、格利格重盾、銲工之心項鍊
  2. `dragon_meneia` (巨龍梅內亞)：掉落梅內亞之首、超頻電池、梅內亞龍匕
  3. `mech_iron_jaw` (鐵顎機甲)：掉落鐵顎重盾設計圖、毀滅之石
  4. `mech_keyo` (機甲凱奧)：掉落凱奧法杖設計圖、絕對零度核心
  5. `mech_scabby` (機甲斯卡比)：掉落斯卡比機械召喚石、督軍生物脊椎
