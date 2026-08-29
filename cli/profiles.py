"""Profile selection policies used by the command-line entry point."""


def resolve_profile_name(args, target_title: str = "") -> str:
    """Resolve the active profile without reading files or touching game state."""
    explicit_profile = getattr(args, "profile", None)
    if explicit_profile:
        return explicit_profile.strip().lower()

    target = str(getattr(args, "target", "") or "").strip().lower()
    sandbox_targets = {"sandbox", "sandboxed", "box", "sb", "2"}
    if target in sandbox_targets or "[#]" in target_title:
        return "sandbox"
    return "native"


def resolve_status_filename(args, target_title: str = "") -> str:
    """Return the profile-relative daily-status file location."""
    return f"{resolve_profile_name(args, target_title)}/daily_status.json"
