import logging
import os
import time
from typing import Dict, List, Optional, Tuple

from config import compute_screen_scale
from utils.detector_registry import DetectorGroup, DetectorRegistry
from utils.scene_snapshot import DetectionProfileId, LobbyTabScope, SceneDetectionRequest, TabId
from vision.matcher import TemplateMatcher
from utils.scene_types import (
    LOBBY_TAB_BY_NAME,
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
    "LOBBY_TAB_BY_NAME",
    "LobbyTabScope",
    "SceneDetectionRequest",
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


LOBBY_TAB_THRESHOLD: float = 0.70
LOBBY_TAB_CLEAR_MARGIN: float = 0.025
LOBBY_TAB_MARGIN: float = 0.02
LOBBY_TAB_CONFLICT_DIFF: float = 0.05
LOBBY_TAB_RED_HALO_THRESHOLD: float = 0.07


def verify_tab_red_halo(
    screen_img,
    pos: Tuple[int, int],
    btn_size: Tuple[int, int] = (160, 160),
    inner_ratio: float = 0.75,
    outer_ratio: float = 1.05,
    threshold_ratio: float = 0.07,
) -> bool:
    """
    向量化計算大廳按鈕匹配位置外環的紅色發光光環 (Red Halo Ring) 比例。
    大廳 5 大頁籤選中態皆具備顯著的高飽和紅色圓環 (H in [0, 12] or [165, 180], S>=70, V>=70)，
    未選中態為灰黑金屬環。在歸一化半徑 [0.75, 1.05] 區間進行二維物理特徵消歧。
    """
    if screen_img is None or not hasattr(screen_img, "shape") or len(screen_img.shape) < 3:
        return False
    try:
        import cv2
        import numpy as np
    except ImportError:
        return False

    cx, cy = int(pos[0]), int(pos[1])
    bw, bh = int(btn_size[0]), int(btn_size[1])
    img_h, img_w = screen_img.shape[:2]

    half_w, half_h = max(10, bw // 2), max(10, bh // 2)
    x1 = max(0, cx - half_w)
    y1 = max(0, cy - half_h)
    x2 = min(img_w, cx + half_w)
    y2 = min(img_h, cy + half_h)

    if x2 <= x1 or y2 <= y1:
        return False

    roi = screen_img[y1:y2, x1:x2]
    roi_h, roi_w = roi.shape[:2]
    if roi_h < 10 or roi_w < 10:
        return False

    roi_cx, roi_cy = cx - x1, cy - y1
    y_idx, x_idx = np.indices((roi_h, roi_w))
    norm_x = (x_idx - roi_cx) / float(half_w)
    norm_y = (y_idx - roi_cy) / float(half_h)
    dist = np.sqrt(norm_x**2 + norm_y**2)

    ring_mask = (dist >= inner_ratio) & (dist <= outer_ratio)
    total_ring_pixels = np.count_nonzero(ring_mask)
    if total_ring_pixels < 20:
        return False

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h_chan, s_chan, v_chan = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    red_pixels = (
        ((h_chan <= 12) | (h_chan >= 165))
        & (s_chan >= 70)
        & (v_chan >= 70)
        & ring_mask
    )
    red_count = np.count_nonzero(red_pixels)
    ratio = red_count / float(total_ring_pixels)
    return ratio >= threshold_ratio


class SceneDetector:
    def __init__(self, matcher: Optional[TemplateMatcher] = None):
        self.matcher = matcher or TemplateMatcher()
        self.registry = DetectorRegistry()
        self._active_profile = DetectionProfileId.UNKNOWN
        self._runtime_templates = {}
        self._frame_match_cache = {}
        self._last_tab_was_full_relocalize = False

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
        request: Optional[SceneDetectionRequest] = None,
    ) -> SceneInfo:
        """
        偵測傳入畫面 screen_img 之完整場景資訊與 UI 頁籤狀態。
        嚴格遵循 階段0 ➔ 階段1 ➔ 階段2 ➔ 階段3 ➔ 階段4 之優先順序。
        """
        if request is not None:
            effective_profile = request.profile
        else:
            effective_profile = profile
            request = SceneDetectionRequest(
                profile=profile,
                expected_tab=None,
                tab_scope=LobbyTabScope.FULL_RELOCALIZE,
                reason="legacy_or_unspecified",
            )
        self._active_profile = effective_profile
        self._frame_match_cache = {}
        self._runtime_templates = self._build_runtime_templates(machine)
        scene_info = SceneInfo(scene_type=SceneType.UNKNOWN)

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

        # 4. 大廳頁籤解析與消歧 (支援 EXPECTED_TAB fast path 與 FULL_RELOCALIZE 仲裁)
        winner_name, winner_scene, winner_conf, is_tab_conflict = self._resolve_lobby_tabs(
            screen_img, machine, scene_info, request=request
        )

        # 5. 模板備援掃描 (僅在未確定頁籤、無衝突且非明確 target inactive 狀態時允許)
        allow_card_fallback = (
            config_type in {"stage", "dungeon", "mix", "daily"}
            and not is_tab_conflict
            and winner_name is None
            and self._last_tab_was_full_relocalize
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
        request: Optional[SceneDetectionRequest] = None,
    ) -> Tuple[Optional[str], Optional[SceneType], float, bool]:

        """調度大廳頁籤（Lobby Tabs）的感知策略並解析當前啟動的分頁。
        依據當前感知 Profile 權限與請求範疇（Tab Scope）進行分流：
        1. 權限檢查：若當前 Profile 未啟用 DetectorGroup.TABS，則直接跳過分頁辨識。
        2. 最小感知（Minimal Perception）：若請求指定 EXPECTED_TAB，僅針對預期頁籤進行
           快速比對驗證，避免非必要全量比對。
        3. 全量重定位（Full Relocalization）：若未指定預期頁籤或要求完整掃描，比對所有
           可用頁籤並記錄 _last_tab_was_full_relocalize 標記供遙測追蹤。
        Args:
            screen_img: 當前截圖影像。
            machine: 遊戲狀態機實例。
            scene_info: 當前幀累積的場景資訊物件。
            request: 可選的場景偵測請求，包含 tab_scope 與 expected_tab。
        Returns:
            Tuple[Optional[str], Optional[SceneType], float, bool]:
                - winner_name: 最佳匹配的分頁名稱（若未匹配成功則為 None）。
                - scene_type: 對應解析出的場景類型（如 SceneType.STAGE_SELECT）。
                - best_val: 匹配相似度分數。
                - is_lobby: 是否確認處於大廳分頁結構中。
        """
        allow_tabs = self.registry.allows_group(self._active_profile, DetectorGroup.TABS)
        if not allow_tabs:
            self._last_tab_was_full_relocalize = False
            return None, None, 0.0, False

        if request and request.tab_scope == LobbyTabScope.EXPECTED_TAB and request.expected_tab:
            return self._resolve_expected_lobby_tab(screen_img, machine, scene_info, request)

        self._last_tab_was_full_relocalize = True
        reason = request.reason if request else "default"
        return self._resolve_full_relocalize(screen_img, machine, scene_info, reason=reason)

    def _resolve_expected_lobby_tab(
        self,
        screen_img,
        machine,
        scene_info: SceneInfo,
        request: SceneDetectionRequest,
    ) -> Tuple[Optional[str], Optional[SceneType], float, bool]:
        t0 = time.monotonic()
        tab_key = (
            request.expected_tab.value
            if hasattr(request.expected_tab, "value")
            else str(request.expected_tab)
        )
        tab = LOBBY_TAB_BY_NAME.get(tab_key)
        if not tab:
            logging.warning("[LobbyTabFastPath] Unknown expected tab '%s'; upgrading to full relocalize", tab_key)
            self._last_tab_was_full_relocalize = True
            return self._resolve_full_relocalize(
                screen_img, machine, scene_info, reason="unknown_expected_tab"
            )

        active_tmpl = tab.active_template
        inactive_tmpl = tab.inactive_template
        if machine and getattr(machine, "config", None):
            cfg = machine.config
            if tab.config_active_key and tab.config_active_key in cfg:
                active_tmpl = cfg[tab.config_active_key] or active_tmpl
            if tab.config_inactive_key and tab.config_inactive_key in cfg:
                inactive_tmpl = cfg[tab.config_inactive_key] or inactive_tmpl

        pos_act, conf_act = self._safe_match(screen_img, active_tmpl, threshold=LOBBY_TAB_THRESHOLD)
        pos_inact, conf_inact = self._safe_match(screen_img, inactive_tmpl, threshold=LOBBY_TAB_THRESHOLD)

        if conf_act < LOBBY_TAB_THRESHOLD and hasattr(self.matcher, "match_mutually_exclusive_tabs"):
            res = self.matcher.match_mutually_exclusive_tabs(
                screen_img, active_tmpl, inactive_tmpl, margin=LOBBY_TAB_MARGIN, threshold=LOBBY_TAB_THRESHOLD
            )
            parsed = _parse_tab_result(res)
            if parsed and parsed[0] and not parsed[1]:
                conf_act = max(conf_act, parsed[2])
                conf_inact = max(conf_inact, parsed[3])

        if pos_act:
            scene_info.matched_elements[active_tmpl] = (pos_act, conf_act)
            scene_info.is_lobby = True
        if pos_inact:
            scene_info.matched_elements[inactive_tmpl] = (pos_inact, conf_inact)
            scene_info.is_lobby = True

        elapsed = time.monotonic() - t0
        scale = compute_screen_scale(screen_img)

        # 1. Active dominance (二維色相光環與差值分級消歧)
        if self._evaluate_tab_active(screen_img, tab.name, conf_act, pos_act, conf_inact, pos_inact, scale=scale):
            self._last_tab_was_full_relocalize = False
            logging.debug(
                "[LobbyTabFastPath] tab=%s active_conf=%.4f inactive_conf=%.4f elapsed=%.3fs upgrade=False",
                tab.name, conf_act, conf_inact, elapsed
            )
            return tab.name, tab.scene_type, conf_act, False

        # 2. Inactive confirmed or active not dominant
        if conf_inact >= LOBBY_TAB_THRESHOLD or pos_inact is not None or conf_act >= LOBBY_TAB_THRESHOLD:
            self._last_tab_was_full_relocalize = False
            logging.debug(
                "[LobbyTabFastPath] tab=%s target_inactive active_conf=%.4f inactive_conf=%.4f elapsed=%.3fs upgrade=False",
                tab.name, conf_act, conf_inact, elapsed
            )
            return None, None, 0.0, False

        # 3. Both missed: upgrade to bounded full relocalize
        self._last_tab_was_full_relocalize = True
        logging.info(
            "[LobbyTabUpgrade] Expected tab '%s' missed (act=%.4f, inact=%.4f, elapsed=%.3fs); upgrading to FULL_RELOCALIZE",
            tab.name, conf_act, conf_inact, elapsed
        )
        return self._resolve_full_relocalize(
            screen_img, machine, scene_info, reason="expected_tab_miss", expected_tab_name=tab.name
        )

    def _evaluate_tab_active(
        self,
        screen_img,
        tab_name: str,
        conf_act: float,
        pos_act: Optional[Tuple[int, int]],
        conf_inact: float,
        pos_inact: Optional[Tuple[int, int]],
        scale: float = 1.0,
    ) -> bool:
        """結合模板置信度差值分級與按鈕外環色相光環 (Red Halo Ring) 向量化檢驗，判定單一頁籤是否處於 Active 態。

        Contract: docs/features/navigation/lobby_scene_contract.md
        """
        if conf_act < LOBBY_TAB_THRESHOLD and conf_inact < LOBBY_TAB_THRESHOLD:
            return False

        diff = conf_act - conf_inact

        if diff >= LOBBY_TAB_CLEAR_MARGIN:
            return True
        if diff <= -LOBBY_TAB_CLEAR_MARGIN:
            return False

        # 微差模糊邊界區間
        pos = pos_act or pos_inact
        if pos is not None and screen_img is not None and hasattr(screen_img, "shape") and len(screen_img.shape) >= 3:
            bw = int(160 * scale)
            bh = int(160 * scale)
            has_red = verify_tab_red_halo(
                screen_img,
                pos,
                btn_size=(bw, bh),
                inner_ratio=0.75,
                outer_ratio=1.05,
                threshold_ratio=LOBBY_TAB_RED_HALO_THRESHOLD,
            )
            if has_red:
                logging.debug(
                    "[LobbyTabDisambiguation] tab=%s ambiguous diff=%.4f (act=%.4f, inact=%.4f) -> ACTIVE via red halo",
                    tab_name, diff, conf_act, conf_inact
                )
                return True
            else:
                logging.debug(
                    "[LobbyTabDisambiguation] tab=%s ambiguous diff=%.4f (act=%.4f, inact=%.4f) -> INACTIVE via dark halo",
                    tab_name, diff, conf_act, conf_inact
                )
                return False

        return diff > LOBBY_TAB_MARGIN

    def _resolve_full_relocalize(
        self,
        screen_img,
        machine,
        scene_info: SceneInfo,
        reason: str = "default",
        expected_tab_name: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[SceneType], float, bool]:
        t0 = time.monotonic()
        scale = compute_screen_scale(screen_img)
        candidates: List[Tuple[str, SceneType, float]] = []

        for tab in LOBBY_TAB_DEFINITIONS:
            active_tmpl = tab.active_template
            inactive_tmpl = tab.inactive_template
            if machine and getattr(machine, "config", None):
                cfg = machine.config
                if tab.config_active_key and tab.config_active_key in cfg:
                    active_tmpl = cfg[tab.config_active_key] or active_tmpl
                if tab.config_inactive_key and tab.config_inactive_key in cfg:
                    inactive_tmpl = cfg[tab.config_inactive_key] or inactive_tmpl

            pos_act, conf_act = self._safe_match(screen_img, active_tmpl, threshold=LOBBY_TAB_THRESHOLD)
            pos_inact, conf_inact = self._safe_match(screen_img, inactive_tmpl, threshold=LOBBY_TAB_THRESHOLD)

            if pos_act:
                scene_info.matched_elements[active_tmpl] = (pos_act, conf_act)
                scene_info.is_lobby = True
            if pos_inact:
                scene_info.matched_elements[inactive_tmpl] = (pos_inact, conf_inact)
                scene_info.is_lobby = True

            if conf_act < LOBBY_TAB_THRESHOLD and hasattr(self.matcher, "match_mutually_exclusive_tabs"):
                res = self.matcher.match_mutually_exclusive_tabs(
                    screen_img, active_tmpl, inactive_tmpl, margin=LOBBY_TAB_MARGIN, threshold=LOBBY_TAB_THRESHOLD
                )
                parsed = _parse_tab_result(res)
                if parsed and parsed[0] and not parsed[1]:
                    conf_act = max(conf_act, parsed[2])
                    conf_inact = max(conf_inact, parsed[3])
                    scene_info.is_lobby = True

            if self._evaluate_tab_active(screen_img, tab.name, conf_act, pos_act, conf_inact, pos_inact, scale=scale):
                candidates.append((tab.name, tab.scene_type, conf_act))

        elapsed = time.monotonic() - t0

        if len(candidates) == 0:
            logging.info(
                "[FullRelocalize] reason=%s expected_tab=%s candidates=[] winner=None is_conflict=False elapsed=%.3fs",
                reason, expected_tab_name, elapsed
            )
            return None, None, 0.0, False

        if len(candidates) == 1:
            name, st, conf = candidates[0]
            logging.info(
                "[FullRelocalize] reason=%s expected_tab=%s candidates=[('%s', '%.4f')] winner=%s is_conflict=False elapsed=%.3fs",
                reason, expected_tab_name, name, conf, name, elapsed
            )
            return name, st, conf, False

        candidates.sort(key=lambda item: item[2], reverse=True)
        top_tab = candidates[0]
        second_tab = candidates[1]
        diff = top_tab[2] - second_tab[2]

        cand_summary = [(c[0], round(c[2], 4)) for c in candidates]
        if diff >= LOBBY_TAB_CONFLICT_DIFF:
            logging.info(
                "[FullRelocalize] reason=%s expected_tab=%s candidates=%s winner=%s is_conflict=False elapsed=%.3fs",
                reason, expected_tab_name, cand_summary, top_tab[0], elapsed
            )
            return top_tab[0], top_tab[1], top_tab[2], False

        logging.warning(
            "[FullRelocalize] Conflicting active lobby tabs with insufficient margin (diff=%.4f): %s (elapsed=%.3fs)",
            diff,
            cand_summary,
            elapsed,
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
