"""Immutable scene observations shared by navigation decisions."""

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class SceneId(str, Enum):
    UNKNOWN = "unknown"
    TOWN = "town"
    LOBBY = "lobby"
    DIAMOND_WINDOW = "diamond_window"
    BREAD_WINDOW = "bread_window"
    STAGE_SELECT = "stage_select"
    DUNGEON_SELECT = "dungeon_select"
    STAGE_LOBBY = "stage_lobby"
    DUNGEON_LOBBY = "dungeon_lobby"
    DUNGEON_EXPLORING = "dungeon_exploring"
    LOADING = "loading"
    BATTLE = "battle"
    RESULT = "result"


class ElementId(str, Enum):
    DOOR = "door"
    DIAMOND_ENTRY = "diamond_entry"
    GOBACK_TOWN = "goback_town"
    BREAD_ENTRY = "bread_entry"
    START = "start"
    CLOSE_OVERLAY = "close_overlay"


class OverlayId(str, Enum):
    TASK_COMPLETE = "task_complete"
    UNEXPECTED = "unexpected"


class TabId(str, Enum):
    STAGE = "stage"
    DUNGEON = "dungeon"


class DetectionProfileId(str, Enum):
    UNKNOWN = "unknown"
    TOWN = "town"
    LOBBY = "lobby"
    LOADING = "loading"
    BATTLE = "battle"
    RESULT = "result"


@dataclass(frozen=True)
class ElementMatch:
    client_x: int
    client_y: int
    confidence: float
    template_name: str


@dataclass(frozen=True)
class SceneSnapshot:
    frame_id: int
    captured_at: float
    scene: SceneId
    confidence: float = 0.0
    elements: Mapping[ElementId, ElementMatch] = field(default_factory=dict)
    overlays: frozenset[OverlayId] = field(default_factory=frozenset)
    active_tabs: frozenset[TabId] = field(default_factory=frozenset)
    detection_profile: DetectionProfileId = DetectionProfileId.UNKNOWN

    def __post_init__(self):
        object.__setattr__(self, "elements", MappingProxyType(dict(self.elements)))
        object.__setattr__(self, "overlays", frozenset(self.overlays))
        object.__setattr__(self, "active_tabs", frozenset(self.active_tabs))

    def has(self, element: ElementId) -> bool:
        return element in self.elements


_SCENE_TYPE_MAP = {
    "TOWN": SceneId.TOWN,
    "LOBBY_STAGE": SceneId.LOBBY,
    "LOBBY_DUNGEON": SceneId.LOBBY,
    "LOBBY_OTHER": SceneId.LOBBY,
    "WINDOW_DIAMOND": SceneId.DIAMOND_WINDOW,
    "WINDOW_BREAD": SceneId.BREAD_WINDOW,
    "IN_DUNGEON": SceneId.DUNGEON_EXPLORING,
}

_ELEMENT_TEMPLATE_MAP = {
    "common/door.png": ElementId.DOOR,
    "diamond.png": ElementId.DIAMOND_ENTRY,
    "goback_town.png": ElementId.GOBACK_TOWN,
    "common/bread.png": ElementId.BREAD_ENTRY,
    "common/quit.png": ElementId.CLOSE_OVERLAY,
}


def snapshot_from_scene_info(
    scene_info,
    *,
    frame_id: int,
    captured_at: float,
    start_template: str | None = None,
) -> SceneSnapshot:
    """Adapt legacy SceneInfo without giving it decision responsibilities."""
    scene_type_name = getattr(getattr(scene_info, "scene_type", None), "name", "UNKNOWN")
    scene_id = _SCENE_TYPE_MAP.get(scene_type_name, SceneId.UNKNOWN)
    template_map = dict(_ELEMENT_TEMPLATE_MAP)
    if start_template:
        template_map[start_template] = ElementId.START

    elements = {}
    confidences = []
    for template_name, match in getattr(scene_info, "matched_elements", {}).items():
        element_id = template_map.get(template_name)
        if element_id is None or not match or match[0] is None:
            continue
        (client_x, client_y), confidence = match
        elements[element_id] = ElementMatch(
            client_x=client_x,
            client_y=client_y,
            confidence=float(confidence),
            template_name=template_name,
        )
        confidences.append(float(confidence))

    tabs = {
        TabId(tab)
        for tab in getattr(scene_info, "active_tabs", ())
        if tab in {item.value for item in TabId}
    }
    overlays = set()
    if scene_type_name == "POPUP_TASK_COMPLETE":
        overlays.add(OverlayId.TASK_COMPLETE)

    profile = DetectionProfileId.UNKNOWN
    if scene_id == SceneId.TOWN:
        profile = DetectionProfileId.TOWN
    elif scene_id == SceneId.LOBBY:
        profile = DetectionProfileId.LOBBY

    return SceneSnapshot(
        frame_id=frame_id,
        captured_at=captured_at,
        scene=scene_id,
        confidence=max(confidences, default=0.0),
        elements=elements,
        overlays=frozenset(overlays),
        active_tabs=frozenset(tabs),
        detection_profile=profile,
    )
