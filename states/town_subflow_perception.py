"""Goal-scoped observations for Town workflow navigation."""

import time

from config import GAME_CONFIGS
from states.town_subflow_registry import spec_for
from utils.scene_snapshot import ElementId, ElementMatch, SceneId, SceneSnapshot
from utils.town_building_detector import detect_building_with_red_dot


EXIT_BUILDING_TEMPLATE = "town_building/exitfromhouse_and_to_town.png"
OVERLAY_CLOSE_TEMPLATES = (
    "common/confirm.png",
    "common/ok.png",
    "common/cancel.png",
    "common/quit.png",
)


class TownSubflowPerception:
    def __init__(self, machine):
        self.machine = machine
        self.matcher = machine.matcher

    def observe(self, screen_img, flow_key: str) -> SceneSnapshot:
        scene, confidence = self._observe_committed_scene(screen_img)
        if scene != SceneId.UNKNOWN:
            return self._snapshot(scene, {}, confidence)

        elements = {}
        matches = {
            ElementId.CLOSE_OVERLAY: self._match_first(
                screen_img, OVERLAY_CLOSE_TEMPLATES, 0.80
            ),
            ElementId.EXIT_BUILDING_TO_TOWN: self._match(
                screen_img, EXIT_BUILDING_TEMPLATE, 0.75
            ),
            ElementId.GOBACK_TOWN: self._match(screen_img, "goback_town.png", 0.80),
            ElementId.EXIT_TO_LOBBY: self._match(
                screen_img, "domains/common/exit_to_lobby.png", 0.80
            ),
            ElementId.DOOR: self._match(screen_img, "common/door.png", 0.80),
            ElementId.DIAMOND_ENTRY: self._match(screen_img, "diamond.png", 0.80),
        }
        elements.update({key: value for key, value in matches.items() if value})

        scene = self._classify_scene(elements)
        if scene == SceneId.TOWN:
            self._observe_entry(screen_img, flow_key, elements)
        return self._snapshot(scene, elements)

    def _observe_committed_scene(self, screen_img):
        result_templates = (
            "defeat.png",
            "common/continue.png",
            "common/continue1.png",
            "common/continue2.png",
            "common/continue_gray.png",
            "stages/retry.png",
            "exit_battle.png",
        )
        for template in result_templates:
            threshold = 0.88 if template == "common/continue_gray.png" else 0.80
            match = self._match(screen_img, template, threshold)
            if match:
                return SceneId.RESULT, match.confidence

        for template in self.machine.dungeon_detection_features():
            match = self._match(screen_img, template, 0.80)
            if match:
                return SceneId.DUNGEON_EXPLORING, match.confidence

        for template in (
            "common/auto.png",
            "battle/battle_features_1.png",
            "battle/battle_features_2.png",
        ):
            match = self._match(screen_img, template, 0.70)
            if match:
                return SceneId.BATTLE, match.confidence
        return SceneId.UNKNOWN, 0.0

    def _observe_entry(self, screen_img, flow_key, elements):
        spec = spec_for(flow_key)
        if spec.dispatch_on_town or not spec.building_template:
            return
        building_template = GAME_CONFIGS.get(flow_key, {}).get(
            "building_btn", spec.building_template
        )
        result = detect_building_with_red_dot(
            screen_img,
            building_template,
            self.matcher,
            debug_tag=flow_key,
        )
        if not result.found_building or result.building_pos is None:
            return
        elements[ElementId.TOWN_SUBFLOW_ENTRY] = ElementMatch(
            *result.building_pos,
            result.confidence_building,
            building_template,
        )
        if result.has_red_dot:
            red_pos = result.red_dot_pos or result.building_pos
            elements[ElementId.TOWN_SUBFLOW_RED_DOT] = ElementMatch(
                *red_pos,
                result.confidence_red_dot,
                "town_building/red_dot.png",
            )

    def _match(self, screen_img, template_name, threshold):
        try:
            result = self.matcher.match(
                screen_img, template_name, threshold=threshold, quiet=True
            )
        except (OSError, TypeError, ValueError):
            return None
        if not isinstance(result, (tuple, list)) or len(result) < 2 or not result[0]:
            return None
        return ElementMatch(
            result[0][0],
            result[0][1],
            float(result[1] or 0.0),
            template_name,
        )

    def _match_first(self, screen_img, template_names, threshold):
        for template_name in template_names:
            match = self._match(screen_img, template_name, threshold)
            if match:
                return match
        return None

    @staticmethod
    def _classify_scene(elements):
        if ElementId.DOOR in elements or ElementId.DIAMOND_ENTRY in elements:
            return SceneId.TOWN
        if ElementId.EXIT_BUILDING_TO_TOWN in elements:
            return SceneId.TOWN_BUILDING
        if ElementId.EXIT_TO_LOBBY in elements:
            return SceneId.DOMAIN_EXPLORE
        if ElementId.GOBACK_TOWN in elements:
            return SceneId.LOBBY
        return SceneId.UNKNOWN

    def _snapshot(self, scene, elements, confidence=None):
        frame_id = int(getattr(self.machine, "_town_navigation_frame_id", 0)) + 1
        self.machine._town_navigation_frame_id = frame_id
        if confidence is None:
            confidence = max(
                (match.confidence for match in elements.values()), default=0.0
            )
        return SceneSnapshot(
            frame_id=frame_id,
            captured_at=self._now(),
            scene=scene,
            confidence=confidence,
            elements=elements,
        )

    def _now(self):
        clock = getattr(self.machine, "clock", None)
        return clock.monotonic() if clock is not None else time.monotonic()
