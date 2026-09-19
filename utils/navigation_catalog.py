"""Physical card-order catalogs used by navigation phases.

This module deliberately contains no availability, cooldown, scheduler, or
combat policy.  Each mode adapter supplies only declaration-order card keys
and templates; the shared builder assigns stable 1-based physical indices.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import NamedTuple


class NavigationCatalogEntry(NamedTuple):
    """One physical card position: ``(index, card_key, template)``."""

    index: int
    key: str
    template: str


def build_ordered_navigation_catalog(
    cards: Iterable[tuple[object, object]],
    *,
    indices: Iterable[int] | None = None,
) -> list[NavigationCatalogEntry]:
    """Assign 1-based indices to declaration-order ``(key, template)`` pairs."""

    indexed_cards = enumerate(cards, start=1) if indices is None else zip(indices, cards)
    return [
        NavigationCatalogEntry(int(index), str(key), str(template))
        for index, (key, template) in indexed_cards
    ]


def stage_navigation_catalog(
    base_stage_levels: Mapping[object, Mapping[str, object]],
) -> list[NavigationCatalogEntry]:
    """Build Stage order from numeric base-level identity and canonical entries."""

    numeric_levels = sorted(
        (
            int(level_key),
            level_config,
        )
        for level_key, level_config in base_stage_levels.items()
        if str(level_key).isdigit()
    )
    return build_ordered_navigation_catalog(
        (
            (level_key, level_config["entry"])
            for level_key, level_config in numeric_levels
        ),
        indices=(level_key for level_key, _level_config in numeric_levels),
    )


def dungeon_navigation_catalog(
    custom_names: Sequence[str] | None = None,
    custom_entries: Sequence[str] | None = None,
) -> list[NavigationCatalogEntry]:
    """Build Dungeon order through the existing ``DungeonCatalog`` authority."""

    from utils.dungeon_catalog import DungeonCatalog

    return build_ordered_navigation_catalog(
        (
            DungeonCatalog.get_name(index, custom_names=custom_names),
            DungeonCatalog.get_entry_template(index, custom_entries=custom_entries),
        )
        for index in DungeonCatalog.get_all_indices(custom_names)
    )


def domain_navigation_catalog(
    canonical_domain_configs: Mapping[str, Mapping[str, object]],
) -> list[NavigationCatalogEntry]:
    """Build Domain order from canonical declaration order and entry buttons."""

    return build_ordered_navigation_catalog(
        (mode_key, config["domain_entry_btn"])
        for mode_key, config in canonical_domain_configs.items()
    )


def boss_navigation_catalog(
    bosses: Mapping[str, Mapping[str, object]],
) -> list[NavigationCatalogEntry]:
    """Build declaration-order boss metadata without applying availability policy."""

    return build_ordered_navigation_catalog(
        (boss_key, boss_config["template"])
        for boss_key, boss_config in bosses.items()
    )


def lord_navigation_catalog(
    bosses: Mapping[str, Mapping[str, object]],
) -> list[NavigationCatalogEntry]:
    """Build the Lord catalog from its configured boss declarations."""

    return boss_navigation_catalog(bosses)


def demon_lord_navigation_catalog(
    bosses: Mapping[str, Mapping[str, object]],
) -> list[NavigationCatalogEntry]:
    """Build the Demon Lord catalog from its configured boss declarations."""

    return boss_navigation_catalog(bosses)
