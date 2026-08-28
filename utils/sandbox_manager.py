"""Sandboxie-Plus 沙盒環境探測、箱體管理與專屬進程控制模組。"""

import os
import subprocess
import logging
from typing import Optional, List
from config import STEAM_APP_ID

logger = logging.getLogger(__name__)

DEFAULT_BOX_NAME = "New_Box"
FALLBACK_BOX_NAME = "DefaultBox"
SANDBOXIE_START_PATHS: List[str] = [
    r"C:\Program Files\Sandboxie-Plus\Start.exe",
    r"C:\Program Files\Sandboxie\Start.exe",
    r"C:\Program Files (x86)\Sandboxie\Start.exe",
]
SANDBOX_ROOT_DIR = r"C:\Sandbox"


DEFAULT_GAME_EXE_PATH = r"D:\Steam\steamapps\common\Blackfire Crusade\Blackfire Crusade.exe"


class SandboxManager:
    """提供 Sandboxie-Plus 沙盒之探測、箱體解析、啟動與進程隔離終止。"""

    def __init__(self, start_exe: Optional[str] = None, box_name: Optional[str] = None):
        self._start_exe = start_exe
        self._box_name = box_name

    @classmethod
    def is_sandbox_title(cls, title: Optional[str]) -> bool:
        """判定視窗標題是否包含 Sandboxie 隔離標籤 [#]...[#]。"""
        return bool(title and "[#]" in title)

    def get_start_exe(self) -> Optional[str]:
        """探測 Sandboxie Start.exe 實體路徑。"""
        if self._start_exe and os.path.exists(self._start_exe):
            return self._start_exe

        for path in SANDBOXIE_START_PATHS:
            if os.path.exists(path):
                self._start_exe = path
                return path
        return None

    def detect_active_box_name(self) -> str:
        """
        自動探測當前系統中最可能使用的活躍沙盒箱體名稱 (Box Name)。
        優先檢查 C:\\Sandbox\\<User>\\ 底下之資料夾，若無則退回預設 New_Box。
        """
        if self._box_name:
            return self._box_name

        try:
            if os.path.exists(SANDBOX_ROOT_DIR):
                for user_entry in os.scandir(SANDBOX_ROOT_DIR):
                    if user_entry.is_dir():
                        for box_entry in os.scandir(user_entry.path):
                            if box_entry.is_dir() and not box_entry.name.startswith("DONT-USE"):
                                self._box_name = box_entry.name
                                return self._box_name
        except Exception as e:
            logger.debug(f"探測活躍沙盒目錄失敗: {e}")

        self._box_name = DEFAULT_BOX_NAME
        return self._box_name

    def launch_steam_game(
        self,
        app_id: str = STEAM_APP_ID,
        game_exe: Optional[str] = None,
        box_name: Optional[str] = None
    ) -> bool:
        """
        於指定沙盒箱體內啟動遊戲。
        若遊戲 EXE 實體存在，優先於沙盒內直接執行 EXE (秒級啟動且自動掛接沙盒 Steam)；
        否則退回使用 steam:// 直連協定。
        """
        start_exe = self.get_start_exe()
        if not start_exe:
            logger.error("❌ 找不到 Sandboxie Start.exe，無法於沙盒內啟動 Steam 遊戲！")
            return False

        target_box = box_name or self.detect_active_box_name()
        target_exe = game_exe or DEFAULT_GAME_EXE_PATH

        if os.path.exists(target_exe):
            cmd = [start_exe, f"/box:{target_box}", target_exe]
            logger.info(f"🚀 [SandboxManager] 於沙盒 [{target_box}] 直接啟動遊戲 EXE: {' '.join(cmd)}")
        else:
            steam_url = f"steam://rungameid/{app_id}"
            cmd = [start_exe, f"/box:{target_box}", steam_url]
            logger.info(f"🚀 [SandboxManager] 於沙盒 [{target_box}] 發起 Steam 協定啟動: {' '.join(cmd)}")

        try:
            subprocess.Popen(cmd, shell=False)
            return True
        except Exception as e:
            logger.error(f"❌ 於沙盒內發起啟動失敗: {e}")
            return False

    def terminate_box(self, box_name: Optional[str] = None) -> bool:
        """
        透過 Sandboxie Start.exe /terminate 命令安全終止該沙盒箱體內所有進程。
        :param box_name: 指定沙盒箱體名稱
        :return: True 代表成功發送終止指令
        """
        start_exe = self.get_start_exe()
        if not start_exe:
            logger.warning("⚠️ 找不到 Sandboxie Start.exe，跳過沙盒終止指令。")
            return False

        target_box = box_name or self.detect_active_box_name()
        cmd = [start_exe, f"/box:{target_box}", "/terminate"]
        logger.info(f"💥 [SandboxManager] 終止沙盒 [{target_box}] 內所有進程: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, shell=False, capture_output=True, timeout=5.0)
            return True
        except Exception as e:
            logger.warning(f"⚠️ 終止沙盒箱體失敗: {e}")
            return False
