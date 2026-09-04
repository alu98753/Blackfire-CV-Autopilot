import os
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from vision.matcher import TemplateMatcher
from utils.detector_registry import DetectorGroup, DetectorRegistry
from utils.scene_snapshot import DetectionProfileId


class SceneType(Enum):
    TOWN = auto()                 # 城鎮主畫面
    LOBBY_STAGE = auto()          # 活動大廳 - 普通關卡頁籤開啟
    LOBBY_DUNGEON = auto()        # 活動大廳 - 地下城頁籤開啟
    DOMAIN_SELECT = auto()        # 活動大廳 - 領地頁籤開啟
    LORD_SELECT = auto()          # 活動大廳 - 領主頁籤開啟
    DEMON_LORD_SELECT = auto()    # 活動大廳 - 魔王頁籤開啟
    LOBBY_OTHER = auto()          # 活動大廳 - 其他頁籤
    IN_DUNGEON = auto()           # 地下城內部戰鬥/探索中
    DUNGEON_PREPARE = auto()      # 地下城備戰畫面 (戰鬥開始按鈕)
    POPUP_TASK_COMPLETE = auto() # 任務完成彈窗
    WINDOW_DIAMOND = auto()       # 鑽石領取視窗已開啟
    WINDOW_BREAD = auto()         # 體力領取視窗已開啟
    POPUP_UNEXPECTED = auto()     # 意外視窗/彈窗已開啟
    DOMAIN_EXPLORE = auto()       # 領地探索主畫面 (例如黃金古國)
    UNKNOWN = auto()              # 未知/切換中



@dataclass
class SceneInfo:
    scene_type: SceneType
    is_town: bool = False
    is_lobby: bool = False
    is_in_dungeon: bool = False
    is_dungeon_prepare: bool = False
    active_tabs: List[str] = field(default_factory=list)
    matched_elements: Dict[str, Tuple[Tuple[int, int], float]] = field(default_factory=dict)


class SceneDetector:
    def __init__(self, matcher: Optional[TemplateMatcher] = None):
        self.matcher = matcher or TemplateMatcher()
        self.registry = DetectorRegistry()
        self._active_profile = DetectionProfileId.UNKNOWN
        self._runtime_templates = {}
        self._frame_match_cache = {}

    def _safe_match(self, screen_img, template_name: str, threshold: float = 0.8) -> Tuple[Optional[Tuple[int, int]], float]:
        """
        安全包裝 TemplateMatcher.match()，相容包含 MagicMock 在內的各類回傳結構。
        """
        if not self.registry.allows_template(
            self._active_profile, template_name, self._runtime_templates
        ):
            return None, 0.0
        cache_key = (template_name, float(threshold))
        if cache_key in self._frame_match_cache:
            return self._frame_match_cache[cache_key]
        res = self.matcher.match(screen_img, template_name, threshold=threshold)
        if isinstance(res, (tuple, list)) and len(res) >= 2:
            match = (res[0], float(res[1]) if res[1] is not None else 0.0)
        else:
            match = (None, 0.0)
        self._frame_match_cache[cache_key] = match
        return match

    def detect(
        self,
        screen_img,
        machine_state=None,
        machine=None,
        profile=DetectionProfileId.UNKNOWN,
    ) -> SceneInfo:
        """
        偵測傳入畫面 screen_img 之完整場景資訊與 UI 頁籤狀態。
        嚴格遵循 階段0 ➔ 階段1 ➔ 階段2 ➔ 階段3 ➔ 階段4 之優先順序。
        """
        self._active_profile = profile
        self._frame_match_cache = {}
        self._runtime_templates = self._build_runtime_templates(machine)
        scene_info = SceneInfo(scene_type=SceneType.UNKNOWN)
        if profile == DetectionProfileId.TOWN:
            scene_info.is_town = True
        elif profile in {
            DetectionProfileId.LOBBY,
            DetectionProfileId.STAGE_SELECT,
            DetectionProfileId.DUNGEON_SELECT,
            DetectionProfileId.DOMAIN_SELECT,
            DetectionProfileId.LORD_SELECT,
            DetectionProfileId.DEMON_LORD_SELECT,
        }:
            scene_info.is_lobby = True

        # 0. 全域最高優先防護與視窗狀態
        if os.path.exists(os.path.join("templates", "task_complete.png")):
            pos_task, conf_task = self._safe_match(screen_img, "task_complete.png", threshold=0.75)
            if pos_task:
                scene_info.scene_type = SceneType.POPUP_TASK_COMPLETE
                scene_info.matched_elements["task_complete.png"] = (pos_task, conf_task)
                return scene_info

        if machine:
            if getattr(machine, "diamond_window_opened", False):
                scene_info.scene_type = SceneType.WINDOW_DIAMOND
                return scene_info
            if getattr(machine, "bread_window_opened", False):
                scene_info.scene_type = SceneType.WINDOW_BREAD
                return scene_info

        config_type = "stage"
        if machine and getattr(machine, "config", None):
            config_type = machine.config.get("type", "stage")

        # 1. 地下城內部檢測 (leave.png / dungeon_bless.png 等)
        if config_type in ["dungeon", "mix"]:
            dungeon_inner_btns = [
                "dungeons/leave.png",
                "dungeons/dungeon_bless.png",
                "dungeons/Treasure.png",
                "dungeons/gungeon_godown.png"
            ]
            for check_btn in dungeon_inner_btns:
                if os.path.exists(os.path.join("templates", check_btn)):
                    pos, conf = self._safe_match(screen_img, check_btn, threshold=0.8)
                    if pos:
                        scene_info.scene_type = SceneType.IN_DUNGEON
                        scene_info.is_in_dungeon = True
                        scene_info.matched_elements[check_btn] = (pos, conf)
                        return scene_info

            # 2. 地下城備戰檢測 (dungeon_fight.png)
            if os.path.exists(os.path.join("templates", "dungeons/dungeon_fight.png")):
                pos_fight, conf_fight = self._safe_match(screen_img, "dungeons/dungeon_fight.png", threshold=0.8)
                if pos_fight:
                    scene_info.scene_type = SceneType.DUNGEON_PREPARE
                    scene_info.is_dungeon_prepare = True
                    scene_info.matched_elements["dungeons/dungeon_fight.png"] = (pos_fight, conf_fight)
                    return scene_info

        # 3. 城鎮與大廳指標檢測
        pos_door, conf_door = self._safe_match(screen_img, "common/door.png", threshold=0.8)
        pos_diamond, conf_diamond = self._safe_match(screen_img, "diamond.png", threshold=0.8)
        if pos_door:
            scene_info.matched_elements["common/door.png"] = (pos_door, conf_door)
        if pos_diamond:
            scene_info.matched_elements["diamond.png"] = (pos_diamond, conf_diamond)

        if pos_door or pos_diamond:
            scene_info.is_town = True

        pos_goback, conf_goback = self._safe_match(screen_img, "goback_town.png", threshold=0.8)
        pos_bread_btn, conf_bread_btn = self._safe_match(screen_img, "common/bread.png", threshold=0.8)
        if pos_goback:
            scene_info.matched_elements["goback_town.png"] = (pos_goback, conf_goback)
        if pos_bread_btn:
            scene_info.matched_elements["common/bread.png"] = (pos_bread_btn, conf_bread_btn)

        if pos_goback or pos_bread_btn:
            scene_info.is_lobby = True

        if scene_info.is_lobby and os.path.exists(os.path.join("templates", "common/quit.png")):
            pos_quit, conf_quit = self._safe_match(
                screen_img,
                "common/quit.png",
                threshold=0.75,
            )
            if pos_quit:
                scene_info.matched_elements["common/quit.png"] = (pos_quit, conf_quit)

        if scene_info.is_town:
            scene_info.scene_type = SceneType.TOWN
            return scene_info

        lobby_start_btn = "stages/start.png"
        if machine and getattr(machine, "config", None):
            lobby_start_btn = machine.config.get("lobby_start_btn", lobby_start_btn)
        if os.path.exists(os.path.join("templates", lobby_start_btn)):
            pos_start, conf_start = self._safe_match(screen_img, lobby_start_btn, threshold=0.8)
            if pos_start:
                scene_info.scene_type = SceneType.LOBBY_OTHER
                scene_info.is_lobby = True
                scene_info.matched_elements[lobby_start_btn] = (pos_start, conf_start)
                return scene_info

        # 4. 頁籤互斥與高信心度內容備援
        # 頁籤是主要證據；卡片只在高信心度時協助定位。Lobby 各分類
        # 共用卡片版型與水平位置，因此一般卡片或 locked_entry 不能單獨
        # 證明目前所在的分類頁。
        stage_select_open = False
        dungeon_select_open = False
        domain_select_open = False
        lord_select_open = False
        demon_lord_select_open = False
        stage_tab_confidence = 0.0
        dungeon_tab_confidence = 0.0

        res_tabs = None
        if self.registry.allows_group(profile, DetectorGroup.TABS):
            res_tabs = self.matcher.match_mutually_exclusive_tabs(
                screen_img, "common/select_stage_after.png", "dungeons/dungeon_after.png", margin=0.02, threshold=0.70
            )
        if isinstance(res_tabs, (tuple, list)) and len(res_tabs) == 4 and type(res_tabs).__name__ != "MagicMock":
            stage_select_open = bool(res_tabs[0])
            dungeon_select_open = bool(res_tabs[1])
            stage_tab_confidence = self._as_confidence(res_tabs[2])
            dungeon_tab_confidence = self._as_confidence(res_tabs[3])
        else:
            conf_stage_after, conf_dungeon_after = 0.0, 0.0
            if os.path.exists(os.path.join("templates", "common/select_stage_after.png")):
                _, conf_stage_after = self._safe_match(screen_img, "common/select_stage_after.png", threshold=0.70)

            if os.path.exists(os.path.join("templates", "dungeons/dungeon_after.png")):
                _, conf_dungeon_after = self._safe_match(screen_img, "dungeons/dungeon_after.png", threshold=0.70)

            stage_select_open = (conf_stage_after >= 0.70 and conf_stage_after > conf_dungeon_after + 0.02)
            dungeon_select_open = (conf_dungeon_after >= 0.70 and conf_dungeon_after > conf_stage_after + 0.02)
            stage_tab_confidence = conf_stage_after
            dungeon_tab_confidence = conf_dungeon_after

        stage_dungeon_conflict = (
            stage_tab_confidence >= 0.70
            and dungeon_tab_confidence >= 0.70
            and not (stage_select_open ^ dungeon_select_open)
        )

        if config_type == "domain":
            domain_tab = self._runtime_config_value(
                machine,
                "domain_tab_btn",
                "domains/Domains_entry.png",
            )
            domain_pos, domain_conf = self._safe_match(
                screen_img,
                domain_tab,
                threshold=0.65,
            )
            if domain_pos and self._has_red_selection_ring(screen_img, domain_pos):
                domain_select_open = True
                scene_info.matched_elements[domain_tab] = (domain_pos, domain_conf)

        if config_type == "lord_boss":
            lord_select_open = self._selected_from_active_inactive_pair(
                screen_img,
                self._runtime_config_value(machine, "entry_after_btn", "load/Lord_entry_after.png"),
                self._runtime_config_value(machine, "entry_btn", "load/Lord_entry.png"),
            )

        if config_type == "demon_lords":
            demon_lord_select_open = self._selected_from_active_inactive_pair(
                screen_img,
                self._runtime_config_value(
                    machine,
                    "entry_after_btn",
                    "demon_lords/demon_lords_entry_after.png",
                ),
                self._runtime_config_value(
                    machine,
                    "entry_btn",
                    "demon_lords/demon_lords_entry.png",
                ),
            )

        # 模板備援掃描
        allow_card_fallback = (
            config_type in {"stage", "dungeon", "mix", "daily"}
            and not stage_dungeon_conflict
        )
        if allow_card_fallback and not stage_select_open and not dungeon_select_open and machine and getattr(machine, "config", None):
            stage_templates = machine.config.get("stage_templates", [])
            for st_temp in stage_templates:
                if os.path.exists(os.path.join("templates", st_temp)):
                    pos, conf = self._safe_match(screen_img, st_temp, threshold=0.85)
                    if pos:
                        stage_select_open = True
                        scene_info.matched_elements[st_temp] = (pos, conf)
                        break

        if allow_card_fallback and not stage_select_open and not dungeon_select_open and machine and getattr(machine, "config", None):
            dungeon_templates = machine.config.get("dungeon_entries", [])
            for dg_temp in dungeon_templates:
                if os.path.exists(os.path.join("templates", dg_temp)):
                    pos, conf = self._safe_match(screen_img, dg_temp, threshold=0.85)
                    if pos:
                        dungeon_select_open = True
                        scene_info.matched_elements[dg_temp] = (pos, conf)
                        break

        # 最終場景分類
        selected_tabs = [
            (dungeon_select_open, SceneType.LOBBY_DUNGEON, "dungeon"),
            (stage_select_open, SceneType.LOBBY_STAGE, "stage"),
            (domain_select_open, SceneType.DOMAIN_SELECT, "domain"),
            (lord_select_open, SceneType.LORD_SELECT, "lord"),
            (demon_lord_select_open, SceneType.DEMON_LORD_SELECT, "demon_lord"),
        ]
        active = [candidate for candidate in selected_tabs if candidate[0]]
        if len(active) == 1:
            _, scene_type, tab_name = active[0]
            scene_info.scene_type = scene_type
            scene_info.active_tabs.append(tab_name)
        elif len(active) > 1:
            logging.warning(
                "Conflicting active lobby tabs detected; refusing to guess: %s",
                [candidate[2] for candidate in active],
            )
            scene_info.scene_type = SceneType.LOBBY_OTHER
        elif scene_info.is_lobby:
            scene_info.scene_type = SceneType.LOBBY_OTHER

        return scene_info

    @staticmethod
    def _as_confidence(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _runtime_config_value(machine, key, default):
        config = getattr(machine, "config", None) if machine is not None else None
        return (config or {}).get(key, default)

    def _selected_from_active_inactive_pair(self, screen_img, active, inactive):
        if not self.registry.allows_group(self._active_profile, DetectorGroup.TABS):
            return False
        result = self.matcher.match_mutually_exclusive_tabs(
            screen_img,
            active,
            inactive,
            margin=0.02,
            threshold=0.70,
        )
        return bool(
            isinstance(result, (tuple, list))
            and len(result) == 4
            and type(result).__name__ != "MagicMock"
            and result[0]
            and not result[1]
        )

    @staticmethod
    def _has_red_selection_ring(screen_img, center):
        """Detect the selected red outline around the Domains tab.

        Domains currently has no dedicated ``*_after.png`` asset. The inactive
        icon provides the location anchor; the red ring is the independent
        selected-state postcondition.
        """
        if type(screen_img).__name__ != "ndarray" or center is None:
            return False
        try:
            import cv2
            import numpy as np

            height, width = screen_img.shape[:2]
            scale = max(0.5, width / 1920.0)
            radius_x = max(35, int(85 * scale))
            radius_y = max(40, int(95 * scale))
            center_x, center_y = int(center[0]), int(center[1] - 8 * scale)
            x1, x2 = max(0, center_x - radius_x), min(width, center_x + radius_x)
            y1, y2 = max(0, center_y - radius_y), min(height, center_y + radius_y)
            roi = screen_img[y1:y2, x1:x2]
            if roi.size == 0:
                return False
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            low_red = cv2.inRange(hsv, np.array([0, 135, 90]), np.array([12, 255, 255]))
            high_red = cv2.inRange(hsv, np.array([168, 135, 90]), np.array([179, 255, 255]))
            red_pixels = int(cv2.countNonZero(cv2.bitwise_or(low_red, high_red)))
            return red_pixels >= max(24, int(120 * scale * scale))
        except (AttributeError, TypeError, ValueError):
            return False

    @staticmethod
    def _build_runtime_templates(machine):
        if machine is None or not getattr(machine, "config", None):
            return {}
        config = machine.config
        templates = {
            config.get("lobby_start_btn", "stages/start.png"): DetectorGroup.LOBBY
        }
        for template in config.get("stage_templates", []):
            templates[template] = DetectorGroup.TABS
        for template in config.get("dungeon_entries", []):
            templates[template] = DetectorGroup.TABS
        for key, default in {
            "domain_tab_btn": "domains/Domains_entry.png",
            "entry_btn": "",
            "entry_after_btn": "",
        }.items():
            template = config.get(key, default)
            if template:
                templates[template] = DetectorGroup.TABS
        return templates
