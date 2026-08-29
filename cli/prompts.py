"""Terminal input helpers with non-interactive fallbacks."""


def prompt_choice(prompt_text: str, default_val: str) -> str:
    """Return terminal input, falling back to the supplied default when unavailable."""
    try:
        value = input(prompt_text).strip()
        return value if value else default_val
    except (EOFError, KeyboardInterrupt, Exception):
        return default_val
