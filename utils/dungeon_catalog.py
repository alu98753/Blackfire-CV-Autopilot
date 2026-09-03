"""Single Source of Truth domain service for 1-based dungeon lookups and cooldown reports."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Mapping, Sequence

from utils.time_parser import format_seconds_to_readable


@dataclass(frozen=True)
class DungeonCooldownReport:
    """Immutable status report for dungeon cooldown evaluations."""

    summary_str: str
    available_names: list[str]
    available_indices: list[int]
    min_remaining_seconds: float
    has_available: bool


class DungeonCatalog:
    """SSOT query helper and cooldown report generator for 1-based dungeon indices (1..6)."""

    @staticmethod
    def _resolve_names(custom_names: Sequence[str] | None = None) -> Sequence[str]:
        if custom_names is not None:
            return custom_names
        from config import DUNGEON_NAMES
        return DUNGEON_NAMES

    @staticmethod
    def _resolve_entries(custom_entries: Sequence[str] | None = None) -> Sequence[str]:
        if custom_entries is not None:
            return custom_entries
        from config import DUNGEON_ENTRY_TEMPLATES
        return DUNGEON_ENTRY_TEMPLATES

    @classmethod
    def get_name(
        cls,
        idx: int | None,
        default: str = "地下城",
        custom_names: Sequence[str] | None = None,
    ) -> str:
        """Return 1-based dungeon name safely without throwing IndexError."""
        if idx is None or not isinstance(idx, int):
            return default
        names = cls._resolve_names(custom_names)
        if 1 <= idx <= len(names):
            return names[idx - 1]
        return default

    @classmethod
    def get_entry_template(
        cls,
        idx: int | None,
        default: str = "dungeons/Ice_entry.png",
        custom_entries: Sequence[str] | None = None,
    ) -> str:
        """Return 1-based dungeon entry template safely without throwing IndexError."""
        if idx is None or not isinstance(idx, int):
            return default
        entries = cls._resolve_entries(custom_entries)
        if 1 <= idx <= len(entries):
            return entries[idx - 1]
        return default

    @classmethod
    def resolve_index_from_nav_path(
        cls,
        nav_path: Sequence[str] | None,
        custom_entries: Sequence[str] | None = None,
    ) -> int | None:
        """Match entry templates against navigation_path and return 1-based index or None."""
        if not nav_path:
            return None
        entries = cls._resolve_entries(custom_entries)
        for idx, template_name in enumerate(entries, start=1):
            if template_name in nav_path:
                return idx
        return None

    @classmethod
    def is_valid_index(
        cls,
        idx: Any,
        custom_names: Sequence[str] | None = None,
    ) -> bool:
        """Return True if index is an integer in the 1-based range [1..max_dungeon]."""
        if not isinstance(idx, int):
            return False
        names = cls._resolve_names(custom_names)
        return 1 <= idx <= len(names)

    @classmethod
    def build_default_cooldowns(
        cls,
        custom_names: Sequence[str] | None = None,
    ) -> dict[int, float]:
        """Return fresh {1: 0.0, ..., max: 0.0} 1-based cooldown dictionary."""
        names = cls._resolve_names(custom_names)
        return {idx: 0.0 for idx in range(1, len(names) + 1)}

    @classmethod
    def format_cooldown_report(
        cls,
        dungeon_cooldowns: Mapping[int, float],
        target_indices: Sequence[int] | None = None,
        now_ts: float | None = None,
        custom_names: Sequence[str] | None = None,
    ) -> DungeonCooldownReport:
        """Generate unified, safe cooldown details, available list, and min remaining seconds."""
        names = cls._resolve_names(custom_names)
        now = time.time() if now_ts is None else now_ts

        indices = (
            list(target_indices)
            if target_indices is not None
            else list(range(1, len(names) + 1))
        )

        cd_details: list[str] = []
        available_names: list[str] = []
        available_indices: list[int] = []
        min_remaining = 180.0
        has_positive_cooldown = False

        for idx in indices:
            if not isinstance(idx, int) or idx < 1 or idx > len(names):
                continue

            name = names[idx - 1]
            cd_until = dungeon_cooldowns.get(idx, 0.0) if dungeon_cooldowns else 0.0
            rem = cd_until - now

            if rem > 0:
                has_positive_cooldown = True
                if cd_until == float("inf"):
                    cd_details.append(f"[{name}]: 永久不可打")
                else:
                    cd_str = format_seconds_to_readable(int(rem))
                    cd_details.append(f"[{name}]: 冷卻中 ({cd_str})")
                    if rem < min_remaining:
                        min_remaining = rem
            else:
                cd_details.append(f"[{name}]: 就緒 (可打)")
                available_names.append(name)
                available_indices.append(idx)

        summary_str = ", ".join(cd_details) if cd_details else "無地下城資訊"
        actual_min_rem = min_remaining if has_positive_cooldown else 0.0

        return DungeonCooldownReport(
            summary_str=summary_str,
            available_names=available_names,
            available_indices=available_indices,
            min_remaining_seconds=actual_min_rem,
            has_available=len(available_indices) > 0,
        )
