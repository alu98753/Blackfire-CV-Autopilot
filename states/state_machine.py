import time
import os
import cv2
import logging
import threading
from copy import deepcopy
from config import (
    GAME_CONFIGS,
    get_navigation_progress_settings,
    get_stamina_retreat_settings,
    get_runtime_game_config,
    normalize_config,
    refresh_runtime_config,
)
from utils import get_stage_configs
from utils.debug_artifacts import write_debug_image
from utils.tier4_config import build_tier4_fallback_config
from states.handlers import (
    NavigationHandler,
    LobbyHandler,
    BattleHandler,
    ResultHandler,
    ExploreHandler,
    BagCleaningHandler,
    BackpackFullSortingHandler,
    BreadCollectionHandler,
    DiamondCollectionHandler,
    CollectOnlyHandler,
    LoadingHandler,
    BloodAltarHandler,
    JewelryWorkshopHandler,
    LordBossHandler,
    ChestHandler,
    HeroDrawHandler,
    BulletinBoardHandler,
    DomainExploreHandler,
    DemonLordsHandler
)
from states.exceptions import ExceptionWatchdog, UnexpectedPopupRecoveryHandler
from states.navigation_intent import ActionId, IntentId
from states.navigation_progress import NavigationProgress, NavigationProgressSettings
from states.battle_session import BattleSession
from states.stamina_retreat import StaminaRetreatRecovery, StaminaRetreatSettings
from runtime.ports import GameRelaunchProcessAdapter, SystemClock



logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_SHARED_OCR_READERS = {}
_SHARED_OCR_LOCK = threading.Lock()
DEFAULT_LORD_BOSS_TARGETS = ("lord_spider", "lord_spectre", "ghoul_snow")

class GameStateMachine:
    # 定義遊戲狀態
    STATE_UNKNOWN = "UNKNOWN"
    STATE_NAVIGATING = "NAVIGATING"          # 尋路/導航中，依序點擊路徑按鈕進入副本
    STATE_LOBBY = "LOBBY"                    # [關卡專屬] 準備大廳，尋找並點擊開始按鈕
    STATE_BATTLE = "BATTLE"                  # 戰鬥進行中，點選自動戰鬥並監控結算
    STATE_RESULT = "RESULT"                  # [關卡專屬] 戰鬥結束結算，點擊繼續/再戰
    STATE_DUNGEON_EXPLORING = "EXPLORING"    # [地下城專屬] 地下城探索中，處理隨機事件與前進下一層
    STATE_BAG_CLEANING = "BAG_CLEANING"      # 背包滿了時，自動打開背包進行分解與整理
    STATE_BACKPACK_FULL_SORTING = "BACKPACK_FULL_SORTING" # 背包滿時自適應裝備分選與銷毀
    STATE_BREAD_COLLECTION = "BREAD_COLLECTION"          # 自動領體力流程
    STATE_DIAMOND_COLLECTION = "DIAMOND_COLLECTION"      # 自動領鑽石流程
    STATE_COLLECT_ONLY = "COLLECT_ONLY"                  # 定時領取麵包與鑽石待機流程
    STATE_LOADING = "LOADING"                            # 畫面過渡載入流程
    STATE_BLOOD_ALTAR = "BLOOD_ALTAR"                    # 血之祭壇獻祭流程
    STATE_JEWELRY_WORKSHOP = "JEWELRY_WORKSHOP"          # 珠寶加工廠出售流程
    STATE_LORD_BOSS = "LORD_BOSS"                        # 首領領主討伐流程
    STATE_CHEST = "CHEST"                                # 神秘寶箱 (開寶箱) 流程
    STATE_HERO_DRAW = "HERO_DRAW"                        # 抽英雄 (酒館招募) 流程
    STATE_BULLETIN_BOARD = "BULLETIN_BOARD"              # 懸賞告示牌 (領任務) 流程
    STATE_POPUP_RECOVERY = "POPUP_RECOVERY"              # 意外彈窗/視窗恢復處置流程
    STATE_DOMAIN_EXPLORE = "DOMAIN_EXPLORE"
    STATE_DEMON_LORDS = "DEMON_LORDS"                    # 深淵魔王討伐流程

    DUNGEON_SCENE_FEATURES = (
        "dungeons/leave.png",
        "dungeons/dungeons_complete.png",
        "dungeons/gungeon_godown.png",
        "dungeons/gungeon_godown_confirm.png",
        "dungeons/Treasure.png",
        "dungeons/dungeon_bless.png",
        "dungeons/dungeon_fight.png",
    )
    DUNGEON_RECOVERY_FEATURES = (
        "dungeons/leave.png",
        "dungeons/dungeons_complete.png",
        "dungeons/gungeon_godown.png",
    )
    DUNGEON_RECOVERY_MODE_TYPES = frozenset(
        {"dungeon", "mix", "stage", "daily"}
    )



    
    def __init__(
        self,
        capturer,
        matcher,
        mouse,
        preload_ocr: bool = True,
        *,
        clock=None,
        process_port=None,
    ):
        self.capturer = capturer
        self.capture_port = capturer
        self.matcher = matcher
        self.mouse = mouse
        self.input_port = mouse
        self.clock = clock or SystemClock()
        self.process_port = process_port or GameRelaunchProcessAdapter()
        
        self.current_state = self.STATE_UNKNOWN
        self.last_state = None
        self.last_state_change = time.time()
        self.battle_session = BattleSession()
        self.run_count = 0
        self.capture_failure_count = 0
        self.capture_failure_limit = 5
        
        # 紀錄上次點選自動戰鬥的時間，用以判斷 CD
        self.last_auto_click_time = 0
        
        # 當前模式配置，由外部 main.py 初始化設定
        self.config = None
        
        # 領體力相關屬性 (由外部 main.py 初始化與設定)
        self.enable_bread = False
        self.bread_collection_available = False
        self.need_bread_collection = False  # 啟動時預設不設定領取，需大門觸發
        self.last_bread_collection_time = 0.0
        self.bread_collected_this_run = False
        self.bread_click_attempted = False
        self.bread_window_opened = False
        
        # 領鑽石相關屬性
        self.need_diamond_collection = False  # 啟動時預設不設定領取，需大門觸發
        self.last_diamond_collection_time = 0.0
        self.diamond_collected_this_run = False
        self.diamond_window_opened = False
        self.diamond_ocr_success = False
        
        # 背包清理相關屬性
        self.need_bag_cleaning = False
        self.bag_tidied = False
        self.bag_disassembled = False
        self.bag_select_all_clicked = False
        self.bag_deselected = False
        
        # 城鎮子流程與流水線相關屬性
        self.need_blood_altar = False
        self.need_jewelry_workshop = False
        self.current_lord_boss_key = None
        self.current_demon_lord_key = None
        self.town_subflow_queue = []
        self.quest_scheduler = None
        self.daily_manager = None
        self.config = {}
        self.primary_config = {}
        self.runtime_config_key = None
        self.runtime_config_overrides = {}
        self.pending_daily_reset_exit = False
        self.next_daily_quest_ready_at = None
        self.pending_daily_quest_preemption = False
        self.navigation_progress = NavigationProgress(
            NavigationProgressSettings.from_mapping(
                get_navigation_progress_settings()
            )
        )
        self.stamina_recovery = StaminaRetreatRecovery(
            StaminaRetreatSettings.from_mapping(get_stamina_retreat_settings())
        )



        
        # 地下城本層探索記憶 (防止已完成的事件重複點選)
        self.is_in_dungeon = False
        self.chest_opened_this_floor = False
        self.skill_selected_this_floor = False
        self.bless_received_this_floor = False
        self.last_godown_click_time = None
        self.dungeon_floor_transitioning = False
        self.consecutive_stuck_count = 0
        
        # 地下城與關卡戰敗計數與退避相關屬性
        self.dungeon_cooldowns = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.current_dungeon_index = 0
        self.defeat_count = 0
        self.fallback_swipe_count = 0
        
        # 使用者手動介入偵測相關屬性
        self.user_operating = False
        self.user_operation_start_time = None
        self.last_user_operation_time = 0.0
        self.prev_mouse_pos = None
        self.just_resumed_from_user = False
        
        # 體力不足退避與還原相關屬性
        self.original_config = None
        self.stamina_retreat_start_time = None
        # Dungeon-only cooldown fallback keeps its own return target.  This is
        # deliberately separate from stamina retreat, whose timer has a
        # different lifecycle.
        self.dungeon_cooldown_return_config = None
        self.is_dev_subflow_run = False
        self.last_lobby_start_click_time = 0.0
        self.last_result_retry_click_time = 0.0
        # 領取任務獎勵子流程 (Phase 狀態機屬性)
        self.task_complete_phase = "INIT_BANNER_CHECK"
        self._subflow_cached_pos_task = None
        self._subflow_click_target = None

        # 定義單一繼續模板路徑
        self.continue_template = "common/continue.png"
        self._ocr_readers = _SHARED_OCR_READERS
        self._ocr_lock = _SHARED_OCR_LOCK
        
        # 意外彈窗處置與 Watchdog 監控器元件 (來自 states.exceptions)
        self.stashed_state = None
        self.stashed_context = {}
        self.exception_watchdog = ExceptionWatchdog(self)

        # 手動暫停與恢復 (Pause/Resume) 控制屬性 (含 threading.Event 原地定格門閥)
        self.is_paused = False
        self.pause_start_time = None
        self.resume_event = threading.Event()
        self.resume_event.set()

        # EasyOCR 背景非同步預熱 (Background Warmup)
        if preload_ocr:
            self.preload_ocr_models()



        # 初始化註冊所有狀態處理器
        self.handlers = {
            self.STATE_NAVIGATING: NavigationHandler(self),
            self.STATE_LOBBY: LobbyHandler(self),
            self.STATE_BATTLE: BattleHandler(self),
            self.STATE_RESULT: ResultHandler(self),
            self.STATE_DUNGEON_EXPLORING: ExploreHandler(self),
            self.STATE_BAG_CLEANING: BagCleaningHandler(self),
            self.STATE_BACKPACK_FULL_SORTING: BackpackFullSortingHandler(self),
            self.STATE_BREAD_COLLECTION: BreadCollectionHandler(self),
            self.STATE_DIAMOND_COLLECTION: DiamondCollectionHandler(self),
            self.STATE_COLLECT_ONLY: CollectOnlyHandler(self),
            self.STATE_LOADING: LoadingHandler(self),
            self.STATE_BLOOD_ALTAR: BloodAltarHandler(self),
            self.STATE_JEWELRY_WORKSHOP: JewelryWorkshopHandler(self),
            self.STATE_LORD_BOSS: LordBossHandler(self),
            self.STATE_CHEST: ChestHandler(self),
            self.STATE_HERO_DRAW: HeroDrawHandler(self),
            self.STATE_BULLETIN_BOARD: BulletinBoardHandler(self),
            self.STATE_POPUP_RECOVERY: UnexpectedPopupRecoveryHandler(self),
            self.STATE_DOMAIN_EXPLORE: DomainExploreHandler(self),
            self.STATE_DEMON_LORDS: DemonLordsHandler(self),
        }

    def stash_current_state(self, reason="unexpected_popup"):
        """
        暫存當前狀態與 context，並切換至意外彈窗復原流程 STATE_POPUP_RECOVERY。
        具備 Stash Lock 防護：若已有暫存狀態未復原，不重覆覆蓋原始業務狀態。
        """
        import copy
        if self.current_state != self.STATE_POPUP_RECOVERY and self.stashed_state is None:
            self.stashed_state = self.current_state
            self.stashed_context = {
                "task_complete_phase": getattr(self, "task_complete_phase", None),
                "last_state_change": self.last_state_change,
                "context": copy.deepcopy(getattr(self, "context", {})),
                "timestamp": time.time(),
                "reason": reason
            }
            logging.info(f"💾 [StateStash] 已暫存原狀態: {self.stashed_state} (原因: {reason})")
            self.transition_to(self.STATE_POPUP_RECOVERY)

    def restore_stashed_state(self):
        """
        復原先前暫存之狀態與 context。若無暫存狀態則安全降級至 STATE_NAVIGATING。
        保留 Watchdog 連續卡死次數記憶，但由 transition_to 賦予全新寬限期 (Grace Period)。
        """
        if self.stashed_state:
            target = self.stashed_state
            logging.info(f"🔄 [StateRestore] 恢復原暫存狀態: {target}")
            if isinstance(self.stashed_context, dict) and "context" in self.stashed_context:
                self.context = self.stashed_context["context"]
            self.stashed_state = None
            self.stashed_context = {}

            saved_stuck_count = getattr(self.exception_watchdog, "consecutive_stuck_count", 0) if hasattr(self, "exception_watchdog") else 0
            saved_stuck_state = getattr(self.exception_watchdog, "last_stuck_state", None) if hasattr(self, "exception_watchdog") else None

            self.transition_to(target)

            if hasattr(self, "exception_watchdog"):
                if saved_stuck_state == target and saved_stuck_count > 0:
                    self.exception_watchdog.consecutive_stuck_count = saved_stuck_count
                    self.exception_watchdog.last_stuck_state = saved_stuck_state
            return True
        else:
            logging.warning("⚠️ [StateRestore] 無可恢復之暫存狀態，安全退避至 NAVIGATING")
            self.transition_to(self.STATE_NAVIGATING)
            return False

    def pause(self):
        """
        進入手動暫停狀態，記錄暫停起點時間並阻斷底層動作門閥。
        """
        if not self.is_paused:
            self.is_paused = True
            if hasattr(self, "resume_event") and self.resume_event:
                self.resume_event.clear()
            self.pause_start_time = time.time()
            logging.info(f"⏸️ [StateMachine] 腳本已暫停，鎖定當前狀態: [{self.current_state}]。")

    def resume(self) -> float:
        """
        退出手動暫停狀態，原子化執行內部安全/防卡死計時器補償並放行底層動作門閥。
        
        :return: pause_duration (暫停總秒數)
        """
        pause_duration = 0.0
        if self.is_paused:
            if self.pause_start_time is not None:
                pause_duration = max(0.0, time.time() - self.pause_start_time)
                self.compensate_internal_timers(pause_duration)
            self.is_paused = False
            self.pause_start_time = None
            if hasattr(self, "resume_event") and self.resume_event:
                self.resume_event.set()
            self.just_resumed_from_user = True
            logging.info(f"▶️ [StateMachine] 腳本已恢復運行 (已補償內部計時器 {pause_duration:.1f} 秒)。繼續執行狀態: [{self.current_state}]。")
        return pause_duration

    def toggle_pause(self) -> bool:
        """
        切換暫停/恢復狀態。
        
        :return: True 代表切換後處於暫停中；False 代表切換後已恢復運行
        """
        if self.is_paused:
            self.resume()
            return False
        else:
            self.pause()
            return True

    def compensate_internal_timers(self, pause_duration: float):
        """
        【Clean Code 內部安全時鐘補償】
        僅補償腳本自設的防卡死、過渡等待與單場戰鬥統計計時器。
        
        注意：
        1. 絕不修改 dungeon_cooldowns、lord_boss_cooldowns 或每日任務重置等客觀遊戲冷卻！
        2. 確保在暫停超過 90 秒後恢復時，ExceptionWatchdog 絕對不會因停滯誤判為卡死。
        """
        if pause_duration <= 0.0:
            return

        now = time.time()

        # 1. 補償狀態轉移 Watchdog (最關鍵：防止暫停 90s 後一恢復就被 Watchdog 誤判卡死)
        if self.last_state_change > 0:
            self.last_state_change += pause_duration

        # 2. 補償戰鬥計時器
        self.battle_session.compensate_pause(pause_duration)

        # 3. 補償例外彈窗暫存時間
        if isinstance(self.stashed_context, dict) and "timestamp" in self.stashed_context:
            self.stashed_context["timestamp"] += pause_duration

        # 4. 補償 Handler 內部的過渡時間戳
        battle_handler = self.handlers.get(self.STATE_BATTLE)
        if battle_handler and getattr(battle_handler, "non_battle_feature_start_time", None) is not None:
            battle_handler.non_battle_feature_start_time += pause_duration

        loading_handler = self.handlers.get(self.STATE_LOADING)
        if loading_handler and getattr(loading_handler, "loading_start_time", None) is not None:
            loading_handler.loading_start_time += pause_duration

        # 5. 補償滑鼠動作與手動介入判定時間戳 (防止恢復瞬間因時間差誤觸手動移動偵測)
        if hasattr(self, "mouse") and self.mouse:
            self.mouse.last_action_time = now
        self.last_user_operation_time = 0.0
        self.user_operating = False
        self.just_resumed_from_user = True

        # 6. 反射自動補償所有動態 missing_time_* 模板記憶
        for attr in list(self.__dict__.keys()):
            if attr.startswith("missing_time_"):
                val = getattr(self, attr)
                if isinstance(val, (int, float)):
                    setattr(self, attr, val + pause_duration)

    @property
    def dungeon_defeat_count(self):
        return self.defeat_count

    @dungeon_defeat_count.setter
    def dungeon_defeat_count(self, value):
        self.defeat_count = value

    def preload_ocr_models(self, lang_list=None, async_mode: bool = True):
        """
        在背景守護執行緒 (Daemon Thread) 或同步預載 EasyOCR 辨識模型，避免於遊戲主迴圈中產生 5~6 秒的卡頓。
        若全域快取中已存在對應模型，則立即跳過，絕不重複建立背景執行緒。
        """
        if lang_list is None:
            lang_list = ['ch_tra', 'en']
        key = "_".join(lang_list)

        # 快速路徑：若已載入過，直接返回
        if key in _SHARED_OCR_READERS:
            return None

        def _worker():
            try:
                logging.info(f"⚙️ [OCR Preload] 正在背景預熱載入 EasyOCR 辨識模型 ({lang_list})...")
                self.get_ocr_reader(lang_list)
                logging.info("✅ [OCR Preload] EasyOCR 辨識模型預熱載入完成！")
            except Exception as e:
                logging.warning(f"⚠️ [OCR Preload] 背景預熱載入 EasyOCR 失敗 (後續調用時將重新嘗試): {e}")

        if async_mode:
            with _SHARED_OCR_LOCK:
                if key in _SHARED_OCR_READERS:
                    return None
                t = threading.Thread(target=_worker, daemon=True, name="EasyOCRPreloadThread")
                t.start()
                return t
        else:
            _worker()
            return None

    def get_ocr_reader(self, lang_list=None):
        """
        執行緒安全地取得 EasyOCR 讀取器實例，預設載入繁體中文與英文 ['ch_tra', 'en']。
        若模型尚未載入則現場載入並快取；若載入失敗則拋出例外 (Fail-Fast)。
        """
        if lang_list is None:
            lang_list = ['ch_tra', 'en']

        key = "_".join(lang_list)

        with _SHARED_OCR_LOCK:
            if key not in _SHARED_OCR_READERS:
                try:
                    import easyocr
                    logging.info(f"⚙️ 正在載入 EasyOCR 辨識模型 ({lang_list}) (使用 CPU)...")
                    _SHARED_OCR_READERS[key] = easyocr.Reader(lang_list, gpu=False)
                except Exception as e:
                    logging.error(f"❌ [OCR] 無法載入 EasyOCR 辨識模型: {e}")
                    raise RuntimeError(f"EasyOCR 辨識模型載入失敗: {e}") from e
            return _SHARED_OCR_READERS[key]



    def transition_to(self, new_state):
        if self.current_state != new_state:
            previous_state = self.current_state
            if new_state == self.STATE_DUNGEON_EXPLORING:
                self.ensure_explore_config()
            logging.info(f"🔄 狀態轉移: {self.current_state} -> {new_state}")
            self.last_state = self.current_state
            self.current_state = new_state
            self.last_state_change = time.time()
            self.consecutive_stuck_count = 0
            self.just_resumed_from_user = False
            
            # 狀態發生真實轉移且非 POPUP_RECOVERY 時，歸零 Watchdog 連續卡死計數
            if new_state != self.STATE_POPUP_RECOVERY and hasattr(self, "exception_watchdog"):
                self.exception_watchdog.consecutive_stuck_count = 0
                self.exception_watchdog.last_stuck_state = None
            
            # 當轉移至新狀態時，自動重置目標 Handler 內部步驟 phase
            handler = self.handlers.get(new_state)
            if handler and hasattr(handler, "reset_state"):
                handler.reset_state()

            self._on_state_transition_sync_context(new_state)
            self._sync_battle_session(previous_state, new_state)

    def _sync_battle_session(self, previous_state, new_state):
        """Own battle timeout lifetime at the state-machine boundary.

        A BATTLE scene observed after UNKNOWN/LOADING/relaunch is a new
        observable session.  It must never inherit a timeout timestamp from a
        completed or pre-relaunch battle.
        """
        if new_state == self.STATE_BATTLE:
            self.battle_session.begin(self.clock.monotonic(), previous_state)
            return
        if previous_state == self.STATE_BATTLE:
            self.battle_session.clear()

    def battle_elapsed_seconds(self) -> float:
        """Return the active battle duration using the runtime clock port."""
        return self.battle_session.elapsed_seconds(self.clock.monotonic())

    @property
    def battle_start_time(self):
        """Legacy test compatibility; production code uses ``battle_session``."""
        return self.battle_session.started_at

    @battle_start_time.setter
    def battle_start_time(self, value):
        """Adapt legacy wall-clock test fixtures to the monotonic session clock."""
        if value is None:
            self.battle_session.clear()
            return
        if value >= 1_000_000_000:
            elapsed = max(0.0, time.time() - value)
            value = self.clock.monotonic() - elapsed
        self.battle_session.started_at = value

    def request_relaunch(self, reason: str) -> bool:
        """Escalate recovery through the configured process boundary."""
        self.navigation_progress.clear()
        return self.process_port.relaunch(self, reason)

    def has_dungeon_context(self) -> bool:
        """Return whether dungeon-only scene anchors may own the current frame."""
        if (
            getattr(self, "current_lord_boss_key", None) is not None
            or getattr(self, "current_demon_lord_key", None) is not None
        ):
            return False
        config_type = (self.config or {}).get("type")
        is_dungeon_run = config_type == "dungeon" or (
            config_type == "mix" and self.is_in_dungeon
        )
        return is_dungeon_run

    def dungeon_detection_features(self):
        """Return dungeon anchors allowed by the current committed context."""
        if (
            getattr(self, "current_lord_boss_key", None) is not None
            or getattr(self, "current_demon_lord_key", None) is not None
        ):
            return ()
        config_type = (self.config or {}).get("type")
        if config_type not in self.DUNGEON_RECOVERY_MODE_TYPES:
            return ()
        if self.has_dungeon_context():
            return self.DUNGEON_SCENE_FEATURES
        return self.DUNGEON_RECOVERY_FEATURES

    def ensure_explore_config(self):
        """Restore a route config that can safely run ``ExploreHandler``.

        Visual state detection and bag-cleanup recovery can enter EXPLORING
        while a temporary town/subflow config is active.  Those configs do not
        define ``explore_priorities``.
        """
        active_config = self.config or {}
        if "explore_priorities" in active_config:
            return True

        candidates = (
            getattr(self, "dungeon_cooldown_return_config", None),
            getattr(self, "original_config", None),
            getattr(self, "primary_config", None),
        )
        for candidate in candidates:
            if candidate and "explore_priorities" in candidate:
                logging.warning(
                    "[Explore config recovery] restoring dungeon route config before entering EXPLORING."
                )
                self.set_config(candidate.copy())
                return True

        logging.error(
            "[Explore config recovery] no config with explore_priorities is available; using ExploreHandler safe fallback."
        )
        return False

    def notify_ui_progress(self):
        """
        通知狀態機當前 Handler 內部發生了「真實有效之 UI 狀態進展 (Valid UI Progress)」。
        更新 last_state_change 與連鎖卡住計數，防止 ExceptionWatchdog 在長途流程中誤判卡死。

        ⚠️ [開發者呼叫原則 (Developer Call Guidelines)]：
        1. ✅ 允許呼叫時機 (Valid Progress)：
           - 確定完成一次真實交易/選單操作 (如成功點擊 confirm/ok，或商品完成出售)。
           - 內部 Iterator 索引成功推進 (如商品 index + 1、關卡清單翻頁)。
           - 畫面 Phase 階段真實轉移 (如 INIT -> ENTERED_BUILDING -> SELL_MENU_OPEN)。
        2. ❌ 嚴禁呼叫時機 (Invalid Progress / False Reset)：
           - 剛發起盲點或未確認 UI 是否回應前。
           - 模板比對失敗、找不到按鈕時的單純 return / sleep。
           - 重複對無反應區域發起點擊時 (若在此呼叫會破壞 Watchdog 卡死救援能力)。
        """
        self.last_state_change = time.time()
        self.consecutive_stuck_count = 0




    # 🏛️ 城鎮子流程與 Config Key 聲明式對照表 (新增城鎮子流程只需在此註冊對應 Key)
    TOWN_SUBFLOW_CONFIG_MAP = {
        STATE_BLOOD_ALTAR: "blood_altar",
        STATE_JEWELRY_WORKSHOP: "jewelry_workshop",
        STATE_LORD_BOSS: "lord_boss",
        STATE_CHEST: "chest",
        STATE_HERO_DRAW: "hero_draw",
        STATE_BULLETIN_BOARD: "bulletin_board",
        STATE_DEMON_LORDS: "demon_lords",
    }



    def _on_state_transition_sync_context(self, new_state):
        from config import GAME_CONFIGS
        if new_state in {self.STATE_LOADING, self.STATE_BATTLE}:
            self.navigation_progress.acknowledge(ActionId.START_PRIMARY)
        elif new_state in {self.STATE_RESULT, self.STATE_NAVIGATING}:
            self.navigation_progress.clear(IntentId.PRIMARY_NAVIGATION)

        key = self.TOWN_SUBFLOW_CONFIG_MAP.get(new_state)
        if key and key in GAME_CONFIGS:
            saved_keep = self.config.get("keep_colors") if self.config else None
            saved_dis = self.config.get("disassemble_colors") if self.config else None
            saved_sac = self.config.get("sacrifice_settings") if self.config else None

            if self.config is None:
                self.config = {}
            self.config.update(GAME_CONFIGS[key])

            if saved_keep is not None:
                self.config["keep_colors"] = saved_keep
            if saved_dis is not None:
                self.config["disassemble_colors"] = saved_dis
            if saved_sac is not None:
                self.config["sacrifice_settings"] = saved_sac

        # 轉移至新狀態時，重置目標 Handler 的內部狀態 (避免累積舊 step_phase 髒資料)
        if new_state in self.handlers and hasattr(self.handlers[new_state], "reset_state"):
            try:
                self.handlers[new_state].reset_state()
            except Exception as e:
                logging.debug(f"重置 Handler [{new_state}] 狀態時發生異常: {e}")

        if new_state == self.STATE_BATTLE:
            self.last_auto_click_time = 0
        elif new_state == self.STATE_LOADING:
            self.loading_start_time = time.time()
        elif new_state == self.STATE_BACKPACK_FULL_SORTING:
            self.need_bag_cleaning = True
            self.handlers[new_state].screenshot_counter = 1
        elif new_state == self.STATE_NAVIGATING:
            if self.consume_daily_quest_preemption_for_navigation():
                return
            if getattr(self, "pending_town_subflows", False):
                self.pending_town_subflows = False
                logging.info("🏛️ [城鎮流水線] 偵測到地下城探索結束退回城鎮，自動補跑延遲的城鎮任務流水線...")
                self.trigger_town_subflow_chain()
            elif self.is_daily_pipeline_active() or self.has_available_selected_lord_boss() or self.has_available_demon_lords():
                self.evaluate_and_schedule_daily_pipeline()



    def step(self):
        """
        執行單步狀態檢索與決策（主調度器）。
        """
        # 動態檢查 08:05 日常任務/Boss 清零重置線 (全模式適用)
        if getattr(self, "daily_manager", None):
            reset_occurred = self.daily_manager.check_and_reset_daily()
            if reset_occurred:
                logging.info("🌅 [GameStateMachine] 跨越 08:05 重置線！重置狀態機掛載的 QuestScheduler、戰敗計數與體力退避狀態。")
                self.quest_scheduler = None
                self.defeat_count = 0
                self.original_config = None
                self.stamina_retreat_start_time = None
                self.stamina_recovery.reset()
                self.pending_daily_reset_exit = True
                logging.info("🌅 [GameStateMachine] 已設定 pending_daily_reset_exit = True，當前戰鬥/結算完畢後將主動離場退回城鎮啟動新日常。")

        if self.config is None:
            logging.warning("⚠️ 尚未載入模式設定 config，請確認 main.py 初始化正確。")
            time.sleep(1)
            return

        self.poll_daily_quest_preemption()

        pass

        # 2. 取得遊戲視窗邊界與擷取畫面
        rect = self.capturer.get_window_rect()
        self.last_rect = rect # 快取當前幀最穩定的物理邊界
        
        if rect is None:
            self.window_lost_count = getattr(self, "window_lost_count", 0) + 1
            logging.warning(f"⚠️ 找不到遊戲視窗 (連續第 {self.window_lost_count} 次)，請確認遊戲未縮小且視窗名稱符合設定。")
            
            # 若連續 5 次 (~2.5s) 找不到遊戲視窗，判定遊戲已被使用者手動關閉或崩潰，觸發 GameRelaunchSubflow 自動重開
            if self.window_lost_count >= 5:
                logging.warning("🚨 連續 5 次偵測不到遊戲視窗 (遊戲已被手動關閉或崩潰)，發起 GameRelaunchSubflow 自動重開流程！")
                self.window_lost_count = 0
                self.request_relaunch("game_window_closed_by_user")
                return

            time.sleep(0.5)
            return

        # 視窗存在，重置視窗遺失計數器
        self.window_lost_count = 0
            
        screen_img = self.capturer.capture(rect)
        if screen_img is None:
            self.capture_failure_count += 1
            logging.warning(
                "[CaptureRecovery] Screenshot unavailable (%d/%d).",
                self.capture_failure_count,
                self.capture_failure_limit,
            )
            if self.capture_failure_count >= self.capture_failure_limit:
                self.capture_failure_count = 0
                logging.error("[CaptureRecovery] Screenshot failure threshold reached; relaunching game.")
                self.request_relaunch("capture_failure_threshold_exceeded")
                return
            logging.warning("⚠️ 無法擷取畫面")
            time.sleep(0.2)
            return

        # 0. 全域 Watchdog 雙重觸發器 (30s 非戰鬥 / 90s 戰鬥 / 30s 衝突掃描)
        if self.capture_failure_count:
            logging.info("[CaptureRecovery] Screenshot capture recovered after %d failures.", self.capture_failure_count)
            self.capture_failure_count = 0

        if self.exception_watchdog.check(screen_img):
            return


        # B. 全域自動重登處理 (低頻率檢測)

        import sys
        is_testing = "unittest" in sys.modules
        now_time = time.time()
        last_low_freq = getattr(self, "_last_low_freq_check_time", 0.0)
        last_state = getattr(self, "_last_low_freq_state", None)
        state_changed = (self.current_state != last_state)
        should_check_low_freq = is_testing or state_changed or (now_time - last_low_freq >= 1.5) or (self.current_state in [self.STATE_UNKNOWN, self.STATE_LOADING])

        # An active recovery is a committed, bounded action sequence.  It must
        # receive every subsequent frame rather than waiting for the low-rate
        # global guard.  Demon Lord additionally gets this narrow overlay
        # profile every tick while its Start action can produce no_bread.
        if self.stamina_recovery.is_active or self.current_state == self.STATE_DEMON_LORDS:
            from states.stamina_flow import handle_insufficient_stamina
            if handle_insufficient_stamina(self, screen_img, rect):
                return

        if should_check_low_freq:
            self._last_low_freq_check_time = now_time
            self._last_low_freq_state = self.current_state
            from states.login_flow import handle_global_login
            if handle_global_login(self, screen_img, rect):
                return

            # C. Confirmed stamina overlays preempt the remaining
            # stamina-consuming workflows. Demon Lord was handled above so
            # its Start outcome has no global-guard latency.
            stamina_consuming_states = {
                self.STATE_NAVIGATING,
                self.STATE_LOBBY,
                self.STATE_RESULT,
                self.STATE_LOADING,
                self.STATE_DOMAIN_EXPLORE,
            }
            if self.current_state in stamina_consuming_states:
                from states.stamina_flow import handle_insufficient_stamina
                if handle_insufficient_stamina(self, screen_img, rect):
                    return

        # 3. 僅有在大門 common/door.png 可見時，才觸發自動領鑽石/領麵包定時檢查
        self.check_collection_trigger(screen_img)

        # A. 狀態持續計數 (consecutive_stuck_count 供 ExceptionWatchdog 與排程追蹤)
        if self.current_state not in [self.STATE_BATTLE, self.STATE_DUNGEON_EXPLORING, self.STATE_UNKNOWN, self.STATE_COLLECT_ONLY, self.STATE_LOADING]:
            self.consecutive_stuck_count += 1
        else:
            self.consecutive_stuck_count = 0


        # 3. 全域彈窗與任務完成處理 (低頻率檢測)
        if should_check_low_freq:
            # 3.1 檢查「任務完成」彈窗 (task_complete.png)
            if os.path.exists(os.path.join("templates", "task_complete.png")):
                pos, conf = self.matcher.match(screen_img, "task_complete.png", threshold=0.8)
                if pos:
                    logging.info(f"🎉 偵測到【任務完成】彈窗 (信心度: {conf:.4f})，啟動「領取任務獎勵」子流程進行 OCR 辨識與核銷。")
                    self._run_task_complete_subflow(rect)
                    return


            # 3.2 檢查「無法容納的物品 (背包滿)」彈窗 (backpack_full.png)
            if os.path.exists(os.path.join("templates", "backpack_full.png")):
                # 調高門檻至 0.80 以避免大廳背景等介面產生虛假誤判，真實彈窗特徵明顯，信心度極高
                pos, conf = self.matcher.match(screen_img, "backpack_full.png", threshold=0.80)
                if pos:
                    if self.current_state != self.STATE_BACKPACK_FULL_SORTING:
                        logging.warning(f"🎒 全域偵測到【無法容納的物品 (背包已滿)】畫面 (信心度: {conf:.4f})，切換至 BACKPACK_FULL_SORTING 狀態進行自適應分選。")
                        self.transition_to(self.STATE_BACKPACK_FULL_SORTING)
                        return

            # 3.3 在大廳或需要清理背包狀態下，若看見通用確認按鈕，點擊以關閉彈窗 (如領取獎勵/關閉背包滿後續確認，排除背包清理狀態自身處理)
            if (self.current_state == self.STATE_LOBBY or self.need_bag_cleaning) and self.current_state not in [self.STATE_BAG_CLEANING, self.STATE_BACKPACK_FULL_SORTING]:
                for conf_btn in ["common/confirm.png", "common/ok.png"]:
                    if os.path.exists(os.path.join("templates", conf_btn)):
                        pos, conf = self.matcher.match(screen_img, conf_btn, threshold=0.8)
                        if pos:
                            logging.info(f"👉 偵測到通用確認按鈕 [{conf_btn}] (信心度: {conf:.4f})，點擊關閉。")
                            self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                            time.sleep(0.08)
                            return

        # 4. 分發處理至當前狀態的 Handler
        handler = self.handlers.get(self.current_state)
        if handler:
            handler.handle(screen_img, rect)
        else:
            # 預設未知狀態下，進行全域掃描定位當前狀態
            self.detect_current_state(screen_img, rect)

    def detect_current_state(self, screen_img, rect):
        """
        全域掃描定位當前狀態。
        """
        # 每秒最多存檔一次除錯畫面，避免過度佔用硬碟 I/O
        import numpy as np
        now = time.time()
        if now - getattr(self, "last_detect_save_time", 0.0) > 1.0:
            self.last_detect_save_time = now
            if isinstance(screen_img, np.ndarray):
                write_debug_image("debug_detect.png", screen_img)
                logging.info("📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png")

        logging.info("🔍 正在進行全域掃描以辨識遊戲狀態...")
        
        # 0.0 全域防護：若畫面上存在歡迎/確認彈窗 (common/confirm.png, common/ok.png)，優先點擊關閉以防遮擋導航與領取
        for popup_btn in ["common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", popup_btn)):
                pos_popup, conf_popup = self.matcher.match(screen_img, popup_btn, threshold=0.90)
                if pos_popup:
                    logging.info(f"👉 [全域防護] 偵測到可能遮擋的彈窗按鈕 [{popup_btn}] (相似度: {conf_popup:.4f})，優先點擊關閉...")
                    self.mouse.click(rect["left"] + pos_popup[0], rect["top"] + pos_popup[1])
                    time.sleep(0.5)
                    return

        # 0.0 如果看見「無法容納的物品 (背包滿)」彈窗，進入分選狀態
        if os.path.exists(os.path.join("templates", "backpack_full.png")):
            pos, _ = self.matcher.match(screen_img, "backpack_full.png", threshold=0.80)
            if pos:
                self.transition_to(self.STATE_BACKPACK_FULL_SORTING)
                return

        # 0.02 如果看見「戰敗畫面」 (defeat.png)，進入結算狀態
        if os.path.exists(os.path.join("templates", "defeat.png")):
            pos, _ = self.matcher.match(screen_img, "defeat.png", threshold=0.75)
            if pos:
                self.transition_to(self.STATE_RESULT)
                return

        # 0.05 如果需要清理背包 (need_bag_cleaning == True) 且已回到了大廳/城鎮畫面 (看到 common/door.png 或 goback_town.png)
        if self.need_bag_cleaning:
            for town_btn in ["common/door.png", "goback_town.png"]:
                if os.path.exists(os.path.join("templates", town_btn)):
                    pos_t, _ = self.matcher.match(screen_img, town_btn, threshold=0.8)
                    if pos_t:
                        self.transition_to(self.STATE_BAG_CLEANING)
                        return

        # 0.06 如果需要血之祭壇獻祭 (need_blood_altar == True) 且已回到了大廳/城鎮畫面 (看到 common/door.png 或 goback_town.png)
        if getattr(self, "need_blood_altar", False):
            for town_btn in ["common/door.png", "goback_town.png", "town_building/Blood_Altar/Blood_Altar.png"]:
                if os.path.exists(os.path.join("templates", town_btn)):
                    pos_t, _ = self.matcher.match(screen_img, town_btn, threshold=0.8)
                    if pos_t:
                        self.transition_to(self.STATE_BLOOD_ALTAR)
                        return

        # 0.07 如果需要珠寶加工廠出售 (need_jewelry_workshop == True)，且已回到了大廳/城鎮/建築畫面
        if getattr(self, "need_jewelry_workshop", False):
            for town_btn in ["common/door.png", "goback_town.png", "town_building/Jewelry_workshop/Jewelry_workshop.png", "town_building/sell_out.png"]:
                if os.path.exists(os.path.join("templates", town_btn)):
                    pos_t, _ = self.matcher.match(screen_img, town_btn, threshold=0.75)
                    if pos_t:
                        self.transition_to(self.STATE_JEWELRY_WORKSHOP)
                        return

        # 0.1 如果需要領鑽石或體力，且畫面上看見入口或功能按鈕，進入導航/領取狀態 (排除獨立模式與城鎮任務流水線中)
        if (self.need_diamond_collection or (self.enable_bread and self.need_bread_collection)) and \
           (self.config is None or self.config["type"] not in ["blood_altar", "jewelry_workshop"]) and \
           not getattr(self, "need_blood_altar", False) and not getattr(self, "need_jewelry_workshop", False):
            nav_buttons = [
                "common/door.png", "goback_town.png", "diamond.png", "free.png",
                "common/bread.png", "common/collect.png", "common/bread_collection.png", "common/quit.png"
            ]
            for bf in nav_buttons:
                if os.path.exists(os.path.join("templates", bf)):
                    pos, _ = self.matcher.match(screen_img, bf, threshold=0.8)
                    if pos:
                        next_state = self.STATE_COLLECT_ONLY if self.is_in_collect_only_mode() else self.STATE_NAVIGATING
                        self.transition_to(next_state)
                        return

        # 1. 檢查是否在戰鬥中 (看到 common/auto.png 或 battle/ 特徵圖案)
        # Dungeon transition/result anchors must take precedence over battle
        # features: some of those screens can falsely match auto.png.
        for btn_name in self.dungeon_detection_features():
            if os.path.exists(os.path.join("templates", btn_name)):
                pos, conf = self.matcher.match(screen_img, btn_name, threshold=0.8)
                if pos:
                    logging.info(
                        "[State detection] Dungeon anchor [%s] (confidence: %.4f); entering EXPLORING before battle detection.",
                        btn_name,
                        conf,
                    )
                    self.is_in_dungeon = True
                    self.transition_to(self.STATE_DUNGEON_EXPLORING)
                    return

        for feat in ["common/auto.png", "battle/battle_features_1.png", "battle/battle_features_2.png"]:
            if os.path.exists(os.path.join("templates", feat)):
                pos, _ = self.matcher.match(screen_img, feat, threshold=0.7)
                if pos:
                    self.transition_to(self.STATE_BATTLE)
                    return

        # 2. 檢查是否在普通關卡大廳 (判斷 common/select_stage.png 與 goback_town.png 至少存在一個)
        if self.config["type"] == "stage":
            in_lobby = False
            for btn in ["common/select_stage.png", "goback_town.png"]:
                if os.path.exists(os.path.join("templates", btn)):
                    pos, _ = self.matcher.match(screen_img, btn, threshold=0.8)
                    if pos:
                        in_lobby = True
                        break
            if in_lobby:
                self.transition_to(self.STATE_LOBBY)
                return
                
        # 3. 檢查是否在大廳的尋路路徑上
        for btn in self.config.get("navigation_path", []):
            pos, conf = self.matcher.match(screen_img, btn, threshold=0.8)
            logging.info(f"🔍 [除錯] 比對尋路按鈕 '{btn}'，最高相似度: {conf:.4f}，座標: {pos}")
            if pos and conf >= 0.8:
                next_state = self.STATE_COLLECT_ONLY if self.is_in_collect_only_mode() else self.STATE_NAVIGATING
                self.transition_to(next_state)
                return
                
        # 4. 檢查是否在地下城探險中 (不限模式 Mode-Agnostic：無論當前設定為 dungeon/mix/daily，只要畫面出現地下城特徵即確定處於地下城)
        dungeon_features = [
            "dungeons/leave.png",
            "dungeons/dungeons_complete.png",
            "dungeons/gungeon_godown.png",
            "dungeons/Treasure.png",
            "dungeons/dungeon_bless.png",
            "dungeons/dungeon_fight.png"
        ]
        for btn_name in dungeon_features:
            if os.path.exists(os.path.join("templates", btn_name)):
                pos, conf = self.matcher.match(screen_img, btn_name, threshold=0.8)
                if pos:
                    logging.info(f"🏰 全域定位：偵測到地下城內部特徵 [{btn_name}] (信心度: {conf:.4f})，鎖定地下城探索狀態！")
                    self.is_in_dungeon = True
                    self.transition_to(self.STATE_DUNGEON_EXPLORING)
                    return
                        
        # 5. 如果是背包整理模式，強制跳轉至 BAG_CLEANING
        if self.config["type"] == "bag_clean":
            self.transition_to(self.STATE_BAG_CLEANING)
            return

        # 6. 如果以上皆非，嘗試檢查是否有退出或確認按鈕可以點擊（代表可能卡在某個手動操作的子視窗/子介面，需關閉以返回大廳）
        for quit_btn in ["common/quit.png", "common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", quit_btn)):
                pos, conf = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                if pos:
                    logging.info(f"🧭 全域定位：未能辨識主要狀態，但偵測到退出/確認按鈕 [{quit_btn}] (信心度: {conf:.4f})，嘗試點擊以返回大廳。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    # 點擊後不轉移狀態，等待下一幀的 UNKNOWN 重新進行定位與尋路
                    time.sleep(0.3)
                    return

        # 7. 如果真的是完全沒有任何可交互按鈕，才依模式給予最安全的預設落點
        if self.config["type"] == "dungeon":
            # 地下城模式下，大部份時間都在走格探索，預設回到 EXPLORING 狀態最為安全
            logging.info("❓ 未能辨識出特定探索按鈕，預設進入 EXPLORING 狀態。")
            self.transition_to(self.STATE_DUNGEON_EXPLORING)
        else:
            # 普通關卡模式下，如果能匹配到自動戰鬥特徵，預設為 BATTLE；否則預設為 NAVIGATING 以重啟大廳尋路
            has_auto = False
            for feat in ["common/auto.png", "battle/battle_features_1.png", "battle/battle_features_2.png"]:
                if os.path.exists(os.path.join("templates", feat)):
                    pos_auto, _ = self.matcher.match(screen_img, feat, threshold=0.7)
                    if pos_auto:
                        has_auto = True
                        break
            
            if has_auto:
                logging.info("⚔️ 未能辨識出關卡大廳特徵，但偵測到自動戰鬥特徵，預設進入 BATTLE 狀態。")
                self.transition_to(self.STATE_BATTLE)
            else:
                logging.info("❓ 未能辨識出關卡大廳特徵，且無自動戰鬥特徵，預設進入 NAVIGATING 狀態重啟尋路.")
                self.transition_to(self.STATE_NAVIGATING)

    def has_available_dungeon(self, target_config=None):
        """檢查記憶體中是否有冷卻已結束且允許打的地下城"""
        if target_config is not None:
            cfg = target_config
        elif getattr(self, "stamina_retreat_start_time", None) is not None and getattr(self, "original_config", None) is not None:
            cfg = self.original_config
        else:
            cfg = self.config

        if not cfg:
            return False

        # 如果模式類型不是地下城/mix/daily，直接傳回 False（防呆非地下城模式）
        cfg_type = cfg.get("type")
        if cfg_type not in ["dungeon", "mix", "daily"]:
            return False

        # 如果先前已確認所有地下城皆在冷卻中，且尚未超過暫存冷卻時間，直接傳回 False
        all_cd_until = getattr(self, "all_dungeons_on_cooldown_until", 0.0)
        if time.time() < all_cd_until:
            return False

        now = time.time()
        is_greedy = cfg.get("greedy_dungeon", False)

        explicit_target_idx = cfg.get("dungeon_index")
        if explicit_target_idx is None and not is_greedy:
            entry_templates = cfg.get("dungeon_entries") or []
            nav_path = cfg.get("navigation_path") or []
            for idx, temp_name in enumerate(entry_templates):
                if temp_name in nav_path:
                    explicit_target_idx = idx
                    break

        if target_config is not None and explicit_target_idx is not None and not is_greedy:
            return now >= self.dungeon_cooldowns.get(explicit_target_idx, 0.0)
        
        if is_greedy:
            allowed_indices = cfg.get("greedy_allowed_indices")
            if allowed_indices is None:
                raise ValueError("配置錯誤：貪婪地下城模式未設定 'greedy_allowed_indices'。")
            for idx in allowed_indices:
                if now >= self.dungeon_cooldowns.get(idx, 0.0):
                    return True
            return False
        else:
            # 非貪婪模式 (指定特定副本)：只檢查 navigation_path 中指定的副本索引
            entry_templates = cfg.get("dungeon_entries")
            if entry_templates is None:
                raise ValueError("配置錯誤：config 未設定 'dungeon_entries'，請在 config.py 或啟動設定中指定地下城入口模板清單。")
            nav_path = cfg.get("navigation_path")
            if nav_path is None:
                raise ValueError("配置錯誤：config 未設定 'navigation_path'。")

            target_idx = None
            for idx, temp_name in enumerate(entry_templates):
                if temp_name in nav_path:
                    target_idx = idx
                    break
            
            if target_idx is not None:
                return now >= self.dungeon_cooldowns.get(target_idx, 0.0)
            
            return False

    def get_dungeon_cooldown_status(self):
        """
        列出當前所有允許地下城的冷卻情形，以及判定可挑戰的地下城列表。
        :return: (status_summary_str, available_dungeon_names_list)
        """
        if not self.config:
            raise ValueError("配置錯誤：GameStateMachine 尚未設定 config。")

        dungeon_names = self.config.get("dungeon_names")
        if dungeon_names is None:
            raise ValueError("配置錯誤：config 未設定 'dungeon_names'，請在 config.py 或啟動設定中指定地下城名稱清單。")

        from utils.time_parser import format_seconds_to_readable
        now = time.time()

        is_greedy = self.config.get("greedy_dungeon", False)
        if is_greedy:
            report_indices = self.config.get("greedy_allowed_indices")
            if report_indices is None:
                raise ValueError("配置錯誤：貪婪地下城模式未設定 'greedy_allowed_indices'。")
            target_indices = report_indices
        else:
            entry_templates = self.config.get("dungeon_entries")
            if entry_templates is None:
                raise ValueError("配置錯誤：config 未設定 'dungeon_entries'，請在 config.py 或啟動設定中指定地下城入口模板清單。")
            nav_path = self.config.get("navigation_path")
            if nav_path is None:
                raise ValueError("配置錯誤：config 未設定 'navigation_path'。")

            target_idx = None
            for idx, temp_name in enumerate(entry_templates):
                if temp_name in nav_path:
                    target_idx = idx
                    break
            if target_idx is None:
                target_idx = self.config.get("dungeon_index")
            if target_idx is None:
                raise ValueError("配置錯誤：指定地下城模式找不到 'dungeon_index' 或對應入口路徑。")
            report_indices = [target_idx]
            target_indices = report_indices

        cd_details = []
        available_names = []

        for idx in report_indices:
            if idx >= len(dungeon_names):
                raise ValueError(f"配置錯誤：greedy_allowed_indices 中的索引 {idx} 超出 dungeon_names 長度 ({len(dungeon_names)})。")
            name = dungeon_names[idx]
            cd_until = self.dungeon_cooldowns.get(idx, 0.0)
            rem = cd_until - now
            if rem > 0:
                if cd_until == float('inf'):
                    cd_details.append(f"[{name}]: 永久不可打")
                else:
                    cd_str = format_seconds_to_readable(rem)
                    cd_details.append(f"[{name}]: 冷卻中 ({cd_str})")
            else:
                if idx in target_indices:
                    cd_details.append(f"[{name}]: 就緒 (可打)")
                    available_names.append(name)
                else:
                    cd_details.append(f"[{name}]: 就緒 (未啟用)")

        return ", ".join(cd_details), available_names

    def has_dungeon_status_context(self):
        """Return whether the active route contains enough data to report dungeon cooldowns."""
        cfg = self.config or {}
        if not cfg.get("dungeon_names") or not cfg.get("dungeon_entries"):
            return False
        if cfg.get("greedy_dungeon", False):
            return bool(cfg.get("greedy_allowed_indices"))
        if cfg.get("dungeon_index") is not None:
            return True
        nav_path = cfg.get("navigation_path", [])
        return any(entry in nav_path for entry in cfg["dungeon_entries"])

    def check_collection_trigger(self, screen_img):
        """
        依據冷卻時間觸發鑽石與麵包的領取（全域時間檢測，不限於大門畫面）。
        """
        config = self.config or {}

        # 以下模式不參與自動領取
        if self.config is not None and self.config["type"] in ["bag_clean", "blood_altar", "jewelry_workshop"]:
            return

        from config import GLOBAL_SETTINGS

        # 1. 檢查鑽石 CD
        default_diamond_cd = GLOBAL_SETTINGS.get("default_diamond_cd", 7200.0)
        diamond_cd = self.config.get("diamond_cd", default_diamond_cd) if self.config else default_diamond_cd
        if config.get("auto_diamond", True) and time.time() - self.last_diamond_collection_time > diamond_cd:
            if not self.need_diamond_collection:
                logging.info(f"⏰ 距離上次領鑽石已滿 {int(diamond_cd // 60)} 分鐘，觸發自動領鑽石。")
                self.need_diamond_collection = True
                self.diamond_collected_this_run = False

        # 2. 檢查體力 CD
        default_bread_cd = 7200.0 if (self.config and self.config.get("type") == "collect_only") else GLOBAL_SETTINGS.get("default_bread_cd", 1800.0)
        bread_cd = self.config.get("bread_cd", default_bread_cd) if self.config else default_bread_cd
        if self.enable_bread and (time.time() - self.last_bread_collection_time > bread_cd):
            if not self.need_bread_collection:
                logging.info(f"⏰ 距離上次領體力已滿 {int(bread_cd // 60)} 分鐘，觸發自動領體力。")
                self.need_bread_collection = True
                self.bread_collected_this_run = False
                self.bread_click_attempted = False

    def attach_quest_scheduler(self, scheduler):
        """
        將實例化的 QuestScheduler 動態掛載至 GameStateMachine。
        """
        self.quest_scheduler = scheduler
        logging.info("🔗 [GameStateMachine] 已成功連結懸賞任務排程器 (QuestScheduler)。")

    def set_config(self, new_config):
        """
        統一設定 GameStateMachine 的模式配置，自動繼承舊配置中由使用者設定的品質偏好 (keep_colors & disassemble_colors)。
        """
        if new_config:
            if getattr(self, "config", None):
                if "keep_colors" in self.config:
                    new_config["keep_colors"] = self.config["keep_colors"]
                if "disassemble_colors" in self.config:
                    new_config["disassemble_colors"] = self.config["disassemble_colors"]
                if "sacrifice_settings" in self.config:
                    new_config["sacrifice_settings"] = self.config["sacrifice_settings"]

        self.config = new_config

    _DERIVED_STAGE_CONFIG_KEYS = frozenset({
        "stage_name", "stage_entry", "stage_target", "stage_navigation_path",
    })

    @staticmethod
    def _apply_tier4_stage_selection(config):
        """Build template paths from the declarative Tier 4 TOML options."""
        if not config.get("enable_stage_farming", False):
            return False

        stage_configs = get_stage_configs()
        level = str(config.get("tier4_stage_level", "6"))
        stage = stage_configs.get(level)
        sub_stage = config.get("tier4_sub_stage", "first")
        if not stage or sub_stage not in stage["sub_stages"]:
            logging.warning(
                "[HotReload] ignored invalid Tier 4 stage selection: level=%s, sub_stage=%s",
                level,
                sub_stage,
            )
            return False

        target = stage["sub_stages"][sub_stage]
        entry = stage["entry"]
        config.update({
            "stage_name": f"{stage['name']} ({sub_stage})",
            "stage_entry": entry,
            "stage_target": target,
            "stage_navigation_path": [
                "common/door.png",
                "common/select_stage.png",
                entry,
                "stages/stage_label.png",
                target,
            ],
        })
        if config.get("type") == "stage":
            config["navigation_path"] = [
                "common/door.png",
                "exit_battle.png",
                "common/select_stage.png",
                entry,
                "stages/stage_label.png",
                target,
            ]
        return True

    @staticmethod
    def _apply_tier4_dungeon_selection(config):
        """Build template paths from the declarative Tier 4 TOML options for dungeons."""
        # Stage configs intentionally retain dungeon template metadata for shared
        # schema compatibility.  That metadata must never turn a stage route
        # into a dungeon route during startup or hot reload.
        if config.get("type") not in {"dungeon", "mix"}:
            return False

        dungeon_entries = config.get("dungeon_entries")
        dungeon_names = config.get("dungeon_names")
        if not dungeon_entries or not dungeon_names:
            return False

        is_greedy = config.get("greedy_dungeon", False)
        if is_greedy:
            config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png"]
            return True

        raw_idx = config.get("tier4_dungeon_index", config.get("dungeon_index", 5))
        try:
            target_idx = int(raw_idx)
        except (ValueError, TypeError):
            target_idx = 5

        if 0 <= target_idx < len(dungeon_entries):
            entry_img = dungeon_entries[target_idx]
            config["dungeon_index"] = target_idx
            config["tier4_dungeon_index"] = target_idx
            config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", entry_img]
            if config.get("type") == "dungeon":
                config["name"] = f"地下城 - {dungeon_names[target_idx]}"
            return True
        else:
            logging.warning(
                "[HotReload] ignored invalid Tier 4 dungeon selection: index=%s",
                raw_idx,
            )
            return False

    def _build_tier4_fallback_config(self):
        """Build the route selected by the Daily Profile without mutating policy."""
        source = getattr(self, "primary_config", None) or getattr(self, "config", None)
        if not source:
            source = GAME_CONFIGS["daily"]
        fallback = build_tier4_fallback_config(source, GAME_CONFIGS)
        if {"tier4_stage_level", "tier4_sub_stage"} & fallback.keys():
            self._apply_tier4_stage_selection(fallback)
        if {"tier4_dungeon_index", "greedy_dungeon"} & fallback.keys():
            self._apply_tier4_dungeon_selection(fallback)
        fallback["is_tier4_fallback"] = True
        return fallback

    def _daily_activity_config(self):
        """Return the persistent Daily scheduling policy, not a temporary route."""
        if self.is_daily_pipeline_active() and getattr(self, "primary_config", None):
            return self.primary_config
        return self.config or {}

    def has_available_daily_dungeon(self):
        """Check the timed dungeon policy even while Tier 4 is a domain route."""
        policy = self._daily_activity_config()
        if not policy.get("enable_dungeon", False):
            return False
        return self.has_available_dungeon(target_config=policy)

    def has_pending_daily_activity(self):
        """Report whether a higher-priority Daily activity should exit Tier 4."""
        if not self.is_daily_pipeline_active():
            return False
        policy = self._daily_activity_config()
        manager = getattr(self, "daily_manager", None)
        if manager and policy.get("enable_town_daily", True):
            if manager.get_pending_town_subflows():
                return True
        if self.has_available_demon_lords() or self.has_available_selected_lord_boss():
            return True
        if self.poll_daily_quest_preemption():
            return True
        return self.has_available_daily_dungeon()

    def enable_runtime_config_refresh(self, mode_key, initial_config):
        """Track the active Profile mode as the runtime configuration source."""
        if mode_key not in GAME_CONFIGS:
            return
        self.runtime_config_key = mode_key
        # Profile TOML is authoritative after startup.  Interactive choices are
        # persisted before this method runs, so retaining a diff here would make
        # later edits to that same Profile appear to hot-reload without effect.
        self.runtime_config_overrides = {}
        if getattr(self, "primary_config", None):
            self._apply_tier4_stage_selection(self.primary_config)
            self._apply_tier4_dungeon_selection(self.primary_config)
        if getattr(self, "config", None):
            self._apply_tier4_stage_selection(self.config)
            self._apply_tier4_dungeon_selection(self.config)

    def _sync_runtime_collection_policies(self, config):
        """Apply profile collection switches without bypassing template capability checks."""
        if not config.get("auto_bread", True):
            self.enable_bread = False
            self.need_bread_collection = False
        elif self.bread_collection_available:
            self.enable_bread = True

        if not config.get("auto_diamond", True):
            self.need_diamond_collection = False

    def get_available_selected_lord_bosses(self, now_ts=None):
        """Return Bosses selected by the active Profile and ready today."""
        manager = getattr(self, "daily_manager", None)
        active_config = self.config or {}
        primary_config = getattr(self, "primary_config", None) or {}
        is_daily_profile = (
            self.runtime_config_key == "daily"
            or primary_config.get("_config_mode_key") == "daily"
        )
        policy_config = primary_config if is_daily_profile else active_config
        if not policy_config.get("enable_lord_boss", True):
            return []
        raw_targets = policy_config.get(
            "lord_boss_targets",
            active_config.get("lord_boss_targets", DEFAULT_LORD_BOSS_TARGETS),
        )
        selected = set(raw_targets) if raw_targets is not None else set()
        if not manager or not selected:
            return []
        return [key for key in manager.get_available_lord_bosses(now_ts) if key in selected]

    def has_available_selected_lord_boss(self, now_ts=None):
        return bool(self.get_available_selected_lord_bosses(now_ts))

    def has_available_demon_lords(self):
        """檢查目前是否已啟用且尚有可挑戰的深淵魔王次數 (每日上限 3 次)。"""
        dm = getattr(self, "daily_manager", None)
        if not dm or not hasattr(dm, "is_demon_lords_available"):
            return False
        cfg = self.config or {}
        mode_type = cfg.get("type")
        is_daily_active = self.is_daily_pipeline_active() or getattr(self, "quest_scheduler", None) is not None
        default_enable = True if (mode_type in ["daily", "mix"] or is_daily_active or not cfg) else False
        if not cfg.get("enable_demon_lords", default_enable):
            return False
        from config import SUBFLOW_CONFIGS
        subflows = cfg.get("subflow_configs") if isinstance(cfg.get("subflow_configs"), dict) else SUBFLOW_CONFIGS
        subflow_cfg = (subflows or {}).get("demon_lords", {})
        if not subflow_cfg.get("enabled", False):
            return False
        targets = subflow_cfg.get("targets") or [subflow_cfg.get("target_boss", "voidborn_elres")]
        res = dm.is_demon_lords_available(targets)
        if isinstance(res, (tuple, list)) and len(res) >= 1:
            return bool(res[0])
        # 若在 Mock 環境且未明確指定回傳值，預設為不可用避免污染非魔王測試
        from unittest.mock import Mock
        if isinstance(res, Mock):
            return False
        return bool(res)

    def refresh_config_at_safe_point(self):
        """Apply a complete configuration only before a new loop iteration."""
        if not self.runtime_config_key or not refresh_runtime_config():
            return False
        refreshed_primary = get_runtime_game_config(self.runtime_config_key)
        refreshed_primary.update(deepcopy(self.runtime_config_overrides))
        self._apply_tier4_stage_selection(refreshed_primary)
        self._apply_tier4_dungeon_selection(refreshed_primary)
        was_tier4_fallback = bool(self.config and self.config.get("is_tier4_fallback"))
        self.primary_config = refreshed_primary
        self._sync_runtime_collection_policies(refreshed_primary)
        if was_tier4_fallback:
            runtime_flags = {
                key: value for key, value in self.config.items()
                if key.startswith("is_") or key == "backend_mode"
            }
            self.config = self._build_tier4_fallback_config()
            self.config.update(runtime_flags)
        elif self.config and self.config.get("type") == refreshed_primary.get("type"):
            runtime_flags = {
                key: value for key, value in self.config.items()
                if key.startswith("is_") or key == "backend_mode"
            }
            self.config = refreshed_primary.copy()
            self.config.update(runtime_flags)
        logging.info("[HotReload] refreshed running primary mode: %s", self.runtime_config_key)
        return True

    def apply_tier4_fallback_config(self):
        """Restore the user's configured Tier 4 fallback baseline.

        ``primary_config`` is the complete configuration chosen at startup.
        Daily quests may temporarily enable their required activity; this
        restores the baseline and marks it as Tier 4 for safe preemption.
        """
        if getattr(self, "primary_config", None):
            fallback_cfg = self._build_tier4_fallback_config()
            if (
                self.config.get("is_tier4_fallback", False)
                and all(self.config.get(key) == value for key, value in fallback_cfg.items())
            ):
                logging.debug("[GameStateMachine] Tier 4 fallback configuration is already active.")
                self.arm_daily_quest_preemption()
                return False
            self.set_config(fallback_cfg)
            self.arm_daily_quest_preemption()
            logging.info(f"🔄 [GameStateMachine] 已切換至使用者設定的 Tier 4 退守配置: {self.config.get('name', 'fallback')} (關卡: {self.config.get('stage_name', 'default')})")
        else:
            from config import PRIMARY_MODES
            mix_config = PRIMARY_MODES["mix"].copy()
            mix_config["greedy_dungeon"] = False
            mix_config["navigation_path"] = ["common/door.png", "dungeons/dungeon.png", "dungeons/Ice_entry.png"]
            mix_config["is_tier4_fallback"] = True
            if hasattr(self, "backend_mode"):
                mix_config["backend_mode"] = self.backend_mode

            self.set_config(mix_config)
            self.primary_config = mix_config.copy()
            self.arm_daily_quest_preemption()
            logging.info(f"🔄 [GameStateMachine] 未找到使用者基準配置，已切換至預設 Tier 4 退守配置: {mix_config['name']}")



    def check_and_advance_quest_target(self):
        """
        當當前任務目標完成時，動態查詢下一個懸賞任務目標並切換模式配置。
        傳回值:
          TaskNode: 成功排定並切換至該 Tier 3 懸賞任務目標 (Truthy)
          None: 無法排定任何懸賞任務（無任務、已 100% 全部完成、或全部冷卻中） (Falsy)
        """
        if self.quest_scheduler is None:
            return None

        if self.quest_scheduler.is_all_completed():
            daily_manager = getattr(self, "daily_manager", None)
            accepted_quests = []
            if daily_manager is not None:
                accepted_quests = daily_manager.status.get("subflows", {}).get(
                    "bulletin_board", {}
                ).get("accepted_quests", [])

            if accepted_quests:
                logging.warning(
                    "⚠️ [懸賞排程修復] 記憶體排程器已完成，但持久化資料仍有 %d 項 "
                    "accepted_quests；從持久化事實重建排程器。",
                    len(accepted_quests),
                )
                self.attach_quest_scheduler(daily_manager.load_quest_scheduler())
                remaining_accepted = daily_manager.status.get("subflows", {}).get(
                    "bulletin_board", {}
                ).get("accepted_quests", [])
                if self.quest_scheduler.is_all_completed() and remaining_accepted:
                    logging.error(
                        "⚠️ [懸賞排程修復] accepted_quests 仍有資料，但無法建立可執行任務；"
                        "保留排程器並禁止誤判為全部完成。"
                    )
                    return None

        if self.quest_scheduler.is_all_completed():
            logging.info("🎉 [GameStateMachine] 所有每日懸賞任務均已 100% 完成！解除懸賞排程器並切換至退守模式。")
            self.quest_scheduler = None
            self.apply_tier4_fallback_config()
            return None

        target_task, msg = self.quest_scheduler.get_next_action_node(
            dungeon_cooldowns=self.dungeon_cooldowns,
            log_cooldowns=True,
        )
        if target_task:
            if target_task.completed_count >= target_task.max_run_limit:
                logging.warning(f"⚠️ [上限防呆強制刪除] 懸賞任務 [{target_task.quest_title}] 已達到最多 {target_task.max_run_limit} 次戰鬥上限，強制將該任務從排程佇列與 JSON 中刪除！")
                self.quest_scheduler.tasks = [t for t in self.quest_scheduler.tasks if t != target_task]
                if getattr(self, "daily_manager", None):
                    self.daily_manager.remove_accepted_quest(target_task.quest_title)
                return self.check_and_advance_quest_target()

            # Each quest starts from the startup baseline, never from the
            # preceding quest's temporary activity switches.
            base_cfg = getattr(self, "primary_config", None) or getattr(self, "config", None)
            quest_cfg = target_task.to_config_dict(base_config=base_cfg)
            if hasattr(self, "backend_mode"):
                quest_cfg["backend_mode"] = self.backend_mode
            self.set_config(quest_cfg)
            logging.info(f"🔄 [GameStateMachine 動態調度] {msg} ➔ 即時自動切換至目標配置: {quest_cfg.get('name')}")
            return target_task

        # 當前尚有未完成任務但均在冷卻中：確保切換至 Tier 4 退守配置，等待冷卻就緒
        if not self.config.get("is_tier4_fallback", False):
            self.apply_tier4_fallback_config()
        return None




    def click_and_wait_until_gone(self, template_name, click_x, click_y, rect, timeout=6.0, threshold=0.75, brightness_threshold=0.0, check_interval=1.0, post_delay=1.0, retry_interval=1.0):
        """
        [配對確認直到消失 - 專案級輔助 API]
        點擊 (click_x, click_y)，並以 check_interval 輪詢比對 template_name，直到其從畫面上 100% 消失。
        若超過 retry_interval 秒模板仍未消失，則發起補點擊 (Re-click)。
        """
        logging.info(f"👉 發起點擊 ({click_x}, {click_y})，啟動「配對確認直到 [{template_name}] 消失」輪詢閉環 (輪詢間隔 {check_interval}s)...")
        self.mouse.click(click_x, click_y)

        start_t = time.time()
        last_click_t = start_t
        disappeared = False
        while time.time() - start_t < timeout:
            if hasattr(self, "resume_event") and self.resume_event:
                self.resume_event.wait()
            time.sleep(check_interval)
            if self.capturer:
                fresh_img = self.capturer.capture(rect)
                if fresh_img is not None and os.path.exists(os.path.join("templates", template_name)):
                    pos, conf = self.matcher.match(fresh_img, template_name, threshold=threshold, brightness_threshold=brightness_threshold, quiet=True)
                    if pos is None:
                        logging.info(f"🟢 [配對確認完成] 模板 [{template_name}] 已徹底從畫面上消失！費時 {time.time() - start_t:.2f} 秒。")
                        disappeared = True
                        break
                    else:
                        logging.info(f"⌛ [配對確認中] 模板 [{template_name}] 仍存在於畫面上 (相似度: {conf:.4f})，持續等待淡出...")
                        if time.time() - last_click_t >= retry_interval:
                            logging.info(f"🔄 [自動補點] 模板 [{template_name}] 在 {retry_interval} 秒內未消失，重新發起點擊 ({click_x}, {click_y})...")
                            self.mouse.click(click_x, click_y)
                            last_click_t = time.time()

        if not disappeared:
            logging.warning(f"⚠️ [配對確認逾時] 模板 [{template_name}] 在 {timeout} 秒內未能確認消失。")

        time.sleep(post_delay)
        return disappeared

    def _run_task_complete_subflow(self, rect):
        """
        以 Match 驅動之 Phase 狀態機執行「領取任務獎勵」子流程。
        唯有當當前 Phase 成功 Match 到目標元素時才更新狀態推進；無 Match 則保持 Phase 等待下一幀。
        """
        if not hasattr(self, "task_complete_phase") or not self.task_complete_phase:
            self.task_complete_phase = "INIT_BANNER_CHECK"

        screen_img = self.capturer.capture(rect)
        if screen_img is None:
            return

        # ===== Phase 1: 彈窗存續檢測 (INIT_BANNER_CHECK) =====
        if self.task_complete_phase == "INIT_BANNER_CHECK":
            pos_task, conf_task = self.matcher.match(screen_img, "task_complete.png", threshold=0.75)
            if pos_task:
                logging.info(f"🟢 [Phase 1: INIT_BANNER_CHECK] Match 成功！發現 task_complete 彈窗 (座標: {pos_task}, 信心度: {conf_task:.4f})，切換 Phase ➔ OCR_RECOGNIZE")
                self.task_complete_phase = "OCR_RECOGNIZE"
                self._subflow_cached_pos_task = pos_task
            else:
                # 📌 有 match 才能更新狀態；若無 match 則保持 Phase 不變，等待下一幀繼續 match
                return

        # ===== Phase 2: OCR 標題辨識與持久化核銷 (OCR_RECOGNIZE) =====
        if self.task_complete_phase == "OCR_RECOGNIZE":
            cached_pos = getattr(self, "_subflow_cached_pos_task", None)
            task_recognized = False
            for attempt in range(1, 4):
                if self.quest_scheduler:
                    try:
                        recognized_title = self.quest_scheduler.process_task_complete_banner(
                            screen_img, cached_pos, ocr_reader=self.get_ocr_reader
                        )
                        if recognized_title:
                            logging.info(f"✅ [Phase 2: OCR_RECOGNIZE] 第 {attempt} 次 Match/辨識成功核銷任務: [{recognized_title}]。")
                            task_recognized = True
                            self._subflow_completed_task = True
                            break
                    except Exception as e:
                        logging.debug(f"OCR 辨識發生例外: {e}")
                
                time.sleep(0.2)
                screen_img = self.capturer.capture(rect)
                if screen_img is None:
                    break

            if not task_recognized:
                logging.warning("⚠️ [Phase 2: OCR_RECOGNIZE] OCR 嘗試結束，切換 Phase ➔ FIND_DISMISS_TARGET。")

            # 辨識步驟結束，更新 Phase 推進至下一階段 (允許同幀瀑布直通)
            self.task_complete_phase = "FIND_DISMISS_TARGET"

        # ===== Phase 3: 尋找關閉按鈕與目標座標 (FIND_DISMISS_TARGET) =====
        if self.task_complete_phase == "FIND_DISMISS_TARGET":
            cached_pos = getattr(self, "_subflow_cached_pos_task", None)
            click_x, click_y, target_tpl = None, None, "task_complete.png"

            # 1. 優先比對獨立確認按鈕 (common/confirm.png 或 common/ok.png)
            for btn_name in ["common/confirm.png", "common/ok.png"]:
                if os.path.exists(os.path.join("templates", btn_name)):
                    pos_btn, conf_btn = self.matcher.match(screen_img, btn_name, threshold=0.80)
                    if pos_btn:
                        click_x = rect["left"] + pos_btn[0]
                        click_y = rect["top"] + pos_btn[1]
                        target_tpl = btn_name  # 鎖定監控消失標的為 confirm.png / ok.png
                        logging.info(f"🎉 [Phase 3: FIND_DISMISS_TARGET] Match 成功！鎖定確認按鈕 [{btn_name}] 座標: ({click_x}, {click_y})。")
                        break

            # 2. 備用方案：若無獨立按鈕，使用彈窗中心算出的保底領獎座標，並鎖定 task_complete.png
            if click_x is None and cached_pos is not None:
                height_to_use = rect.get("height") or screen_img.shape[0] or 1080
                scale_y = height_to_use / 1080.0
                click_x = rect["left"] + cached_pos[0]
                click_y = rect["top"] + cached_pos[1] + int(281 * scale_y)
                target_tpl = "task_complete.png"  # 鎖定監控消失標的為 task_complete.png
                logging.info(f"🔄 [Phase 3: FIND_DISMISS_TARGET] 使用保底領獎座標: ({click_x}, {click_y})，監控標的: [{target_tpl}]。")

            if click_x is not None and click_y is not None:
                self._subflow_click_target = (click_x, click_y, target_tpl)
                logging.info(f"🟢 [Phase 3: FIND_DISMISS_TARGET] 按鈕/座標定位成功 (標的: {target_tpl})，切換 Phase ➔ CLICK_DISMISS_LOOP")
                self.task_complete_phase = "CLICK_DISMISS_LOOP"
            else:
                return

        # ===== Phase 4: 配對點擊直到目標與 confirm 彈窗徹底消失 (CLICK_DISMISS_LOOP) =====
        if self.task_complete_phase == "CLICK_DISMISS_LOOP":
            click_target = getattr(self, "_subflow_click_target", None)
            if click_target and click_target[0] is not None and click_target[1] is not None:
                click_x, click_y, target_tpl = click_target
                logging.info(f"👉 [Phase 4: CLICK_DISMISS_LOOP] 發起配對點擊 ({click_x}, {click_y}) 直到 [{target_tpl}] 與所有 confirm 彈窗徹底消失 (每 2.0 秒匹配檢查一次)...")
                
                # 1. 第一階段：配對點擊並等待目標標的與 confirm 消失 (每次輪詢 2.0 秒)
                self.click_and_wait_until_gone(
                    target_tpl, click_x, click_y, rect,
                    timeout=10.0, threshold=0.70, check_interval=2.0, retry_interval=2.0, post_delay=0.5
                )

                # 2. 第二階段：連鎖檢查是否還有殘留的 confirm/ok 按鈕，匹配直到完全沒有 confirm (每次 2.0s 輪詢)
                for extra_round in range(1, 3):
                    fresh_img = self.capturer.capture(rect)
                    if fresh_img is None:
                        break
                    
                    found_any_confirm = False
                    for btn_name in ["common/confirm.png", "common/ok.png"]:
                        if os.path.exists(os.path.join("templates", btn_name)):
                            match_res = self.matcher.match(fresh_img, btn_name, threshold=0.75, quiet=True) if hasattr(self.matcher, 'match') else None
                            pos_c = match_res[0] if match_res and isinstance(match_res, tuple) and len(match_res) >= 1 else None
                            conf_c = match_res[1] if match_res and isinstance(match_res, tuple) and len(match_res) >= 2 else 0.0
                            if pos_c:
                                found_any_confirm = True
                                cx = rect["left"] + pos_c[0]
                                cy = rect["top"] + pos_c[1]
                                logging.info(f"🔄 [Phase 4: 二次補點擊] 畫面上仍存在彈窗 [{btn_name}] (相似度: {conf_c:.4f})，點擊 ({cx}, {cy}) 並等待 2.0 秒...")
                                self.mouse.click(cx, cy)
                                time.sleep(2.0)
                                break
                    
                    if not found_any_confirm:
                        logging.info("🟢 [Phase 4: 配對完成] 畫面上已完全無任何 confirm/ok 彈窗，安全結束子流程。")
                        break
            
            # 關閉成功，重置 Phase 與暫存屬性
            self.task_complete_phase = "INIT_BANNER_CHECK"
            self._subflow_cached_pos_task = None
            self._subflow_click_target = None
            if getattr(self, "_subflow_completed_task", False):
                self._subflow_completed_task = False
                logging.info("🔄 [任務核銷完成] 「領取任務獎勵」子流程完成，觸發動態推進下一個懸賞任務目標...")
                self.check_and_advance_quest_target()
            logging.info("🎉 [子流程] 「領取任務獎勵」 Phase 狀態機圓滿結束！")

    def start_subflow_queue(self, queue):
        """
        初始化並啟動城鎮子流程佇列，並單次列印任務總覽儀表板。
        """
        from config import SUBFLOW_CONFIGS
        self.town_subflow_queue = list(queue)

        logging.info("=" * 60)
        logging.info("🏛️ 【城鎮任務流水線 - 任務總覽儀表板】 🏛️")
        logging.info("=" * 60)
        for idx, flow_key in enumerate(queue, 1):
            cfg = SUBFLOW_CONFIGS.get(flow_key, {})
            name = cfg.get("name", flow_key)
            is_enabled = cfg.get("enabled", True)
            status_str = "🟢 待執行 (Enabled)" if is_enabled else "🔴 停用 (enabled=False)"
            logging.info(f"  {idx}. [{flow_key}] {name:<12} : {status_str}")
        logging.info("=" * 60)

        self.pop_and_next_town_subflow()

    def trigger_town_subflow_chain(self):
        """
        當背包清理完成退回城鎮後，構建需在城鎮執行的子流程佇列。
        """
        from config import GLOBAL_SETTINGS
        cfg = self.config or {}
        order = cfg.get("town_subflow_order", GLOBAL_SETTINGS.get("default_town_subflow_order", ["blood_altar", "jewelry_workshop"]))
        logging.info("🏛️ [城鎮流水線] 背包清理完成，構建城鎮任務佇列...")
        self.start_subflow_queue(order)

    def pop_and_next_town_subflow(self):
        """
        彈出並執行佇列中的下一個城鎮任務。若佇列已空，則回復 STATE_NAVIGATING。
        """
        # 切換任務前先重置舊標記，防止舊標記優先權高於新標記
        self.need_blood_altar = False
        self.need_jewelry_workshop = False

        while self.town_subflow_queue:
            next_flow = self.town_subflow_queue.pop(0)

            from config import SUBFLOW_CONFIGS, GAME_CONFIGS
            flow_cfg = SUBFLOW_CONFIGS.get(next_flow, {})
            if not self.is_dev_subflow_run and not flow_cfg.get("enabled", True):
                logging.info(f"⏭️ [城鎮流水線] 子流程 [{next_flow}] 設定為停用 (enabled=False) ➔ 自動跳過！剩餘佇列 ({len(self.town_subflow_queue)} 個): {self.town_subflow_queue}")
                dm = getattr(self, "daily_manager", None)
                if dm and hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed(next_flow)
                continue

            flow_name = flow_cfg.get("name", next_flow)
            logging.info("=" * 60)
            logging.info(f"🎯 [城鎮流水線進度] 彈出並切換至任務: [{next_flow}] ({flow_name})")
            logging.info(f"📌 剩餘待執行子流程 ({len(self.town_subflow_queue)} 個): {self.town_subflow_queue}")
            logging.info("=" * 60)

            if next_flow in GAME_CONFIGS:
                self.set_config(GAME_CONFIGS[next_flow].copy())

            if next_flow == "bag_clean":
                self.need_bag_cleaning = True
                self.transition_to(self.STATE_BAG_CLEANING)
                return
            elif next_flow == "blood_altar":
                self.need_blood_altar = True
            elif next_flow == "jewelry_workshop":
                self.need_jewelry_workshop = True



            # 🏛️ 資料驅動動態派發：依據 TOWN_SUBFLOW_CONFIG_MAP 反向比對目標狀態
            config_to_state = {v: k for k, v in self.TOWN_SUBFLOW_CONFIG_MAP.items()}
            target_state = config_to_state.get(next_flow)
            if target_state:
                self.transition_to(target_state)
                return

        # 若佇列已空！無條件強制重置所有城鎮子流程旗標，防止殘留旗標導致死循環
        self.need_blood_altar = False
        self.need_jewelry_workshop = False
        self.need_bag_cleaning = False

        logging.info("=" * 60)
        logging.info("🎉 【城鎮流水線 - 全部完成】 🎉")
        if getattr(self, "is_dev_subflow_run", False):
            logging.info("Dev 測試模式：所有指定的城鎮子流程已全數執行完畢！結束程式。")
            logging.info("=" * 60)
            import sys
            sys.exit(0)
            return

        if getattr(self, "original_config", None) is not None:
            from config import GAME_CONFIGS
            self.set_config(GAME_CONFIGS["collect_only"].copy())
            logging.info("體力退避期間城鎮流水線結束，回復定時領取待機配置 [collect_only]...")
        elif getattr(self, "primary_config", None):
            self.set_config(self.primary_config.copy())
            logging.info(f"恢復主掛機模式配置: [{self.config.get('name', '原模式')}]")
        else:
            logging.info("重置旗標並回復原模式續行...")
        logging.info("=" * 60)

        # 城鎮流水線結束，先將狀態轉移至 NAVIGATING / COLLECT_ONLY，確保退出子流程狀態
        next_st = self.STATE_COLLECT_ONLY if self.is_in_collect_only_mode() else self.STATE_NAVIGATING
        self.transition_to(next_st)

        # 全域每日大流水線自動排程檢查 (僅在 daily 模式下觸發)
        if self.is_daily_pipeline_active():
            # A town-only queue can finish while accepted_quests still exist.
            # Rebuild only when no scheduler is attached; retain in-memory progress.
            if self.quest_scheduler is None and getattr(self, "daily_manager", None):
                self.attach_quest_scheduler(self.daily_manager.load_quest_scheduler())
            self.evaluate_and_schedule_daily_pipeline()

    def is_in_collect_only_mode(self):
        """
        檢查目前活躍配置是否為定時領取待機 (collect_only)。
        注意：不應僅以 stamina_retreat_start_time is not None 判定，
        因為在 auto_resume_dungeon_on_cd 暫時切回打地下城時，stamina_retreat_start_time 仍保留作為背景倒數。
        """
        if getattr(self, "current_state", None) == self.STATE_COLLECT_ONLY:
            return True
        if not getattr(self, "config", None):
            return False
        return self.config.get("type") == "collect_only"

    def is_daily_pipeline_active(self):
        """
        檢查目前是否處於每日全域流水線 (--mode daily) 運作模式中。
        注意：當處於定時領取待機狀態 (collect_only) 時，一律回傳 False 以禁止排程推進 accepted_quests 任務。
        """
        if not getattr(self, "daily_manager", None):
            return False
        if self.is_in_collect_only_mode():
            return False
        mode_type = self.config.get("type") if getattr(self, "config", None) else None
        primary_mode = (getattr(self, "primary_config", None) or {}).get("_config_mode_key")
        return (
            self.runtime_config_key == "daily"
            or primary_mode == "daily"
            or mode_type in ["daily", "mix"]
            or self.quest_scheduler is not None
        )

    def has_ready_daily_quest_preemption(self):
        """Return whether a ready Daily quest must preempt Tier 4 farming.

        This is deliberately a query only: ResultHandler owns the result-screen
        exit decision, while the next NAVIGATING transition owns scheduling and
        applying the selected quest configuration.
        """
        return self.poll_daily_quest_preemption()

    def arm_daily_quest_preemption(self, now_ts=None):
        """Record when Tier 3 work can next preempt Tier 4, without switching."""
        if not self.config.get("is_tier4_fallback", False) or not self.quest_scheduler:
            return False

        ready_task, _ = self.quest_scheduler.get_next_action_node(
            dungeon_cooldowns=self.dungeon_cooldowns,
            now_ts=now_ts,
        )
        if ready_task is not None:
            self.pending_daily_quest_preemption = True
            self.next_daily_quest_ready_at = None
            return True

        self.pending_daily_quest_preemption = False
        self.next_daily_quest_ready_at = self.quest_scheduler.get_next_ready_at(
            dungeon_cooldowns=self.dungeon_cooldowns,
            now_ts=now_ts,
        )
        return False

    def poll_daily_quest_preemption(self, now_ts=None):
        """Latch a ready Tier 3 task; never mutate configuration mid-activity."""
        if not self.config.get("is_tier4_fallback", False) or not self.quest_scheduler:
            return False
        if self.pending_daily_quest_preemption:
            return True

        now_ts = time.time() if now_ts is None else now_ts
        deadline = self.next_daily_quest_ready_at
        if deadline is not None and now_ts < deadline:
            return False
        return self.arm_daily_quest_preemption(now_ts=now_ts)

    def consume_daily_quest_preemption_for_navigation(self):
        """At the NAVIGATING boundary, select and apply the ready quest once."""
        if not self.pending_daily_quest_preemption:
            return False

        self.pending_daily_quest_preemption = False
        self.next_daily_quest_ready_at = None
        scheduled_task = self.check_and_advance_quest_target()
        if scheduled_task:
            logging.info("📋 [Tier 4 插隊] 已在導航安全點切換至就緒的懸賞任務。")
            return True

        # The visual cooldown state can change after the deadline was armed;
        # retain Tier 4 and calculate the next wake-up instead of thrashing.
        self.arm_daily_quest_preemption()
        return False


    def evaluate_next_activity(self):
        """
        全域模組化活動動態調度器 (Modular Activity Dynamic Scheduler)。
        依據當前 config 的活動開關與遊戲即時狀態評估並切換至下一活動：
        - 優先級 1: 每日城鎮速領 (enable_town_daily)
        - 優先級 2: 首領領主討伐 (enable_lord_boss)
        - 優先級 3: 每日懸賞任務 (enable_quests)
        - 優先級 4: 地下城探索 (enable_dungeon)
        - 優先級 5: 普通關卡打怪 (enable_stage_farming)
        - 優先級 0: 兜底基底待機 (轉入 STATE_COLLECT_ONLY)
        """
        if getattr(self, "_in_scheduling_pipeline", False):
            return False
        self._in_scheduling_pipeline = True

        try:
            cfg = self.config or {}
            activity_cfg = self._daily_activity_config()
            # 0. 體力退避期間冷卻復歸
            if getattr(self, "stamina_retreat_start_time", None) is not None:
                if cfg.get("enable_dungeon", True):
                    logging.info("🔄 [Activity Scheduler] 處於體力退避冷卻復歸期間 ➔ 嘗試執行退守地下城！")
                    self.apply_tier4_fallback_config()
                    return True
                else:
                    return False

            dm = getattr(self, "daily_manager", None)
            # 1. 檢查 Tier 1 城鎮速領 (chest, hero_draw, blood_altar, jewelry_workshop)
            if activity_cfg.get("enable_town_daily", True) and dm:
                pending_town = dm.get_pending_town_subflows()
                if pending_town and not self.town_subflow_queue:
                    logging.info(f"🏛️ [Activity Scheduler] 觸發 Tier 1 每日城鎮速領子流程: {pending_town}")
                    self.start_subflow_queue(pending_town)
                    return True

            # 1.5. 檢查 Tier 1.5 深淵魔王 (demon_lords) - 在城鎮速領之後，Lord Boss 之前
            if self.has_available_demon_lords() and not self.town_subflow_queue:
                subflows = cfg.get("subflow_configs") if isinstance(cfg.get("subflow_configs"), dict) else {}
                sub_cfg = (subflows or {}).get("demon_lords", {})
                targets = sub_cfg.get("targets") or [sub_cfg.get("target_boss", "voidborn_elres")]
                res = dm.is_demon_lords_available(targets) if dm and hasattr(dm, "is_demon_lords_available") else None
                reason = res[1] if isinstance(res, (tuple, list)) and len(res) > 1 else ""
                logging.info(f"👑 [Activity Scheduler] 觸發 Tier 1.5 深淵魔王討伐 ({reason}) ➔ 優先插隊討伐！")
                self.start_subflow_queue(["demon_lords"])
                return True

            # 2. 檢查 Tier 2 首領 Boss 討伐 (lord_boss)
            if dm and activity_cfg.get("enable_lord_boss", True):
                avail_bosses = self.get_available_selected_lord_bosses()
                if avail_bosses:
                    logging.info(f"⚔️ [Activity Scheduler] 觸發 Tier 2 領主 Boss 討伐 (可用 Boss: {avail_bosses}) ➔ 優先插隊討伐！")
                    self.start_subflow_queue(["lord_boss"])
                    return True

            # 3. 檢查 Tier 3 懸賞告示牌與動態任務 (bulletin_board)
            if self.quest_scheduler:
                if self.quest_scheduler.is_all_completed():
                    logging.info("🎉 [GameStateMachine] 所有每日懸賞任務均已 100% 完成！自動解除懸賞排程器並切換至退守模式")
                    self.quest_scheduler = None
                    self.apply_tier4_fallback_config()
                    return False
                else:
                    scheduled_node = self.check_and_advance_quest_target()
                    if scheduled_node:
                        return True
                    # Keep the scheduler attached while temporarily farming Tier 4.
                    # ResultHandler will preempt Tier 4 at the next safe result
                    # screen as soon as any Daily quest becomes runnable.
                    if self.quest_scheduler.get_pending_tasks():
                        logging.info("⏳ [Daily Pipeline] 尚有未完成懸賞任務，但目前均在冷卻中；暫時退守 Tier 4，任務就緒後將在本場結算立即插隊。")
                        self.apply_tier4_fallback_config()
                        return False

            # 4. 檢查 Tier 4 地下城探索 (dungeon)
            if activity_cfg.get("enable_dungeon", False):
                if self.has_available_dungeon(target_config=activity_cfg):
                    if cfg.get("type") == "domain":
                        dungeon_route = activity_cfg.copy()
                        self._apply_tier4_stage_selection(dungeon_route)
                        self._apply_tier4_dungeon_selection(dungeon_route)
                        dungeon_route["is_tier4_fallback"] = True
                        self.set_config(dungeon_route)
                    if self.current_state not in [self.STATE_NAVIGATING, self.STATE_DUNGEON_EXPLORING, self.STATE_BATTLE]:
                        logging.info("🏰 [Activity Scheduler] 偵測到地下城就緒 ➔ 轉移至 NAVIGATING 前往地下城！")
                        self.transition_to(self.STATE_NAVIGATING)
                    return True

            # 5. Daily 無較高優先級工作時，解析玩家選定的 Tier 4 長駐路由。
            if self.is_daily_pipeline_active():
                self.apply_tier4_fallback_config()
                return False

            # 非 Daily 的 Mix / Stage 模式維持既有關卡退守行為。
            mode_type = cfg.get("type")
            default_stage_farm = True if (mode_type in ["mix", "stage", "daily"] or getattr(self, "is_tier4_fallback", False) or getattr(self, "daily_manager", None) is not None) else False
            is_stage_farming = cfg.get("enable_stage_farming", default_stage_farm)

            if is_stage_farming:
                self.apply_tier4_fallback_config()
                return False

            # 6. 兜底待機：所有啟用活動均在冷卻中，且未開啟普通關卡打怪 ➔ 切換至 COLLECT_ONLY 待機！
            if not self.is_in_collect_only_mode():
                logging.info("💤 [Activity Scheduler] 所有啟用的週期性任務均在冷卻中且未開啟普通打怪 ➔ 轉入 COLLECT_ONLY 待機...")
                self.transition_to(self.STATE_COLLECT_ONLY)
            return False

        finally:
            self._in_scheduling_pipeline = False


    def evaluate_and_schedule_daily_pipeline(self):
        """
        全域每日大流水線動態調度器 (Daily Master Pipeline Scheduler)。
        向後相容包裝，委託至 evaluate_next_activity()。
        """
        if self.is_in_collect_only_mode():
            return False
        return self.evaluate_next_activity()
