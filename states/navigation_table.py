"""Static v1 adjacency table for navigation actions."""

from dataclasses import dataclass

from states.navigation_intent import (
    ActionId,
    IntentId,
    PostconditionId,
    ReasonCode,
)
from utils.scene_snapshot import ElementId, SceneId


@dataclass(frozen=True)
class NavigationEdge:
    intent_id: IntentId
    source: SceneId
    target: SceneId
    required_element: ElementId
    action: ActionId
    postcondition: PostconditionId
    reason: ReasonCode


V1_NAVIGATION_EDGES = (
    NavigationEdge(
        IntentId.COLLECT_DIAMOND,
        SceneId.LOBBY,
        SceneId.LOBBY,
        ElementId.CLOSE_OVERLAY,
        ActionId.DISMISS_OVERLAY,
        PostconditionId.OVERLAY_CLOSED,
        ReasonCode.DIAMOND_CLOSE_OVERLAY,
    ),
    NavigationEdge(
        IntentId.COLLECT_DIAMOND,
        SceneId.LOBBY,
        SceneId.TOWN,
        ElementId.GOBACK_TOWN,
        ActionId.RETURN_TOWN,
        PostconditionId.TOWN,
        ReasonCode.DIAMOND_RETURN_TO_TOWN,
    ),
    NavigationEdge(
        IntentId.COLLECT_DIAMOND,
        SceneId.TOWN,
        SceneId.DIAMOND_WINDOW,
        ElementId.DIAMOND_ENTRY,
        ActionId.OPEN_DIAMOND,
        PostconditionId.DIAMOND_WINDOW,
        ReasonCode.DIAMOND_ENTRY_READY,
    ),
    NavigationEdge(
        IntentId.COLLECT_BREAD,
        SceneId.TOWN,
        SceneId.LOBBY,
        ElementId.DOOR,
        ActionId.ENTER_LOBBY,
        PostconditionId.LOBBY,
        ReasonCode.BREAD_ENTER_LOBBY,
    ),
    NavigationEdge(
        IntentId.COLLECT_BREAD,
        SceneId.LOBBY,
        SceneId.BREAD_WINDOW,
        ElementId.BREAD_ENTRY,
        ActionId.OPEN_BREAD,
        PostconditionId.BREAD_WINDOW,
        ReasonCode.BREAD_ENTRY_READY,
    ),
    NavigationEdge(
        IntentId.PRIMARY_NAVIGATION,
        SceneId.TOWN,
        SceneId.LOBBY,
        ElementId.DOOR,
        ActionId.ENTER_LOBBY,
        PostconditionId.LOBBY,
        ReasonCode.PRIMARY_ENTER_LOBBY,
    ),
    NavigationEdge(
        IntentId.PRIMARY_NAVIGATION,
        SceneId.LOBBY,
        SceneId.LOADING,
        ElementId.START,
        ActionId.START_PRIMARY,
        PostconditionId.LOADING_OR_BATTLE,
        ReasonCode.PRIMARY_START_READY,
    ),
)


class NavigationTable:
    """Return the first declared edge satisfied by one immutable snapshot."""

    def __init__(self, edges=V1_NAVIGATION_EDGES):
        self.edges = tuple(edges)

    def next_edge(self, scene, intent_id):
        for edge in self.edges:
            if (
                edge.intent_id == intent_id
                and edge.source == scene.scene
                and scene.has(edge.required_element)
            ):
                return edge
        return None
