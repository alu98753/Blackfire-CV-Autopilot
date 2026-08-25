"""
Hero and Skill Metadata Analyzer for Blackfire Crusade.

Parses .tres raw metadata and produces structured JSON datasets
and a comprehensive Markdown analytics report with English-to-Chinese translations.
"""

import json
import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from typing import Any, Dict, List, Optional
from meta_data.tres_parser import TresParser


class HeroAnalyzer:
    """Analyzes heroes, skills, and attributes from parsed Game MetaDatas."""

    def __init__(self, tres_path: Optional[str] = None):
        self.parser = TresParser(tres_path)
        self.data: Dict[str, Any] = {}
        self.heroes_raw: Dict[str, Any] = {}
        self.skills_raw: Dict[str, Any] = {}
        self.classes_raw: Dict[str, Any] = {}
        self.races_raw: Dict[str, Any] = {}
        
        self.dict_dir = os.path.join(os.path.dirname(__file__), "dicts")
        self.output_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(self.output_dir, exist_ok=True)

        self.class_i18n = self._load_dict("class_i18n.json")
        self.rarity_i18n = self._load_dict("rarity_i18n.json")
        self.race_i18n = self._load_dict("race_i18n.json")
        self.damage_type_i18n = self._load_dict("damage_type_i18n.json")
        self.target_i18n = self._load_dict("target_i18n.json")
        self.attr_i18n = self._load_dict("attr_i18n.json")
        self.skill_i18n = self._load_dict("skill_i18n.json")
        self.hero_i18n = self._load_dict("hero_i18n.json")

    def _load_dict(self, filename: str) -> Dict[str, Any]:
        filepath = os.path.join(self.dict_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def load_data(self):
        """Load and cache raw metadata from TRES."""
        self.data = self.parser.parse()
        self.heroes_raw = self.parser.get_heroes()
        self.skills_raw = self.parser.get_skills()
        self.classes_raw = self.parser.get_classes()
        self.races_raw = self.parser.get_races()

    def translate_attr_dict(self, attr_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert an attribute dictionary into a readable formatted dictionary with Chinese labels."""
        translated = {}
        for k, v in attr_dict.items():
            name_zh = self.attr_i18n.get(k, k)
            translated[k] = {
                "name_zh": name_zh,
                "value": v,
                "display": f"{name_zh}: {v}"
            }
        return translated

    def get_skill_detail(self, skill_id: str) -> Dict[str, Any]:
        """Extract and translate a single skill by its ID."""
        sdata = self.skills_raw.get(skill_id, {})
        if not sdata:
            return {
                "skill_id": skill_id,
                "skill_name_zh": self.skill_i18n.get(skill_id, skill_id),
                "error": "Skill not found in database"
            }

        skill_type = sdata.get("skill_type", "active")
        skill_type_zh = "被動" if skill_type == "passive" else "主動"
        damage_type = sdata.get("damage_type", "physical" if skill_type == "active" else "none")
        damage_type_zh = self.damage_type_i18n.get(damage_type, damage_type)

        target_data = sdata.get("target_data", {})
        party = target_data.get("party", "enemy")
        party_zh = self.target_i18n.get("party", {}).get(party, party)
        target = target_data.get("target", "single")
        target_zh = self.target_i18n.get("target", {}).get(target, target)
        target_count = target_data.get("count", 1.0)

        raw_attr = sdata.get("attr", {})
        damage_offset = raw_attr.get("damage_offset", 0.0)
        cool_round = sdata.get("cool_round", 0.0)
        sp = sdata.get("sp", 0.0)

        raw_attr_per_level = sdata.get("attr_per_level", {})

        return {
            "skill_id": skill_id,
            "skill_name_zh": self.skill_i18n.get(skill_id, skill_id),
            "skill_type": skill_type,
            "skill_type_zh": skill_type_zh,
            "damage_type": damage_type,
            "damage_type_zh": damage_type_zh,
            "damage_offset": damage_offset,
            "cool_round": cool_round,
            "sp": sp,
            "target": target,
            "target_zh": target_zh,
            "target_count": target_count,
            "party": party,
            "party_zh": party_zh,
            "attr": raw_attr,
            "attr_zh": self.translate_attr_dict(raw_attr),
            "attr_per_level": raw_attr_per_level,
            "attr_per_level_zh": self.translate_attr_dict(raw_attr_per_level),
            "raw_data": sdata
        }

    def analyze_heroes(self) -> List[Dict[str, Any]]:
        """Parse all heroes and produce structured hero records."""
        if not self.heroes_raw:
            self.load_data()

        analyzed_heroes = []

        for hero_id, hinfo in sorted(self.heroes_raw.items()):
            hero_class = hinfo.get("class", "unknown")
            class_zh = self.class_i18n.get(hero_class, hero_class)
            
            rarity_val = hinfo.get("rarity", 0.0)
            rarity_zh = self.rarity_i18n.get(str(rarity_val), f"稀有度 {rarity_val}")

            race = hinfo.get("race", "unknown")
            race_zh = self.race_i18n.get(race, race)

            gender = hinfo.get("gender", "unknown")
            gender_zh = "男" if gender == "male" else ("女" if gender == "female" else gender)

            class_info = self.classes_raw.get(hero_class, {})
            class_base_attr = class_info.get("attr", {})
            class_upgrade_attr = class_info.get("upgrade_attr", {})

            skill_ids = hinfo.get("skills", [])
            skills_detail = [self.get_skill_detail(sid) for sid in skill_ids]

            custom_name = self.hero_i18n.get(hero_id)
            name_zh = custom_name if custom_name else f"{class_zh} · {rarity_zh} ({hero_id})"

            hero_record = {
                "hero_id": hero_id,
                "name_zh": name_zh,
                "class": hero_class,
                "class_zh": class_zh,
                "rarity": rarity_val,
                "rarity_zh": rarity_zh,
                "race": race,
                "race_zh": race_zh,
                "gender": gender,
                "gender_zh": gender_zh,
                "equipments": hinfo.get("equipments", {}),
                "class_base_attr": class_base_attr,
                "class_base_attr_zh": self.translate_attr_dict(class_base_attr),
                "class_upgrade_attr": class_upgrade_attr,
                "class_upgrade_attr_zh": self.translate_attr_dict(class_upgrade_attr),
                "skill_ids": skill_ids,
                "skills": skills_detail,
                "raw_hero_data": hinfo
            }
            analyzed_heroes.append(hero_record)

        return analyzed_heroes

    def generate_all_outputs(self) -> Dict[str, str]:
        """Generate all 4 output datasets and markdown report."""
        if not self.heroes_raw:
            self.load_data()

        heroes_analyzed = self.analyze_heroes()

        # Output 1: 1_heroes_list.json
        heroes_list = []
        for h in heroes_analyzed:
            heroes_list.append({
                "hero_id": h["hero_id"],
                "class": h["class"],
                "class_zh": h["class_zh"],
                "rarity": h["rarity"],
                "rarity_zh": h["rarity_zh"],
                "race": h["race"],
                "race_zh": h["race_zh"],
                "gender": h["gender"],
                "gender_zh": h["gender_zh"],
                "equipments": h["equipments"],
                "skill_ids": h["skill_ids"],
                "skill_names_zh": [s["skill_name_zh"] for s in h["skills"]]
            })
        path_out1 = os.path.join(self.output_dir, "1_heroes_list.json")
        with open(path_out1, "w", encoding="utf-8") as f:
            json.dump(heroes_list, f, ensure_ascii=False, indent=2)

        # Output 2: 2_hero_skills.json
        hero_skills_map = {}
        for h in heroes_analyzed:
            hero_skills_map[h["hero_id"]] = {
                "hero_id": h["hero_id"],
                "class_zh": h["class_zh"],
                "rarity_zh": h["rarity_zh"],
                "skills": h["skills"]
            }
        path_out2 = os.path.join(self.output_dir, "2_hero_skills.json")
        with open(path_out2, "w", encoding="utf-8") as f:
            json.dump(hero_skills_map, f, ensure_ascii=False, indent=2)

        # Output 3: 3_raw_skills.json (All 700+ skills in database)
        all_skills_detailed = {}
        for sid in sorted(self.skills_raw.keys()):
            all_skills_detailed[sid] = self.get_skill_detail(sid)
        path_out3 = os.path.join(self.output_dir, "3_raw_skills.json")
        with open(path_out3, "w", encoding="utf-8") as f:
            json.dump(all_skills_detailed, f, ensure_ascii=False, indent=2)

        # Output 4: 4_hero_skill_analytics.json (Comprehensive master JSON)
        path_out4_json = os.path.join(self.output_dir, "4_hero_skill_analytics.json")
        with open(path_out4_json, "w", encoding="utf-8") as f:
            json.dump(heroes_analyzed, f, ensure_ascii=False, indent=2)

        # Output 5: HERO_ANALYSIS_REPORT.md (Markdown Comprehensive Report)
        report_md = self._build_markdown_report(heroes_analyzed, all_skills_detailed)
        path_report = os.path.join(self.output_dir, "HERO_ANALYSIS_REPORT.md")
        with open(path_report, "w", encoding="utf-8") as f:
            f.write(report_md)

        return {
            "heroes_list": path_out1,
            "hero_skills": path_out2,
            "raw_skills": path_out3,
            "analytics_json": path_out4_json,
            "report_markdown": path_report
        }

    def _build_markdown_report(self, heroes: List[Dict[str, Any]], all_skills: Dict[str, Any]) -> str:
        """Construct a formatted Markdown analysis report."""
        lines = [
            "# ⚔️ Blackfire Crusade 全英雄與全技能繁體中文分析圖鑑",
            "",
            "> 本文件由 `meta_data/hero_analyzer.py` 依據遊戲原始數據 `meta_datas.tres` 自動解析並翻譯生成。",
            "",
            "## 📊 數據統計概覽",
            f"- **收錄英雄總數**：{len(heroes)} 位",
            f"- **職業類別總數**：{len(self.classes_raw)} 種",
            f"- **全遊戲技能總數**：{len(all_skills)} 個",
            "",
            "---",
            "",
            "## 🛡️ 職業基礎屬性與每級成長表",
            "",
            "| 職業 (Class) | 基礎專精屬性 | 每級升級屬性成長 (Upgrade Attr) | 裝備偏好 |",
            "| :--- | :--- | :--- | :--- |"
        ]

        for cname, cinfo in sorted(self.classes_raw.items()):
            czh = self.class_i18n.get(cname, cname)
            base_attr = ", ".join([f"{self.attr_i18n.get(k, k)}: {v}" for k, v in cinfo.get("attr", {}).items()])
            up_attr = ", ".join([f"{self.attr_i18n.get(k, k)}: +{v}" for k, v in cinfo.get("upgrade_attr", {}).items()])
            eq = cinfo.get("equipments", {})
            eq_str = ", ".join([f"{k}: {v}" for k, v in eq.items()])
            lines.append(f"| **{czh}** (`{cname}`) | {base_attr} | {up_attr} | {eq_str} |")

        lines.extend([
            "",
            "---",
            "",
            "## 🧙‍♂️ 全部英雄與技能全景清單",
            ""
        ])

        # Group heroes by Class
        by_class = {}
        for h in heroes:
            c = h["class"]
            if c not in by_class:
                by_class[c] = []
            by_class[c].append(h)

        for cname, hlist in by_class.items():
            czh = self.class_i18n.get(cname, cname)
            lines.extend([
                f"### ⚔️ 【{czh}】系列英雄 ({len(hlist)} 位)",
                ""
            ])

            for h in hlist:
                lines.extend([
                    f"#### 🔹 {h['hero_id']} - {h['class_zh']} ({h['rarity_zh']})",
                    f"- **基本資料**：種族 `{h['race_zh']}` | 性別 `{h['gender_zh']}` | 稀有度星級 `{h['rarity']}`",
                ])
                if h["equipments"]:
                    eq_items = [f"{slot}: `{item}`" for slot, item in h["equipments"].items()]
                    lines.append(f"- **初始裝備**：{', '.join(eq_items)}")

                lines.append("- **配備技能列表**：")
                lines.append("")
                lines.append("| 技能 ID | 中文名稱 | 類型 | 傷害屬性 | 傷害倍率 | CD | SP | 目標範圍 | 成長與附加效果 |")
                lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

                for s in h["skills"]:
                    if "error" in s:
                        lines.append(f"| `{s['skill_id']}` | {s.get('skill_name_zh', '未知')} | - | - | - | - | - | - | 技能資料缺失 |")
                        continue

                    eff_list = []
                    for ak, av in s["attr"].items():
                        if ak != "damage_offset":
                            azh = self.attr_i18n.get(ak, ak)
                            eff_list.append(f"{azh}: {av}")
                    for ak, av in s["attr_per_level"].items():
                        azh = self.attr_i18n.get(ak, ak)
                        eff_list.append(f"每級{azh}: +{av}")
                    eff_str = "<br>".join(eff_list) if eff_list else "無額外效果"

                    dam_str = f"{s['damage_offset']*100:.0f}%" if s['damage_offset'] > 0 else "-"
                    cd_str = f"{int(s['cool_round'])} 回合" if s['cool_round'] > 0 else "無 CD"
                    sp_str = f"{int(s['sp'])}" if s['sp'] != 0 else "0"
                    target_str = f"{s['party_zh']} {s['target_zh']} ({int(s['target_count'])}體)"

                    lines.append(f"| `{s['skill_id']}` | **{s['skill_name_zh']}** | {s['skill_type_zh']} | {s['damage_type_zh']} | {dam_str} | {cd_str} | {sp_str} | {target_str} | {eff_str} |")

                lines.append("")

        return "\n".join(lines)


if __name__ == "__main__":
    analyzer = HeroAnalyzer()
    analyzer.load_data()
    outputs = analyzer.generate_all_outputs()
    print("[SUCCESS] All outputs generated successfully:")
    for k, v in outputs.items():
        print(f"  - {k}: {v}")
