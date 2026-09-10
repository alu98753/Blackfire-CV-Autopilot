import logging
import os
from typing import Dict, List, Optional, Tuple

from utils.detector_registry import DetectorGroup, DetectorRegistry
from utils.scene_snapshot import DetectionProfileId
from vision.matcher import TemplateMatcher
from utils.scene_types import (
    LOBBY_TAB_DEFINITIONS,
    LobbyTabDefinition,
    SceneAnchorSpec,
    SceneId,
    SceneInfo,
    SceneType,
)

# Re-export for 100% backward compatibility
__all__ = [
    "SceneId",
    "SceneType",
    "SceneInfo",
    "LobbyTabDefinition",
    "SceneAnchorSpec",
    "LOBBY_TAB_DEFINITIONS",
    "SceneDetector",
]


def _parse_tab_result(res) -> Optional[Tuple[bool, bool, float, float]]:
    """
    標準化解析互斥頁籤比對結果。
    支援標準契約 (is_a, is_b, conf_a, conf_b)，
    以及容錯相容舊測試中偶見之 (is_a, is_b, pos, conf)。
    """
    if not isinstance(res, (tuple, list)) or len(res) < 4:
        return None
    try:
        is_a = bool(res[0])
        is_b = bool(res[1])
    except Exception:
        return None

    # 標準契約：res[2] 與 res[3] 皆為數值
    if isinstance(res[2], (int, float)) and isinstance(res[3], (int, float)):
        return is_a, is_b, float(res[2]), float(res[3])

    # 舊測試相容：res[2] 為位置 tuple/list，res[3] 為信心度
    if isinstance(res[3], (int, float)):
        conf = float(res[3])
        conf_a = conf if is_a else 0.10
        conf_b = conf if is_b else 0.10
        return is_a, is_b, conf_a, conf_b

    return None


SCENE_ANCHOR_SPECS: Tuple[SceneAnchorSpec, ...] = (
    SceneAnchorSpec(
        scene_id=SceneId.POPUP_TASK_COMPLETE,
        required_any=("task_complete.png",),
        min_confidence=0.75,
    ),
    SceneAnchorSpec(
        scene_id=SceneId.DUNGEON_EXPLORING,
        required_any=(
            "dungeons/leave.png",
            "dungeons/dungeon_bless.png",
            "dungeons/Treasure.png",
            "dungeons/gungeon_godown.png",
        ),
        min_confidence=0.80,
    ),
    SceneAnchorSpec(
        scene_id=SceneId.DUNGEON_LOBBY,
        required_any=("dungeons/dungeon_fight.png",),
        min_confidence=0.80,
    ),
    SceneAnchorSpec(
        scene_id=SceneId.TOWN,
        required_any=("common/door.png", "diamond.png"),
        min_confidence=0.80,
    ),
)


class SceneDetector:
    def __init__(self, matcher: Optional[TemplateMatcher] = None):
        self.matcher = matcher or TemplateMatcher()
        self.registry = DetectorRegistry()
        self._active_profile = DetectionProfileId.UNKNOWN
        self._runtime_templates = {}
        self._frame_match_cache = {}

    def _safe_match(self, screen_img, template_name: str, threshold: float = 0.8) -> Tuple[Optional[Tuple[int, int]], float]:
        """
        安全包裝 TemplateMatcher.match()，符合 (pos, confidence) 回傳契約。
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

        # 4. 大廳 5 大頁籤對稱解析與仲裁 (10 模板感知)
        winner_name, winner_scene, winner_conf, is_tab_conflict = self._resolve_lobby_tabs(
            screen_img, machine, scene_info
        )

        # 5. 模板備援掃描 (僅在未確定頁籤且無頁籤衝突時允許)
        allow_card_fallback = (
            config_type in {"stage", "dungeon", "mix", "daily"}
            and not is_tab_conflict
            and winner_name is None
        )
        if allow_card_fallback and machine and getattr(machine, "config", None):
            stage_templates = machine.config.get("stage_templates", [])
            for st_temp in stage_templates:
                if os.path.exists(os.path.join("templates", st_temp)):
                    pos, conf = self._safe_match(screen_img, st_temp, threshold=0.85)
                    if pos:
                        winner_name = "stage"
                        winner_scene = SceneType.LOBBY_STAGE
                        scene_info.matched_elements[st_temp] = (pos, conf)
                        break

        if allow_card_fallback and winner_name is None and machine and getattr(machine, "config", None):
            dungeon_templates = machine.config.get("dungeon_entries", [])
            for dg_temp in dungeon_templates:
                if os.path.exists(os.path.join("templates", dg_temp)):
                    pos, conf = self._safe_match(screen_img, dg_temp, threshold=0.85)
                    if pos:
                        winner_name = "dungeon"
                        winner_scene = SceneType.LOBBY_DUNGEON
                        scene_info.matched_elements[dg_temp] = (pos, conf)
                        break

        # 6. 最終場景判定輸出
        if winner_name and winner_scene:
            scene_info.scene_type = winner_scene
            scene_info.active_tabs = [winner_name]
        elif scene_info.is_lobby:
            scene_info.scene_type = SceneType.LOBBY_OTHER

        return scene_info

    def _resolve_lobby_tabs(
        self,
        screen_img,
        machine,
        scene_info: SceneInfo,
    ) -> Tuple[Optional[str], Optional[SceneType], float, bool]:
        """
        對稱成對評估大廳 5 大頁籤 (共 10 張模板)。
        1. 任何頁籤模板 (active 或 inactive) 出現，即為身處活動大廳之鐵證 (is_lobby = True)。
        2. 5 大頁籤統一對稱檢驗：Active 信心度 >= 0.70 且顯著高於 Inactive (margin 0.02)。
        3. 最大信心度仲裁 (Max-Confidence Disambiguation)：
           - 0 個 active：回傳 (None, None, 0.0, False)
           - 1 個 active：直接勝出
           - >1 個 active：最高信心度顯著領先 (diff >= 0.05) 則勝出；若差距 < 0.05 視為真衝突。
        回傳 (winner_name, winner_scene_type, winner_conf, is_conflict)
        """
        candidates: List[Tuple[str, SceneType, float]] = []
        allow_tabs = self.registry.allows_group(self._active_profile, DetectorGroup.TABS)
        if not allow_tabs:
            return None, None, 0.0, False

        # 1. 遍歷 5 大頁籤成對評估
        for tab in LOBBY_TAB_DEFINITIONS:
            active_tmpl = tab.active_template
            inactive_tmpl = tab.inactive_template
            if machine and getattr(machine, "config", None):
                cfg = machine.config
                if tab.config_active_key and tab.config_active_key in cfg:
                    active_tmpl = cfg[tab.config_active_key] or active_tmpl
                if tab.config_inactive_key and tab.config_inactive_key in cfg:
                    inactive_tmpl = cfg[tab.config_inactive_key] or inactive_tmpl

            pos_act, conf_act = self._safe_match(screen_img, active_tmpl, threshold=0.70)
            pos_inact, conf_inact = self._safe_match(screen_img, inactive_tmpl, threshold=0.70)

            # 大廳鐵證：10 模板中任一出現，證明畫面身處活動大廳
            if pos_act:
                scene_info.matched_elements[active_tmpl] = (pos_act, conf_act)
                scene_info.is_lobby = True
            if pos_inact:
                scene_info.matched_elements[inactive_tmpl] = (pos_inact, conf_inact)
                scene_info.is_lobby = True

            # 相容 Matcher 互斥介面 (相容 Mock 或外部自訂 Matcher)
            if conf_act < 0.70 and hasattr(self.matcher, "match_mutually_exclusive_tabs"):
                res = self.matcher.match_mutually_exclusive_tabs(
                    screen_img, active_tmpl, inactive_tmpl, margin=0.02, threshold=0.70
                )
                parsed = _parse_tab_result(res)
                if parsed and parsed[0] and not parsed[1]:
                    conf_act = max(conf_act, parsed[2])
                    conf_inact = max(conf_inact, parsed[3])
                    scene_info.is_lobby = True

            # 對稱成對判定：Active 必須達標且勝過 Inactive (杜絕幽靈匹配)
            if conf_act >= 0.70 and conf_act > conf_inact + 0.02:
                candidates.append((tab.name, tab.scene_type, conf_act))

        # 相容舊式 (stage_after vs dungeon_after) 跨頁籤二元比對 Mock
        has_stage_or_dungeon = any(name in {"stage", "dungeon"} for name, _, _ in candidates)
        if not has_stage_or_dungeon and hasattr(self.matcher, "match_mutually_exclusive_tabs"):
            res_legacy = self.matcher.match_mutually_exclusive_tabs(
                screen_img, "common/select_stage_after.png", "dungeons/dungeon_after.png", margin=0.02, threshold=0.70
            )
            parsed_legacy = _parse_tab_result(res_legacy)
            if parsed_legacy:
                is_st, is_dg, c_st, c_dg = parsed_legacy
                # 若兩者信心度皆高 (>= 0.70) 卻均未勝出，說明兩者處於嚴重衝突狀態
                if c_st >= 0.70 and c_dg >= 0.70 and not (is_st ^ is_dg):
                    logging.warning("High confidence tab conflict between stage (%.4f) and dungeon (%.4f)", c_st, c_dg)
                    return None, None, 0.0, True

                if is_st and c_st >= 0.70:
                    candidates.append(("stage", SceneType.LOBBY_STAGE, c_st))
                    scene_info.is_lobby = True
                elif is_dg and c_dg >= 0.70:
                    _, conf_dg_inact = self._safe_match(screen_img, "dungeons/dungeon.png", threshold=0.70)
                    if conf_dg_inact <= c_dg + 0.02:
                        candidates.append(("dungeon", SceneType.LOBBY_DUNGEON, c_dg))
                        scene_info.is_lobby = True

        # 2. 最大信心度仲裁 (Max-Confidence Disambiguation)
        if len(candidates) == 0:
            return None, None, 0.0, False
        if len(candidates) == 1:
            name, st, conf = candidates[0]
            return name, st, conf, False

        candidates.sort(key=lambda item: item[2], reverse=True)
        top_tab = candidates[0]
        second_tab = candidates[1]
        diff = top_tab[2] - second_tab[2]

        if diff >= 0.05:
            return top_tab[0], top_tab[1], top_tab[2], False

        logging.warning(
            "Conflicting active lobby tabs detected with insufficient margin (diff=%.4f): %s",
            diff,
            [c[0] for c in candidates],
        )
        return None, None, 0.0, True

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
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "entry_btn": "",
            "entry_after_btn": "",
        }.items():
            template = config.get(key, default)
            if template:
                templates[template] = DetectorGroup.TABS
        return templates
