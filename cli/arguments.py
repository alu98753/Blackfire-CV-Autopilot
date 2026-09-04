"""Command-line argument contract for the application entry point."""

import argparse

from config import PRIMARY_MODES, SUBFLOW_CONFIGS


def parse_arguments():
    parser = argparse.ArgumentParser(description="Blackfire Crusade 副本與地下城自動掛機腳本")
    parser.add_argument("--title", type=str, default="Blackfire Crusade", help="遊戲視窗標題")
    parser.add_argument("--target", type=str, default=None,
                        help="指定控制的遊戲實例 (可傳入編號如 1, 2，別名 native, sandbox，或 HWND 如 0x2707a8)")
    parser.add_argument("--interval", type=float, default=0.5, help="畫面偵測間隔秒數 (預設: 0.5)")
    parser.add_argument("--mode", type=str, default="mix", choices=list(PRIMARY_MODES.keys()),
                        help="主掛機模式：mix (混合模式，預設)、dungeon (地下城)、stage (普通關卡)、golden_empire (黃金古國領地)、collect_only (純領取)")
    parser.add_argument("--subflow", nargs="+", choices=list(SUBFLOW_CONFIGS.keys()), default=None,
                        help="【Dev 單體測試專用】直接單獨或組合執行城鎮子流程 (如 --subflow blood_altar 或 --subflow jewelry_workshop)")
    parser.add_argument("--backend", action="store_true", help="啟用後台掛機模式 (不搶滑鼠，支援雙螢幕)")
    parser.add_argument("--monitor", "--screen", type=int, default=None,
                        help="指定全螢幕擷取/開遊戲的顯示器編號 (預設: 依據 Profile TOML [global.monitor_index] 設定)")
    parser.add_argument("--blessmode", type=str, default=None, choices=["combat", "life", "exp"],
                        help="地下城祝福模式：combat (戰鬥) 或 life (生命) 或 exp (經驗)")
    parser.add_argument("--boss", dest="enable_lord_boss", action=argparse.BooleanOptionalAction,
                        default=None, help="啟用/停用首領領主討伐 (lord_boss)")
    parser.add_argument("--dungeon", dest="enable_dungeon", action=argparse.BooleanOptionalAction,
                        default=None, help="啟用/停用地下城探索 (dungeon)")
    parser.add_argument("--stage", dest="enable_stage_farming", action=argparse.BooleanOptionalAction,
                        default=None, help="啟用/停用普通關卡打怪 (stage farming)")
    parser.add_argument("--town", dest="enable_town_daily", action=argparse.BooleanOptionalAction,
                        default=None, help="啟用/停用每日城鎮速領 (chest, hero, altar, jewelry)")
    parser.add_argument("--demon-lords", dest="enable_demon_lords", action=argparse.BooleanOptionalAction,
                        default=None, help="啟用/停用深淵魔王討伐 (demon lords)")
    parser.add_argument("--profile", type=str, default=None,
                        help="指定帳號配置名稱 (例如 native, sandbox, acc2)，將自動綁定 user_data/<profile>/ (包含專屬 config.toml 與 daily_status.json)")
    parser.add_argument(
        "--resume", action="store_true",
        help="Supervisor restart: reuse the selected profile and skip startup prompts.",
    )
    parser.add_argument(
        "--restart-game", action="store_true", default=False,
        help="強制關閉現有遊戲視窗並由 Steam 重新拉起遊戲 (用於定時維護或嚴重卡死自癒)",
    )
    parser.add_argument("--incident-session-id", type=str, default=None, help=argparse.SUPPRESS)
    return parser.parse_args()
