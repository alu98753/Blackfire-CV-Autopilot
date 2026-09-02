# 💎《黑火遠征》全素材與材料資料手冊 (0~6 星等級全收錄)
> **依據底層資料庫**：[meta_datas.tres](../../raw_tres/meta_datas.tres)  
> **涵蓋範圍**：遊戲中全部 **146 種工藝製作材料 (`crafting`)**、**21 種部位強化石 (`enhancement_stone`)**、**7 種強化水晶 (`enhancement_crystal`)**、**6 種精華素材 (`essence`)** 與 **16 大遠古首領核心/龍心**。
> **版本規範**：全材料依星級（Tier 0 ~ Tier 6）嚴格分級，收錄底層變數名稱 (`id`)、繁體中文官方名稱、分類標籤、加工精煉配方、主要怪物產出來源及代表性打造去向。

---

## 📊 一、全星級素材規格總覽表

| 星級階數 | 代表框色 / 數值 (`rarity`) | 基礎工藝材料種數 | 強化石 / 水晶 / 精華 | 代表性素材群 |
| :---: | :---: | :---: | :---: | :--- |
| **Tier 0** | ⚪ 白色 (`0.0` 或無) | **20 種** | 武器/防具/飾品強化石 x3 | 硬化岩石碎片、粗鐵錠、輕皮革、基礎骨粉、粗亞麻 |
| **Tier 1** | 🟢 綠色 (`1.0`) | **21 種** | 強化石 x3、1階水晶、1階精華 | 優質鋼錠、中皮革、強化骨粉、沙礦石、堅石果實 |
| **Tier 2** | 🔵 藍色 (`2.0`) | **25 種** | 強化石 x3、2階水晶、2階精華 | 精煉鋼錠、重皮革、高級骨粉、鐵礦石、惡魔之角 |
| **Tier 3** | 🟣 紫色 (`3.0`) | **25 種** | 強化石 x3、3階水晶、3階精華 | 惡魔金屬錠、冰霜鋼錠、巨獸皮革、史詩骨粉、龍骨 |
| **Tier 4** | 🟠 橘黃 (`4.0`) | **28 種** | 強化石 x3、4階水晶、4階精華 | 熔岩鋼錠、黃金鑄塊、獸人皮革、傳說骨粉、墮落之心 |
| **Tier 5** | 🔶 橙色 (`5.0`) | **23 種** | 強化石 x3、5階水晶、5階精華、3大皇家核心、4大龍心 | 龍鱗皮革、神秘骨粉、龍息核心、霜誓基石、地獄花 |
| **Tier 6** | 🔴 紅色 (`6.0`) | **4 種** | 強化石 x3、6~7階水晶、6階精華、9大罪核、6大破損聖物 | 絕對零度之心、殘破魂印聖物、魂鍛之錘、魂鍛火鉗 |
| **合計** | - | **146 種** | **62 種特殊升級與核心素材** | **全遊戲共計 208 種材料** |

---

## 🔨 二、全 0~6 星基礎與進階工藝材料總表 (`crafting`，共 146 種)

### 0. 【Tier 0】0 星 / 白色普通素材 (Common)

> 標籤：`rarity: 0.0` | 框色：**⚪ 白色 (0.0)** | 總計 **20** 種材料  
> 特點說明：基础粗料、生皮、原生原礦、基礎骨粉

| 序號 | 中文名稱 | 底層變數名稱 (`id`) | 分類 / 標籤 | 加工精煉配方 (`processing_items`) | 主要獲取來源 (怪物/地下城) | 代表打造用途 (`used_in`) |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **蝙蝠翅膀** | `bat_wing` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `earring_bat_cave`, 【輕皮革】 |
| 2 | **野獸獠牙** | `beast_fang` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【基礎骨粉】, `bow_beast_fang`, `necklace_beast_fang` |
| 3 | **野豬皮** | `boar_hide` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `chest_boar_hide`, 【輕皮革】 |
| 4 | **基礎骨粉** | `bone_powder_basic` | `processing_bone_powder` | 野獸獠牙 x1 | 任務 / 商店 / 特殊掉落 | `antidote_potion`, 【強化骨粉】, `clarity_potion` 等 (4項) |
| 5 | **裝備碎屑** | `equipment_scraps` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `throwing_darts` |
| 6 | **粗製布匹** | `fabric_rough` | `processing_fabric` | 粗亞麻 x2<br>蜘蛛絲 x2 | 任務 / 商店 / 特殊掉落 | 【優質布匹】, `waist_shadow_king` |
| 7 | **蛙皮** | `frog_skin` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【輕皮革】 |
| 8 | **硬殼碎片** | `hard_shell_fragment` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `chest_hard_shell`, `chest_slime_armored`, `feet_hard_shell` 等 (6項) |
| 9 | **硬化岩石碎片** | `hardened_rock_shard` | 原生採集/掉落 | - | `golem_stone`, `lizard_desert`, `lizard_rockspike` 等 (5處) | `dagger_heavy_iron`, `hammer_golem_wall_guardian`, `head_hardened_rock_shard` 等 (7項) |
| 10 | **粗鐵錠** | `ingot_rough` | `processing_ingot` | 硬化岩石碎片 x2 | 任務 / 商店 / 特殊掉落 | `hands_iron_tusk`, 【優質鋼錠】, `ring_bear_bone_fragment` 等 (4項) |
| 11 | **輕皮革** | `leather_light` | `processing_leather` | 蝙蝠翅膀 x4<br>野豬皮 x2<br>蛙皮 x2<br>沙蟲鱗片 x2<br>堅韌蜥蜴皮 x2<br>狼皮 x2 | 任務 / 商店 / 特殊掉落 | `book_resilient_vine`, `hands_light_leather`, 【中皮革】 等 (5項) |
| 12 | **魔物血液 (1級)** | `monster_blood_1` | `monster_blood` | - | `bear_forest`, `desert_raider`, `frogman_archer` 等 (29處) | `hp_potion_1` |
| 13 | **紫色孢子** | `purple_spores` | 原生採集/掉落 | - | `mushroom_magic` | `clarity_potion` |
| 14 | **粗亞麻** | `rough_linen` | 原生採集/掉落 | - | `breeze_sprite` | 【粗製布匹】, `feet_rough_linen`, `hands_rough_linen` |
| 15 | **沙蟲鱗片** | `sandworm_scale` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `feet_sandworm_scale`, 【輕皮革】 |
| 16 | **史萊姆黏液** | `slime_mucus` | 原生採集/掉落 | - | `slime_baby_2`, `slime_mage`, `slime_medium` | `head_slime_baby`, `ring_slime` |
| 17 | **蜘蛛絲** | `spider_thread` | 原生採集/掉落 | - | `spider_armored`, `spider_baby_mage`, `spider_baby` 等 (5處) | `chest_spider_thread`, 【粗製布匹】, `hands_spider_rock` 等 (5項) |
| 18 | **蜘蛛毒腺** | `spider_venom_gland` | 原生採集/掉落 | - | `spider_armored`, `spider_baby_mage`, `spider_baby` 等 (5處) | `antidote_potion` |
| 19 | **堅韌蜥蜴皮** | `tough_lizard_hide` | 原生採集/掉落 | - | `lizard_desert` | `hands_spider_rock`, `hands_tough_lizard_hide`, 【輕皮革】 |
| 20 | **狼皮** | `wolf_pelt` | 原生採集/掉落 | - | `wolf_shadowwood`, `wolf_thorn`, `wolf_wasteland` | `feet_wolf_pelt`, 【輕皮革】 |

---

### 1. 【Tier 1】1 星 / 綠色優秀素材 (Uncommon)

> 標籤：`rarity: 1.0` | 框色：**🟢 綠色 (1.0)** | 總計 **21** 種材料  
> 特點說明：強化骨粉、優質鋼錠、初級加工素材、毒素與纖維

| 序號 | 中文名稱 | 底層變數名稱 (`id`) | 分類 / 標籤 | 加工精煉配方 (`processing_items`) | 主要獲取來源 (怪物/地下城) | 代表打造用途 (`used_in`) |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **野豬獠牙** | `boar_tusk` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【強化骨粉】, `bow_beast_fang`, `hands_iron_tusk` 等 (4項) |
| 2 | **強化骨粉** | `bone_powder_enhanced` | `processing_bone_powder` | 野豬獠牙 x1<br>基礎骨粉 x2<br>巨人牙齒 x1<br>毒牙獵豹獠牙 x1 | 任務 / 商店 / 特殊掉落 | `armor_potion`, 【高級骨粉】, `hp_potion_2` 等 (4項) |
| 3 | **暗黑史萊姆黏液** | `dark_slime_mucus` | 原生採集/掉落 | - | `slime_dark_baby`, `slime_dark` | 【一階精華 (初級精華)】, `ring_darkfrog_relic`, `ring_slime_dark` |
| 4 | **優質布匹** | `fabric_quality` | `processing_fabric` | 粗製布匹 x4<br>霜蛛絲 x2<br>韌性藤蔓 x2<br>怨魂碎布 x2 | 任務 / 商店 / 特殊掉落 | `chest_arcane_robe`, 【精編布匹】, `head_shadowweave_hood` |
| 5 | **霜蛛絲** | `frost_spider_silk` | 原生採集/掉落 | - | `spider_frost_king`, `spider_snowstorm` | 【冰織布匹】, 【優質布匹】, `hands_frost_spider_silk` |
| 6 | **巨人牙齒** | `giant_teeth` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【強化骨粉】, `ring_bear_bone_fragment` |
| 7 | **微小黃金碎屑** | `gold_fragment_small` | 原生採集/掉落 | - | `golem_golden`, `voidborn_coin`, `voidborn_gilded_lion` 等 (10處) | 【黃金鑄塊】 |
| 8 | **黃金史萊姆黏液** | `golden_slime_mucus` | 原生採集/掉落 | - | `slime_gold` | 【一階精華 (初級精華)】, `ring_slime_golden` |
| 9 | **優質鋼錠** | `ingot_quality` | `processing_ingot` | 粗鐵錠 x4<br>沙礦石 x2<br>堅石果實 (石皮果) x2 | 任務 / 商店 / 特殊掉落 | `axe_rune_shard`, `chest_boneplate_helm`, 【精煉鋼錠】 等 (7項) |
| 10 | **中皮革** | `leather_medium` | `processing_leather` | 輕皮革 x4<br>花豹皮 x2<br>石化鱗片 x2 | 任務 / 商店 / 特殊掉落 | `bow_ingot_demonite`, `feet_medium_leather`, 【重皮革 (厚重皮革)】 等 (5項) |
| 11 | **花豹皮** | `leopard_hide` | 原生採集/掉落 | - | `panther_forest` | `feet_leopard_hide`, 【中皮革】, `quiver_leopard_hide` |
| 12 | **魔物血液 (2級)** | `monster_blood_2` | `monster_blood` | - | `human_chained_slave`, `skeleton_eclipse_executioner`, `skeleton_shadow_sentinel` 等 (9處) | `hp_potion_2` |
| 13 | **石化鱗片** | `petrified_scale` | 原生採集/掉落 | - | `lizard_petrified` | `dagger_petrified_scale`, `hands_petrified_scale`, 【中皮革】 等 (5項) |
| 14 | **韌性藤蔓** | `resilient_vine` | 原生採集/掉落 | - | `vine_horror_default` | `book_resilient_vine`, 【優質布匹】, `head_resilient_vine` |
| 15 | **沙礦石** | `sand_ore` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `bow_sand_ore`, 【優質鋼錠】, `scepter_sand_ore` 等 (4項) |
| 16 | **巨蠍甲殼** | `scorpion_carapace` | 原生採集/掉落 | - | `scorpion_giant` | `waist_scorpion_shell_girdle` |
| 17 | **堅石果實 (石皮果)** | `stoneskin_fruit` | 原生採集/掉落 | - | `golem_stone`, `golem_wall_guardian`, `phantom_rock` | `armor_potion`, `hammer_golem_wall_guardian`, 【優質鋼錠】 |
| 18 | **蟾蜍毒液** | `toad_venom` | 原生採集/掉落 | - | `toad_bloodsucker`, `toad_plague_king`, `toad_plague` | `chest_plaguehide`, 【一階精華 (初級精華)】, `plague_potion` 等 (4項) |
| 19 | **毒牙獵豹獠牙** | `venomfang_panther` | 原生採集/掉落 | - | `panther_venomous_black` | 【強化骨粉】, `necklace_venomfang_panther` |
| 20 | **怨魂碎布** | `wraith_cloth` | 原生採集/掉落 | - | `skeleton_bone_warden`, `skeleton_eclipse_executioner`, `skeleton_mage` 等 (7處) | `chest_malice_shroud`, 【優質布匹】, `feet_wraith_cloth` |
| 21 | **怨魂核心** | `wraith_core` | 原生採集/掉落 | - | `specter_ancient` | `book_wraith_core`, 【一階精華 (初級精華)】, `quiver_wraith_core` |

---

### 2. 【Tier 2】2 星 / 藍色稀有素材 (Rare)

> 標籤：`rarity: 2.0` | 框色：**🔵 藍色 (2.0)** | 總計 **25** 種材料  
> 特點說明：高級骨粉、精煉金屬錠、重皮革、礦石與巨獸部位

| 序號 | 中文名稱 | 底層變數名稱 (`id`) | 分類 / 標籤 | 加工精煉配方 (`processing_items`) | 主要獲取來源 (怪物/地下城) | 代表打造用途 (`used_in`) |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **巨熊碎骨** | `bear_bone_fragment` | 原生採集/掉落 | - | `bear_forest_giant`, `bear_forest` | 【高級骨粉】, `necklace_bone_fury`, `shield_bear_bone` |
| 2 | **巨獸之骨** | `behemoth_bone` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【高級骨粉】, `head_ancient_beast_warden` |
| 3 | **高級骨粉** | `bone_powder_advanced` | `processing_bone_powder` | 巨熊碎骨 x1<br>巨獸之骨 x1<br>強化骨粉 x2<br>詛咒骨片 x1<br>惡魔之角 x1<br>冥骨鋼 x1 | 任務 / 商店 / 特殊掉落 | `ap_potion`, `energy_potion`, `frog_eye_potion` 等 (5項) |
| 4 | **寒卵孵化液** | `chillspawn_hatch_fluid` | 原生採集/掉落 | - | `spider_frozen_egg` | 【二階精華 (優秀精華)】, `frostshield_potion` |
| 5 | **詛咒骨片** | `cursed_bone_fragment` | 原生採集/掉落 | - | `skeleton_bone_warden`, `skeleton_eclipse_executioner`, `skeleton_kaldor` 等 (7處) | 【高級骨粉】, `earring_netherworld`, `necklace_bone_fury` |
| 6 | **惡魔之角** | `demon_horn` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【高級骨粉】, `head_demon_vargon`, `quiver_frost_demon` |
| 7 | **能量果實** | `energy_fruit` | 原生採集/掉落 | - | `beetle_energy` | `energy_potion` |
| 8 | **邪靈碎屑** | `evil_soul_shards` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【二階精華 (優秀精華)】, `head_shadowweave_hood`, 【惡魔金屬錠】 |
| 9 | **精編布匹** | `fabric_finely_woven` | `processing_fabric` | 優質布匹 x4<br>沼澤織布 x2 | 任務 / 商店 / 特殊掉落 | `bow_ingot_demonite`, `chest_frostbinder`, `feet_frostbinder` 等 (6項) |
| 10 | **蛙眼晶石** | `frog_eye_crystal` | 原生採集/掉落 | - | `frogman_archer`, `frogman_bog_chieftain`, `frogman_hunter` 等 (5處) | `chest_arcane_robe`, 【二階精華 (優秀精華)】, `frog_eye_potion` 等 (4項) |
| 11 | **巨人毛皮** | `giant_hide` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【重皮革 (厚重皮革)】 |
| 12 | **冰晶碎片** | `ice_crystal_shard` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `chest_frozen_warden`, 【二階精華 (優秀精華)】, `feet_frozen_warden` 等 (11項) |
| 13 | **冰原毛皮** | `ice_fur` | 原生採集/掉落 | - | `bear_frost`, `bear_yolda`, `demon_snowmount` | `chest_frostbinder`, `feet_frostbinder`, 【重皮革 (厚重皮革)】 |
| 14 | **精煉鋼錠** | `ingot_refined` | `processing_ingot` | 優質鋼錠 x4<br>鐵礦石 x2<br>枷鎖碎片 x2 | `golem_roland` | `chest_expedition_knight`, `chest_frozen_warden`, `chest_leather_orc` 等 (10項) |
| 15 | **鐵礦石** | `iron_ore` | 原生採集/掉落 | - | `sludge_fiend_default` | `hands_chained_slave`, 【精煉鋼錠】, `quiver_wraith_core` |
| 16 | **重皮革 (厚重皮革)** | `leather_heavy` | `processing_leather` | 巨獸毛皮 x1<br>巨人毛皮 x2<br>冰原毛皮 x2<br>中皮革 x4<br>蛇皮 x2<br>厚熊皮 x2 | 任務 / 商店 / 特殊掉落 | `chest_ancient_beast_warden`, `feet_ancient_beast_warden`, `hands_ancient_beast_warden` 等 (10項) |
| 17 | **獸人碎皮** | `leather_orc_fragment` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【獸人皮革】 |
| 18 | **魔物血液 (3級)** | `monster_blood_3` | `monster_blood` | - | `bat_darkwing_king`, `boar_iron_tusk`, `frogman_bog_chieftain` 等 (17處) | `hp_potion_3` |
| 19 | **冥骨鋼** | `netherbone_teel` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【高級骨粉】, `chest_boneplate_helm`, `scepter_ingot_demonite` |
| 20 | **符文碎塊** | `rune_shard` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `axe_rune_shard`, `shield_rune_shard`, `waist_runic_girdle` |
| 21 | **枷鎖碎片** | `shackled_fragment` | 原生採集/掉落 | - | `human_chained_slave` | `hands_chained_slave`, 【精煉鋼錠】 |
| 22 | **蛇皮** | `snake_hide` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【重皮革 (厚重皮革)】 |
| 23 | **沼澤織布** | `swamp_cloth` | 原生採集/掉落 | - | `frogman_hunter`, `frogman_rogue`, `frogman_warrior` | `book_wraith_core`, `earring_netherworld`, 【精編布匹】 等 (5項) |
| 24 | **厚熊皮** | `thick_bear_hide` | 原生採集/掉落 | - | `bear_forest` | `chest_ancient_beast_warden`, `feet_ancient_beast_warden`, `hands_ancient_beast_warden` 等 (6項) |
| 25 | **活力果實** | `vitality_fruit` | 原生採集/掉落 | - | `tree_sprite_action` | `ap_potion` |

---

### 3. 【Tier 3】3 星 / 紫色史詩素材 (Epic)

> 標籤：`rarity: 3.0` | 框色：**🟣 紫色 (3.0)** | 總計 **25** 種材料  
> 特點說明：史詩骨粉、惡魔金屬錠、冰霜鋼錠、巨獸皮革、龍骨

| 序號 | 中文名稱 | 底層變數名稱 (`id`) | 分類 / 標籤 | 加工精煉配方 (`processing_items`) | 主要獲取來源 (怪物/地下城) | 代表打造用途 (`used_in`) |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **深淵黏液** | `abyssal_slime` | 原生採集/掉落 | - | `behemoth_kazlom`, `demon_vilzaan`, `fiendbat_fleshspore` 等 (5處) | `abyssal_potion`, `chrism_abyss_elemental`, 【三階精華 (稀有精華)】 等 (5項) |
| 2 | **巨獸毛皮** | `behemoth_hide` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【巨獸皮革】, 【重皮革 (厚重皮革)】 |
| 3 | **染血信箋** | `bloodstained_letter` | 原生採集/掉落 | - | `human_cutter` | `chrism_thousand_souls` |
| 4 | **史詩骨粉** | `bone_powder_epic` | `processing_bone_powder` | 巨龍之骨 (龍骨) x1<br>食屍鬼尖牙 x1<br>獸人獠牙 x1 | 任務 / 商店 / 特殊掉落 | 【傳說骨粉】, `hp_potion_4`, `hp_potion_abyssal` 等 (5項) |
| 5 | **殘破墓碑** | `broken_gravestone` | 原生採集/掉落 | - | `skeleton_daros`, `skeleton_gravebound_golem`, `skeleton_margus` | `accessory_soulseal_relic` |
| 6 | **深海氣泡** | `deepsea_bubble` | 原生採集/掉落 | - | `abysseroded_crag_lurker`, `abysseroded_depth_executioner`, `abysseroded_leviathan` 等 (12處) | `aqueous_aegis_potion`, `book_gillborn_selkuun`, `bow_abysseroded_moses` 等 (4項) |
| 7 | **巨龍之骨 (龍骨)** | `dragonbone` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【史詩骨粉】 |
| 8 | **冰織布匹** | `fabric_iceweave` | `processing_fabric` | 霜蛛絲 x8 | 任務 / 商店 / 特殊掉落 | `chest_frostbinder`, `feet_frostbinder`, `hands_frostbinder` 等 (4項) |
| 9 | **烈焰精華素材** | `flame_essence` | 原生採集/掉落 | - | `behemoth_blazefiend`, `behemoth_karrog`, `demon_firecore_imp` 等 (5處) | `bow_demon_lilith`, `chest_dragonscale`, 【三階精華 (稀有精華)】 等 (9項) |
| 10 | **冰霜礦石** | `frost_ore` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【冰霜鋼錠 (寒霜鑄塊)】 |
| 11 | **食屍鬼尖牙** | `ghoul_fang` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【史詩骨粉】, `necklace_ancient_beast_warden` |
| 12 | **黃金甲殼** | `golden_carapace` | 原生採集/掉落 | - | `beetle_golden`, `snake_cursed_golden` | 【黃金鑄塊】 |
| 13 | **地獄之鏈** | `hell_chain` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `head_demon_vargon`, 【地獄火鋼錠】, `shield_demon_molthar` |
| 14 | **惡魔金屬錠** | `ingot_demonite` | `processing_ingot` | 邪靈碎屑 x4 | 任務 / 商店 / 特殊掉落 | `bow_ingot_demonite`, `bow_undead_uzerg`, `earring_netherworld` 等 (8項) |
| 15 | **冰霜鋼錠 (寒霜鑄塊)** | `ingot_frezon` | `processing_ingot` | 冰霜礦石 x2<br>冰晶碎片 x4 | 任務 / 商店 / 特殊掉落 | `chest_expedition_knight`, `chest_frozen_warden`, `feet_frozen_warden` 等 (11項) |
| 16 | **巨獸皮革** | `leather_behemoth` | `processing_leather` | 巨獸毛皮 x2 | 任務 / 商店 / 特殊掉落 | `chest_ancient_beast_warden`, `feet_ancient_beast_warden`, `hands_ancient_beast_warden` 等 (5項) |
| 17 | **魔物血液 (4級)** | `monster_blood_4` | `monster_blood` | - | `golem_tolthek`, `wraith_issarion` | `hp_potion_4`, `staff_hellfire` |
| 18 | **深淵爬行者魔血** | `monster_blood_abysscrawler` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `earing_drowned_song`, `hp_potion_abyssal`, `scepter_abysscrawler_irmaja` |
| 19 | **獸人之血** | `monster_blood_orc` | `monster_blood` | - | 任務 / 商店 / 特殊掉落 | `rage_howl_potion` |
| 20 | **誓約鎖環** | `oathlock_chainlink` | 原生採集/掉落 | - | `demon_frostscar_statue`, `golem_Frostetched_vower`, `golem_coldplate_husk` 等 (6處) | 【誓約鋼錠】, `necklace_frostoath` |
| 21 | **獸人獠牙** | `orc_fang` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【史詩骨粉】, `chest_leather_orc`, `feet_leather_orc` 等 (7項) |
| 22 | **異界果實** | `otherworldly_fruit` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | - |
| 23 | **瘟疫之皮** | `plaguehide` | 原生採集/掉落 | - | `toad_plague_king` | `chest_plaguehide`, 【三階精華 (稀有精華)】 |
| 24 | **不朽之根** | `root_immortality` | 原生採集/掉落 | - | `treant_ancient`, `treant_guardian`, `treant_mage` | 【三階精華 (稀有精華)】, `resurrection_potion` |
| 25 | **磨損齒輪** | `worn_gear` | 原生採集/掉落 | - | `demon_sarlst`, `dragon_meneia`, `goblin_glig` 等 (14處) | `dagger_dragon_meneia`, `emergency_protocol_primer`, `shield_mech_iron_jaw` 等 (5項) |

---

### 4. 【Tier 4】4 星 / 橘黃傳說素材 (Legendary)

> 標籤：`rarity: 4.0` | 框色：**🟠 橘/黃色 (4.0)** | 總計 **28** 種材料  
> 特點說明：傳說骨粉、熔岩鋼錠、黃金鑄塊、獸人皮革、墮落之心

| 序號 | 中文名稱 | 底層變數名稱 (`id`) | 分類 / 標籤 | 加工精煉配方 (`processing_items`) | 主要獲取來源 (怪物/地下城) | 代表打造用途 (`used_in`) |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **深淵增生外殼** | `abyssal_growth_husk` | 原生採集/掉落 | - | `behemoth_kazlom` | `amulet_abyssbeast_lair`, `amulet_dam_8`, 【四階精華 (史詩精華)】 等 (7項) |
| 2 | **傳說骨粉** | `bone_powder_legendary` | `processing_bone_powder` | 史詩骨粉 x2<br>墮落之心 x1<br>巨狼卡爾瑟之齒 x1 | 任務 / 商店 / 特殊掉落 | `aqueous_aegis_potion`, 【神秘骨粉 (神話骨粉)】, `hp_potion_5` 等 (5項) |
| 3 | **龍鱗碎片** | `dragonscale_fragment` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `chest_dragonscale`, `feet_dragonscale`, `hands_dragonscale` 等 (7項) |
| 4 | **仇恨精華** | `essence_hatred` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `bow_undead_uzerg`, `chest_malice_shroud`, 【四階精華 (史詩精華)】 |
| 5 | **永凍玄武岩** | `everfrozen_basalt` | 原生採集/掉落 | - | `demon_frostscar_statue`, `golem_Frostetched_vower`, `golem_coldplate_husk` 等 (8處) | 【誓約鋼錠】 |
| 6 | **墮落之心** | `fallen_heart` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【傳說骨粉】, 【四階精華 (史詩精華)】, `head_demon_vargon` 等 (4項) |
| 7 | **烈焰紅寶石** | `flame_ruby` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | `chest_dragonscale`, 【四階精華 (史詩精華)】, `feet_dragonscale` 等 (6項) |
| 8 | **霜凍之羽** | `frostbitten_feather` | 原生採集/掉落 | - | `crow_frostclaw` | `quiver_frostfeather` |
| 9 | **霜息殘頁** | `frostbreath_page` | 原生採集/掉落 | - | `elf_mage_ecasia` | `chrism_frostoath`, 【四階精華 (史詩精華)】, `summonstone_frostdragon` |
| 10 | **鍍金血淚** | `gilded_blood_tear` | 原生採集/掉落 | - | `voidborn_gleaming_eye`, `voidborn_radiant_hexeye` | `radiant_war_potion` |
| 11 | **黃金碎塊** | `gold_fragments` | 原生採集/掉落 | - | `elf_mythril_hag`, `golem_golden`, `human_golden_tulakh` 等 (13處) | 【黃金鑄塊】 |
| 12 | **黃金鑄塊** | `ingot_gold` | `processing_ingot` | 微小黃金碎屑 x16<br>黃金碎塊 x2<br>黃金甲殼 x4 | `human_cutter` | `chest_dragonscale`, `chest_gold`, `dagger_wolf_karlther` 等 (15項) |
| 13 | **地獄火鋼錠** | `ingot_hellfire` | `processing_ingot` | 地獄之鏈 x4 | 任務 / 商店 / 特殊掉落 | `chest_demon_samael`, `shield_pale_amethyst`, `staff_hellfire` |
| 14 | **熔岩鋼錠 (熔火鑄塊)** | `ingot_molten` | `processing_ingot` | 熔岩礦石 x2 | 任務 / 商店 / 特殊掉落 | `bow_demon_lilith`, `chest_demon_samael`, `hands_moltenflare_girdle` 等 (5項) |
| 15 | **誓約鋼錠** | `ingot_oathbound` | `processing_ingot` | 永凍玄武岩 x2<br>誓約鎖環 x4 | `elf_mage_ecasia` | `bow_abysseroded_moses`, `hands_oathbound`, `head_oathbound` 等 (5項) |
| 16 | **熔岩礦石** | `lava_ore` | 原生採集/掉落 | - | `behemoth_karrog`, `demon_boneflame_crawler`, `demon_firecore_imp` 等 (8處) | 【熔岩鋼錠 (熔火鑄塊)】, `summonstone_hellhounds` |
| 17 | **獸人皮革** | `leather_orc` | `processing_leather` | 獸人碎皮 x8<br>圖騰毛皮吊墜 x2 | 任務 / 商店 / 特殊掉落 | `chest_leather_orc`, `feet_leather_orc`, `hands_ghoul_ehrlan` 等 (8項) |
| 18 | **微型電池** | `micro_battery` | 原生採集/掉落 | - | `demon_sarlst`, `dragon_meneia`, `goblin_glig` 等 (14處) | `amulet_hp_8`, `amulet_phy_8`, `dagger_dragon_meneia` 等 (9項) |
| 19 | **魔物血液 (5級)** | `monster_blood_5` | `monster_blood` | - | `voidborn_elres` | `hp_potion_5` |
| 20 | **契約魔血** | `monster_blood_pact` | `monster_blood` | - | `demon_azrim`, `demon_bloodpit_digger` | `ring_demon_azrim` |
| 21 | **相位鱗片** | `phasing_scales` | 原生採集/掉落 | - | `abysseroded_depth_executioner`, `abysseroded_leviathan`, `abysseroded_moses` 等 (7處) | `amulet_mag_8`, `bow_abysseroded_moses`, `feet_fallen_expedition` 等 (6項) |
| 22 | **破雪萬能溶劑** | `snowbane_alkahest` | 原生採集/掉落 | - | `fiendbat_frostdrain` | `chrism_frostoath`, `snowbane_potion` |
| 23 | **靈魂水晶** | `soul_crystal` | 原生採集/掉落 | - | `wraith_issarion` | `chest_voidwoven_cloth`, 【四階精華 (史詩精華)】, `head_soul_crystal` 等 (4項) |
| 24 | **窒息珊瑚** | `suffocating_coral` | 原生採集/掉落 | - | `abysseroded_crag_lurker`, `abysseroded_leviathan`, `abysseroded_moses` 等 (9處) | `aqueous_aegis_potion`, `book_gillborn_selkuun`, `earing_drowned_song` 等 (5項) |
| 25 | **圖騰毛皮吊墜** | `totem_pelt_pendant` | 原生採集/掉落 | - | `orc_gorsak`, `orc_gul`, `orc_harugor` | 【獸人皮革】 |
| 26 | **虛空之眼** | `void_eye` | 原生採集/掉落 | - | `sludge_fiend_olg`, `voidborn_ordis`, `voidborn_soulpeering_eye` | `book_voidborn_ordis` |
| 27 | **虛空編織布** | `voidwoven_cloth` | 原生採集/掉落 | - | `voidborn_elres` | `chest_voidwoven_cloth` |
| 28 | **巨狼卡爾瑟之齒** | `wolf_karlther_teeth` | 原生採集/掉落 | - | `wolf_karlther` | 【傳說骨粉】, `dagger_wolf_karlther` |

---

### 5. 【Tier 5】5 星 / 橙色神話素材 (Mythic)

> 標籤：`rarity: 5.0` | 框色：**🔶 橙色 (5.0)** | 總計 **23** 種材料  
> 特點說明：神秘骨粉、龍鱗皮革、霜誓建材、龍息核心、地獄花

| 序號 | 中文名稱 | 底層變數名稱 (`id`) | 分類 / 標籤 | 加工精煉配方 (`processing_items`) | 主要獲取來源 (怪物/地下城) | 代表打造用途 (`used_in`) |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **深淵觸鬚標本** | `abyssal_tendril_specimen` | 原生採集/掉落 | - | `abysscrawler_broodspore`, `abysscrawler_carapace`, `abysscrawler_gorvath` | `abyssal_potion`, `amulet_dam_8`, `chrism_abyss_elemental` 等 (6項) |
| 2 | **血鍛碎片** | `bloodforged_fragment` | 原生採集/掉落 | - | `demon_azrim` | `ring_demon_azrim` |
| 3 | **血脈鉤刃** | `bloodvein_hookblade` | 原生採集/掉落 | - | `abomination_saron` | `waist_abomination_saron` |
| 4 | **神秘骨粉 (神話骨粉)** | `bone_powder_mystic` | `processing_bone_powder` | 傳說骨粉 x2<br>地獄犬獠牙 x1<br>殉道者顱骨 x1<br>腐臭之心 x1 | 任務 / 商店 / 特殊掉落 | `abyssal_potion` |
| 5 | **詛咒鍛造碎片** | `cursedforged_shard` | 原生採集/掉落 | - | `demon_molthar`, `voidborn_ordis`, `voidborn_soulpeering_eye` | `shield_demon_molthar` |
| 6 | **維度碎片** | `dimensional_shard` | 原生採集/掉落 | - | `abysseroded_depth_executioner`, `abysseroded_leviathan`, `abysseroded_moses` 等 (5處) | `amulet_mag_8`, `book_gillborn_selkuun`, `bow_abysseroded_moses` 等 (8項) |
| 7 | **龍息核心** | `dragonbreath_core` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【五階精華 (傳說精華)】, `necklace_dragonslayer`, `waist_moltenflare_girdle` |
| 8 | **霜誓基石** | `frostoath_foundation` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | - |
| 9 | **霜誓墓痕** | `frostoath_gravemark` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | - |
| 10 | **霜誓墓碑** | `frostoath_headstone` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | - |
| 11 | **灰石甲殼** | `graystone_carapace` | 原生採集/掉落 | - | `behemoth_karrog` | `accessory_behemoth_karrog` |
| 12 | **地獄花** | `hellbloom` | 原生採集/掉落 | - | `demon_lilith`, 地下城:`abyss_hell` | `staff_demon_lilith` |
| 13 | **地獄犬獠牙** | `hellhound_tooth` | 原生採集/掉落 | - | 任務 / 商店 / 特殊掉落 | 【神秘骨粉 (神話骨粉)】, `summonstone_hellhounds` |
| 14 | **冰核碎片** | `ice_heart_fragment` | 原生採集/掉落 | - | `behemoth_frost` | `accessory_ice_heart`, 【五階精華 (傳說精華)】 |
| 15 | **地獄板甲碎片** | `infernal_plate_shard` | 原生採集/掉落 | - | `demon_infernal_enforcer`, `demon_kargros`, `demon_molthorn_servitor` 等 (6處) | `bow_demon_lilith`, `hands_moltenflare_girdle`, `head_demon_vargon` 等 (4項) |
| 16 | **銘刻石板** | `inscribed_stone_tablet` | 原生採集/掉落 | - | `skeleton_daros` | `accessory_soulseal_relic`, 【五階精華 (傳說精華)】 |
| 17 | **龍鱗皮革** | `leather_dragonscale` | `processing_leather` | 龍鱗碎片 x4 | 任務 / 商店 / 特殊掉落 | `book_voidborn_ordis`, `feet_leather_dragonscale` |
| 18 | **殉道者顱骨** | `martyr_cranium` | 原生採集/掉落 | - | `orc_gul` | 【神秘骨粉 (神話骨粉)】, 【五階精華 (傳說精華)】, `staff_orc_gul` |
| 19 | **過載電容組** | `overloaded_capacitor_bank` | 原生採集/掉落 | - | `demon_sarlst`, `goblin_glig`, `mech_grease_monkey` 等 (13處) | `amulet_hp_8`, `amulet_phy_8`, `dagger_dragon_meneia` 等 (7項) |
| 20 | **蒼白紫晶** | `pale_amethyst` | 原生採集/掉落 | - | `behemoth_crystalhorn`, `voidborn_azlorth` | 【五階精華 (傳說精華)】, `shield_pale_amethyst`, `spear_pale_amethyst` |
| 21 | **腐臭之心** | `putrid_heart` | 原生採集/掉落 | - | `sludge_fiend_olg`, `undead_mugrath`, `undead_uzerg` | `accessory_decay_charm`, 【神秘骨粉 (神話骨粉)】, `bow_undead_uzerg` 等 (6項) |
| 22 | **軍閥生體脊椎** | `warlord_bio_vertebra` | 原生採集/掉落 | - | `mech_scabby` | 【五階精華 (傳說精華)】, `summonstone_mech_scabby` |
| 23 | **畸變母巢核心 (畸變胎心)** | `warped_wombheart` | 原生採集/掉落 | - | `abysscrawler_irmaja` | `amulet_abyssbeast_lair`, `scepter_abysscrawler_irmaja` |

---

### 6. 【Tier 6】6 星 / 紅色遠古/創世素材 (Ancient / Genesis)

> 標籤：`rarity: 6.0` | 框色：**🔴 紅色 (6.0)** | 總計 **4** 種材料  
> 特點說明：絕對零度之心、魂鍛神器、殘破魂印聖物

| 序號 | 中文名稱 | 底層變數名稱 (`id`) | 分類 / 標籤 | 加工精煉配方 (`processing_items`) | 主要獲取來源 (怪物/地下城) | 代表打造用途 (`used_in`) |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **絕對零度之心** | `absolute_zero_heart` | 原生採集/掉落 | - | `mech_keyo` | `staff_mech_keyo` |
| 2 | **殘破魂印聖物** | `broken_soulseal_relic` | 原生採集/掉落 | - | `skeleton_margus` | `accessory_soulseal_relic`, 【六階精華 (遠古精華)】 |
| 3 | **魂鍛之錘** | `soulforge_hammer` | 原生採集/掉落 | - | `demon_talav` | 【六階精華 (遠古精華)】 |
| 4 | **魂鍛火鉗** | `soulforge_tongs` | 原生採集/掉落 | - | `demon_talav` | 【六階精華 (遠古精華)】 |

---

## 💎 三、裝備強化石、強化水晶與精華素材體系 (0~6 階)

在《黑火遠征》中，裝備強化升級與突破需要消耗專屬的強化石、水晶與精華素材。此類素材嚴格依階級對應裝備強化等級：

### 1. ⚔️ 部位強化石 (Enhancement Stones / Shards，共 21 種)

| 星級階數 | 武器強化石 (`weapon_shard`) | 防具強化石 (`armor_shard`) | 飾品強化石 (`charm_shard`) | 分解裝備來源 (100% 部位與階級對應) |
| :---: | :--- | :--- | :--- | :--- |
| **Tier 0** | **0 階粗製武器強化石** (`weapon_shard_0`) | **0 階粗製防具強化石** (`armor_shard_0`) | **0 階粗製飾品強化石** (`charm_shard_0`) | 分解 0 階 (星級 0.0) 對應部位裝備產出 (4 合 1 可精煉升級) |
| **Tier 1** | **1 階優秀武器強化石** (`weapon_shard_1`) | **1 階優秀防具強化石** (`armor_shard_1`) | **1 階優秀飾品強化石** (`charm_shard_1`) | 分解 1 階 (星級 1.0) 對應部位裝備產出 (4 合 1 可精煉升級) |
| **Tier 2** | **2 階稀有武器強化石** (`weapon_shard_2`) | **2 階稀有防具強化石** (`armor_shard_2`) | **2 階稀有飾品強化石** (`charm_shard_2`) | 分解 2 階 (星級 2.0) 對應部位裝備產出 (4 合 1 可精煉升級) |
| **Tier 3** | **3 階史詩武器強化石** (`weapon_shard_3`) | **3 階史詩防具強化石** (`armor_shard_3`) | **3 階史詩飾品強化石** (`charm_shard_3`) | 分解 3 階 (星級 3.0) 對應部位裝備產出 (4 合 1 可精煉升級) |
| **Tier 4** | **4 階傳奇武器強化石** (`weapon_shard_4`) | **4 階傳奇防具強化石** (`armor_shard_4`) | **4 階傳奇飾品強化石** (`charm_shard_4`) | 分解 4 階 (星級 4.0) 對應部位裝備產出 (4 合 1 可精煉升級) |
| **Tier 5** | **5 階神話武器強化石** (`weapon_shard_5`) | **5 階神話防具強化石** (`armor_shard_5`) | **5 階神話飾品強化石** (`charm_shard_5`) | 分解 5 階 (星級 5.0) 對應部位裝備產出 (4 合 1 可精煉升級) |
| **Tier 6** | **6 階遠古武器強化石** (`weapon_shard_6`) | **6 階遠古防具強化石** (`armor_shard_6`) | **6 階遠古飾品強化石** (`charm_shard_6`) | 分解 6 階 (星級 6.0) 對應部位裝備產出 (4 合 1 可精煉升級) |

### 2. 🔮 裝備強化水晶 (Enhancement Crystals，共 7 種)

| 水晶階級 | 變數名稱 (`id`) | 中文名稱 | 對應裝備強化區間 | 備註 |
| :---: | :--- | :--- | :---: | :--- |
| **1 階** | `enhancement_crystal_1` | **1 階裝備強化水晶** | 裝備 +1 ~ +3 強化 | 雜貨鋪購買、轉盤抽獎、寶箱或高級地下城獎勵 |
| **2 階** | `enhancement_crystal_2` | **2 階裝備強化水晶** | 裝備 +2 ~ +4 強化 | 雜貨鋪購買、轉盤抽獎、寶箱或高級地下城獎勵 |
| **3 階** | `enhancement_crystal_3` | **3 階裝備強化水晶** | 裝備 +3 ~ +5 強化 | 雜貨鋪購買、轉盤抽獎、寶箱或高級地下城獎勵 |
| **4 階** | `enhancement_crystal_4` | **4 階裝備強化水晶** | 裝備 +4 ~ +6 強化 | 雜貨鋪購買、轉盤抽獎、寶箱或高級地下城獎勵 |
| **5 階** | `enhancement_crystal_5` | **5 階裝備強化水晶** | 裝備 +5 ~ +7 強化 | 雜貨鋪購買、轉盤抽獎、寶箱或高級地下城獎勵 |
| **6 階** | `enhancement_crystal_6` | **6 階裝備強化水晶** | 裝備 +6 ~ +8 強化 | 雜貨鋪購買、轉盤抽獎、寶箱或高級地下城獎勵 |
| **7 階** | `enhancement_crystal_7` | **7 階裝備強化水晶** | 裝備 +7 ~ +9 強化 | 雜貨鋪購買、轉盤抽獎、寶箱或高級地下城獎勵 |

### 3. 🧪 六大階級精華素材 (Essences，共 6 種)

| 精華階級 | 變數名稱 (`id`) | 中文名稱 | 品質星級 | 主要用途與打造領域 |
| :---: | :--- | :--- | :---: | :--- |
| **1 階** | `essence_1` | **一階精華 (初級精華)** | Tier 1 (1.0) | 全 1 階裝備、武器、副手及藥劑之核心精華黏合劑 |
| **2 階** | `essence_2` | **二階精華 (優秀精華)** | Tier 2 (2.0) | 全 2 階裝備、武器、副手及藥劑之核心精華黏合劑 |
| **3 階** | `essence_3` | **三階精華 (稀有精華)** | Tier 3 (3.0) | 全 3 階裝備、武器、副手及藥劑之核心精華黏合劑 |
| **4 階** | `essence_4` | **四階精華 (史詩精華)** | Tier 4 (4.0) | 全 4 階裝備、武器、副手及藥劑之核心精華黏合劑 |
| **5 階** | `essence_5` | **五階精華 (傳說精華)** | Tier 5 (5.0) | 全 5 階裝備、武器、副手及藥劑之核心精華黏合劑 |
| **6 階** | `essence_6` | **六階精華 (遠古精華)** | Tier 6 (6.0) | 全 6 階裝備、武器、副手及藥劑之核心精華黏合劑 |

---

## 👑 四、首領核心、巨龍之心與遠古神話素材 (5~6 星)

### 1. 🏰 3 大皇家核心 (`royal_core`，Tier 5 神話橙)

| 變數名稱 (`id`) | 中文名稱 | 品質星級 | 主要掉落首領 | 核心用途 |
| :--- | :--- | :---: | :--- | :--- |
| `royal_core_slime` | **史萊姆皇家核心** | 5.0 (橙) | 皇家史萊姆國王 / 巨型史萊姆首領 | 打造頂級生命/防禦神話飾品 |
| `royal_core_spider` | **蜘蛛皇家核心** | 5.0 (橙) | 蜘蛛母皇 (育母蜘蛛首領) | 打造頂級神話毒素/敏捷飾品與長弓 |
| `royal_core_treant` | **樹人皇家核心** | 5.0 (橙) | 遠古守護樹人首領 (烏爾德) | 打造頂級神話生命恢復裝備 |

### 2. 🐉 4 大屬性巨龍之心 (`dragon_heart`，Tier 5 神話橙)

| 變數名稱 (`id`) | 中文名稱 | 屬性標籤 | 主要掉落巨龍 | 背包直接分解收益 |
| :--- | :--- | :---: | :--- | :--- |
| `dragon_heart_darkness` | **暗影巨龍之心** | 暗影 (`darkness`) | 冥淵暗龍首領 | 🎒 可直接分解：保底產出 10 顆強化石 (含 5 顆 4~5 階) |
| `dragon_heart_flame` | **烈焰巨龍之心** | 火焰 (`fire`) | 熾炎火龍首領 | 🎒 可直接分解：保底產出 10 顆強化石 (含 5 顆 4~5 階) |
| `dragon_heart_frost` | **冰霜巨龍之心** | 冰霜 (`ice`) | 極凍霜龍首領 | 🎒 可直接分解：保底產出 10 顆強化石 (含 5 顆 4~5 階) |
| `dragon_heart_venom` | **劇毒巨龍之心** | 毒素 (`poison`) | 沼澤毒龍首領 | 🎒 可直接分解：保底產出 10 顆強化石 (含 5 顆 4~5 階) |

### 3. ☠️ 9 大罪業王核 (`sin_core`，Tier 6 遠古紅)

| 變數名稱 (`id`) | 中文名稱 | 品質星級 | 對應大罪 / 領域首領 | 核心特性與分解價值 |
| :--- | :--- | :---: | :--- | :--- |
| `sin_core_abysslord` | **深淵領主之罪核** | 6.0 (紅) | 深淵魔境 / 深淵之王 | 打造頂級遠古創世神裝；分解獲 10 顆高階強化石 |
| `sin_core_chaosking` | **混沌之王之罪核** | 6.0 (紅) | 混沌邊界 / 混沌之主 | 打造頂級遠古創世神裝；分解獲 10 顆高階強化石 |
| `sin_core_doomqueen` | **毀滅女王之罪核** | 6.0 (紅) | 終焉之座 / 毀滅女王 | 打造頂級遠古創世神裝；分解獲 10 顆高階強化石 |
| `sin_core_everhunger` | **永恆飢渴之罪核** | 6.0 (紅) | 暴食之淵 / 吞噬魔神 | 打造頂級遠古創世神裝；分解獲 10 顆高階強化石 |
| `sin_core_firecoreking` | **熾炎火核王之罪核** | 6.0 (紅) | 熔岩地心 / 火核之王 | 打造頂級遠古創世神裝；分解獲 10 顆高階強化石 |
| `sin_core_frostgiant` | **霜巨人王之罪核** | 6.0 (紅) | 極寒永凍峰 / 冰霜之王 | 打造頂級遠古創世神裝；分解獲 10 顆高階強化石 |
| `sin_core_seaemperor` | **深海帝皇之罪核** | 6.0 (紅) | 沉沒神殿 / 深海帝皇 | 打造頂級遠古創世神裝；分解獲 10 顆高階強化石 |
| `sin_core_voidwalker` | **虛空行者之罪核** | 6.0 (紅) | 無盡虛空 / 虛空漫遊者 | 打造頂級遠古創世神裝；分解獲 10 顆高階強化石 |
| `sin_core_wastelord` | **荒原霸主之罪核** | 6.0 (紅) | 遺忘荒原 / 荒原霸王 | 打造頂級遠古創世神裝；分解獲 10 顆高階強化石 |

### 4. 🧩 6 大破損聖物部件與特殊遠古素材

| 變數名稱 (`id`) | 中文名稱 | 品質星級 | 來源與作用說明 |
| :--- | :--- | :---: | :--- |
| `broken_accessory_init_module_left` | **殘破飾品初始左模組** | 6.0 (紅) | 地下城終極試煉掉落，重組遠古首飾必備模組 |
| `broken_accessory_init_module_right` | **殘破飾品初始右模組** | 6.0 (紅) | 地下城終極試煉掉落，重組遠古首飾必備模組 |
| `broken_axe_darok` | **達羅克的殘破戰斧** | 6.0 (紅) | 狂戰士達羅克專屬傳承神器復原素材 |
| `broken_relic_salvation_lantern` | **殘破救贖之燈聖物** | 6.0 (紅) | 大主教救贖聖燈修復核心素材 |
| `broken_spear_depth_executioner` | **深淵處刑者的殘破之槍** | 6.0 (紅) | 深淵處刑者神話長槍修復素材 |
| `broken_sword_demon_azrim` | **惡魔阿茲里姆的殘破魔劍** | 6.0 (紅) | 惡魔魔王阿茲里姆滅世魔刃修復素材 |
| `frostoath_emblem` | **霜誓徽記** | 6.0 (紅) | 霜誓大教堂終極信物，直接分解獲大量高階強化石 |
| `dragonblood_gem` | **龍血寶石** | 6.0 (紅) | 巨龍先祖真血結晶，遠古裝備極限打孔與鑲嵌 |
| `warlord_last_word` | **軍閥遺言** | 6.0 (紅) | 鋼鐵軍閥之最後信物，分解保底獲高階強化石 |

---

## 🔄 五、四大核心加工鏈合成機制總覽

遊戲中的鐵匠鋪加工系統（`blacksmith.processing_dic`）具備極具特色的**層級遞歸加工機制**，玩家可將低階素材一路向上提煉：

```mermaid
graph LR
    subgraph ⛏️ 鑄塊鏈 (Ingot)
        I0["粗鐵錠 (ingot_rough)<br>硬化岩石 x2"] --> I1["優質鋼錠 (ingot_quality)<br>粗鐵錠x4 + 沙礦石x2 + 堅石果實x2"]
        I1 --> I2["精煉鋼錠 (ingot_refined)<br>優質鋼錠x4 + 鐵礦石x2 + 枷鎖碎片x2"]
        I2 --> I_SP["特殊高級金屬錠<br>冰霜/惡魔/熔岩/誓約/黃金"]
    end
    subgraph 🦌 皮革鏈 (Leather)
        L0["輕皮革 (leather_light)<br>生皮 x2 或 蝙蝠翅膀 x4"] --> L1["中皮革 (leather_medium)<br>輕皮革x4 + 花豹皮x2 + 石化鱗片x2"]
        L1 --> L2["重皮革 (leather_heavy)<br>中皮革x4 + 巨獸/巨人/熊皮x2"]
        L2 --> L_SP["特殊高級皮革<br>獸人皮革 / 龍鱗皮革"]
    end
    subgraph 🧵 布匹鏈 (Fabric)
        F0["粗製布匹 (fabric_rough)<br>粗亞麻x2 + 蜘蛛絲x2"] --> F1["優質布匹 (fabric_quality)<br>粗製布匹x4 + 霜蛛絲/藤蔓/怨魂布x2"]
        F1 --> F2["精編布匹 (fabric_finely_woven)<br>優質布匹x4 + 沼澤織布x2"]
        F2 --> F3["冰織布匹 (fabric_iceweave)<br>霜蛛絲x8"]
    end
    subgraph ☠️ 骨粉鏈 (Bone Powder)
        B0["基礎骨粉 (basic)<br>野獸獠牙x1"] --> B1["強化骨粉 (enhanced)<br>基礎x2 + 獠牙/巨人牙x1"]
        B1 --> B2["高級骨粉 (advanced)<br>強化x2 + 熊骨/巨獸骨/惡魔角x1"]
        B2 --> B3["史詩骨粉 (epic)<br>龍骨 + 食屍鬼牙 + 獸人牙"]
        B3 --> B4["傳說骨粉 (legendary)<br>史詩x2 + 墮落之心 + 狼王齒"]
        B4 --> B5["神秘骨粉 (mystic)<br>傳說x2 + 地獄犬齒 + 殉道顱骨 + 腐臭心"]
    end
```

---

## 📑 相關文件索引

- 原始數據來源：[meta_datas.tres](../../raw_tres/meta_datas.tres)
- 掉落率總綱手冊：[Drop_rate.md](Drop_rate.md)
- 鑄塊專題手冊：[ingot/ALL.md](ingot/ALL.md)
- 重皮革專題手冊：[leather/leather_heavy.md](leather/leather_heavy.md)
- 武器強化石獲取指南：[weapon_upgrade_shards_guide.md](../../../docs/guides/weapon_upgrade_shards_guide.md)
- 全裝備強化定價指南：[GEAR_ENHANCEMENT_PRICE_GUIDE.md](../Gear/Enhancement/GEAR_ENHANCEMENT_PRICE_GUIDE.md)
