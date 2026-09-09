"""Interactive log level configuration, profile persistence, and daily rotation."""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from cli.prompts import prompt_choice
from config import (
    USER_DATA_DIR,
    apply_log_level,
    get_active_profile,
    get_log_level,
    get_log_retention_days,
    update_profile_config,
)

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

_LOG_LEVEL_OPTIONS = (
    ("1", "INFO", "標準模式 (推薦：顯示狀態轉移、重要事件、警告與錯誤)"),
    ("2", "DEBUG", "除錯模式 (顯示完整細節：模板比對分數、像素差異、OCR 座標與耗時)"),
    ("3", "WARNING", "靜音模式 (僅在發生異常、背包滿、卡死重試時提示)"),
    ("4", "ERROR", "極致安靜 (僅在系統崩潰或致命錯誤時輸出)"),
)

_LEVEL_TO_NUM = {lvl: num for num, lvl, _ in _LOG_LEVEL_OPTIONS}
_NUM_TO_LEVEL = {num: lvl for num, lvl, _ in _LOG_LEVEL_OPTIONS}


def init_file_logger(profile: str | None = None) -> Path:
    """Attach a daily midnight rotating file handler to the root logger for the profile."""
    prof = (profile or get_active_profile()).strip().lower()
    log_dir = Path(USER_DATA_DIR) / prof / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, TimedRotatingFileHandler) and getattr(handler, "_app_log_profile", None) == prof:
            return log_file

    retention_days = get_log_retention_days()
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=retention_days,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.setLevel(root_logger.level)
    file_handler._app_log_profile = prof
    root_logger.addHandler(file_handler)
    return log_file


def setup_log_level_config(
    args,
    profile_name: str | None = None,
    is_resume: bool = False,
) -> str:
    """Resolve and apply terminal & file logging with profile-bound persistence.

    Priority:
        1. CLI explicit argument (--log-level)
        2. Supervisor resume (re-use profile-stored preference without prompt)
        3. Interactive menu selection (persists to user_data/<profile>/config.toml)
    """
    prof = (profile_name or get_active_profile()).strip().lower()
    explicit_level = getattr(args, "log_level", None)
    if explicit_level:
        apply_log_level(explicit_level)
        init_file_logger(prof)
        return explicit_level

    current_level = get_log_level()

    if is_resume:
        apply_log_level(current_level)
        init_file_logger(prof)
        return current_level

    default_num = _LEVEL_TO_NUM.get(current_level, "1")

    print("\n請選擇終端機日誌顯示等級 (Log Level)：")
    for num, lvl, desc in _LOG_LEVEL_OPTIONS:
        pref_mark = " [目前偏好]" if lvl == current_level else ""
        print(f" {num}) {lvl.ljust(7)} - {desc}{pref_mark}")

    choice = prompt_choice(
        f"請輸入數字 [1-4] (直接 Enter 保留 {default_num}): ", default_num
    )
    if choice not in _NUM_TO_LEVEL:
        print(f"[!] 無效選擇 '{choice}'，保留目前設定 ({current_level})。")
        choice = default_num

    chosen_level = _NUM_TO_LEVEL[choice]

    if chosen_level != current_level:
        update_profile_config(prof, {"global": {"log_level": chosen_level}})

    apply_log_level(chosen_level)
    init_file_logger(prof)
    return chosen_level
