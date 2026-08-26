"""
Godot Resource (.tres) Parser for MetaDatas.

Parses Godot 4 .tres text resources containing MetaDatas dictionaries
into structured Python dictionaries.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional


class TresParser:
    """Parser for Blackfire Crusade Godot .tres resource files."""

    def __init__(self, tres_path: Optional[str] = None):
        if tres_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.tres_path = os.path.join(base_dir, "meta_data", "raw_tres", "meta_datas.tres")
        else:
            self.tres_path = tres_path
        
        self.raw_data: Dict[str, Any] = {}
        self._parsed = False

    def parse(self) -> Dict[str, Any]:
        """Parse the .tres file and load the data dictionary."""
        if not os.path.exists(self.tres_path):
            raise FileNotFoundError(f"TRES file not found: {self.tres_path}")

        with open(self.tres_path, "r", encoding="utf-8") as f:
            text = f.read()

        match = re.search(r"data\s*=\s*\{", text)
        if not match:
            raise ValueError(f"Could not find 'data = {{' section in {self.tres_path}")

        start_pos = match.end() - 1

        # Use bracket matching to isolate the JSON data object
        stack = 0
        in_string = False
        escape = False
        end_pos = start_pos

        for i in range(start_pos, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if not in_string:
                if c == "{":
                    stack += 1
                elif c == "}":
                    stack -= 1
                    if stack == 0:
                        end_pos = i + 1
                        break

        if stack != 0:
            raise ValueError("Mismatched brackets while parsing TRES data dictionary.")

        json_str = text[start_pos:end_pos]
        self.raw_data = json.loads(json_str, strict=False)
        self._parsed = True
        return self.raw_data

    def get_characters(self) -> Dict[str, Any]:
        """Return all characters dictionary."""
        if not self._parsed:
            self.parse()
        return self.raw_data.get("characters", {})

    def get_heroes(self) -> Dict[str, Any]:
        """
        Filter and return hero characters.
        A character is a hero if its id starts with 'hero_' or it has rarity and no enemy_type.
        """
        characters = self.get_characters()
        heroes = {}
        for char_id, char_info in characters.items():
            if char_id.startswith("hero_") or ("rarity" in char_info and "enemy_type" not in char_info):
                heroes[char_id] = char_info
        return heroes

    def get_skills(self) -> Dict[str, Any]:
        """Return all skills dictionary."""
        if not self._parsed:
            self.parse()
        return self.raw_data.get("skills", {})

    def get_classes(self) -> Dict[str, Any]:
        """Return all classes dictionary."""
        if not self._parsed:
            self.parse()
        return self.raw_data.get("classes", {})

    def get_races(self) -> Dict[str, Any]:
        """Return all races dictionary."""
        if not self._parsed:
            self.parse()
        return self.raw_data.get("races", {})

    def get_rarity(self) -> Dict[str, Any]:
        """Return rarity dictionary."""
        if not self._parsed:
            self.parse()
        return self.raw_data.get("rarity", {})

    def get_buffs(self) -> Dict[str, Any]:
        """Return buffs dictionary."""
        if not self._parsed:
            self.parse()
        return self.raw_data.get("buffs", {})
