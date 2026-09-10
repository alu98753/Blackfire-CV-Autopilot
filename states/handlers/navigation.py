import os
import time
import logging
import re
from copy import deepcopy
from states.handlers.base import BaseStateHandler
from config import (
    DEFAULT_THRESHOLD,
    SUB_STAGE_THRESHOLD,
    EXIT_BATTLE_THRESHOLD,
    ENTRY_THRESHOLD,
    TIER4_MODE_DOMAIN,
    TIER4_MODE_NONE,
    BASE_RESOLUTION_WIDTH,
    BASE_RESOLUTION_HEIGHT,
    compute_screen_scale,
    get_template_threshold
)
from utils.time_parser import parse_time_to_seconds, format_seconds_to_readable
from utils.cooldown_detector import detect_cooldown_sign_and_time
from utils.card_navigator import CardAlignmentStatus, CardListNavigator
from utils.sub_stage_navigator import SubStageDirection, SubStageListNavigator
from utils.scene_detector import SceneDetector, SceneType
from utils.dungeon_catalog import DungeonCatalog
from states.navigation_routing import (
    NavigationDecisionExecutor,
    resolve_detection_request,
    resolve_navigation_context,
)


def filter_navigation_path(nav_path, active_tabs=None, is_lobby=False):
    """
    動態過濾導航路徑中已被已開啟 UI 頁籤涵蓋的父階按鈕（防重入跳過）。
    :param nav_path: 導航路徑按鈕列表
    :param active_tabs: 已開啟頁籤名稱列表，如 ["stage"], ["dungeon"]
    :param is_lobby: 是否已身處活動大廳內部 (若在大廳內，剔除 common/door.png)
    """
    skip_btns = set()
    if is_lobby:
        skip_btns.add("common/door.png")

    if active_tabs:
        skip_map = {
            "stage": "common/select_stage.png",
            "dungeon": "dungeons/dungeon.png"
        }
        skip_btns.update({skip_map[tab] for tab in active_tabs if tab in skip_map})

    if not skip_btns:
        return list(nav_path)
    return [btn for btn in nav_path if btn not in skip_btns]

class NavigationHandler(BaseStateHandler):
    CARD_RESET_MAX_ATTEMPTS = 7
    SUB_STAGE_SCROLL_MAX_ATTEMPTS = 5
    SUB_STAGE_SCROLL_OFFSET_Y = 200
    SUB_STAGE_SCROLL_COOLDOWN = 0.25
    SUB_STAGE_MISSING_DEBOUNCE = 0.2
    SUB_STAGE_ROW1_MAX_RATIO = 0.40
    SUB_STAGE_BOUNDARY_THRESHOLD = 0.93

    @classmethod
    def _is_sub_stage_target(cls, btn: str) -> bool:
        """
        判斷給定按鈕是否為小關卡目標 (first, middle, six, final)。
        由 SubStageListNavigator 單一權威 (SSOT) 判定。
        """
        return SubStageListNavigator.is_sub_stage_target(btn)

    @classmethod
    def _is_top_sub_stage_row(cls, pos: tuple[int, int] | None, rect: dict) -> bool:
        """
        核驗偵測到的小關卡標誌 (first_stage 或 six_stage) 是否嚴格位於抽屜第一欄 (Row 1)。
        在各解析度下，Row 1 位於抽屜最上方 (約 client_h * 0.33)，
        而 Row 3 (如關卡III) 則在 Y >= client_h * 0.53。
        使用 client_h * SUB_STAGE_ROW1_MAX_RATIO (0.40) 可穩健區分 Row 1 與 Row 3。
        """
        if not pos:
            return False
        client_h = rect.get("height") or 1080
        return pos[1] <= int(client_h * cls.SUB_STAGE_ROW1_MAX_RATIO)

    @staticmethod
    def _resolve_sub_stage_hint(config: dict) -> str | None:
        """Resolve the active route before falling back to Tier 4 policy."""
        return config.get("sub_stage") or config.get("tier4_sub_stage")

    @classmethod
    def _save_boss_skull_debug_artifact(
        cls,
        screen_img,
        pos: tuple[int, int] | None,
        pos_first: tuple[int, int] | None,
        pos_six: tuple[int, int] | None,
        conf_first: float,
        conf_six: float,
        is_top: bool,
        is_bottom: bool,
        sub_stage_type: str,
        accepted: bool,
    ) -> None:
        """在 debug 模式下繪製骷髏頭及頁面邊界標記並儲存診斷圖片。"""
        if screen_img is None or getattr(screen_img, "size", 0) == 0:
            return
        try:
            import cv2
            import numpy as np
            from utils.debug_artifacts import write_debug_image

            if not isinstance(screen_img, np.ndarray):
                return

            canvas = screen_img.copy()
            box_half = 30

            # 1. 繪製 boss_skull 框框與語意
            if pos:
                bx, by = pos
                color_skull = (0, 255, 0) if accepted else (0, 0, 255)
                cv2.rectangle(canvas, (bx - box_half, by - box_half), (bx + box_half, by + box_half), color_skull, 2)
                tag = f"[boss_skull] {'ACCEPTED' if accepted else 'REJECTED'}"
                cv2.putText(canvas, tag, (bx - box_half, max(20, by - box_half - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_skull, 2)

            # 2. 繪製 first_stage 框框與語意 (若有偵測到)
            if pos_first:
                fx, fy = pos_first
                color_first = (255, 255, 0)
                cv2.rectangle(canvas, (fx - box_half, fy - box_half), (fx + box_half, fy + box_half), color_first, 2)
                cv2.putText(canvas, f"[first_stage] conf={conf_first:.2f}", (fx - box_half, max(20, fy - box_half - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_first, 2)

            # 3. 繪製 six_stage 框框與語意 (若有偵測到)
            if pos_six:
                sx, sy = pos_six
                color_six = (255, 0, 255)
                cv2.rectangle(canvas, (sx - box_half, sy - box_half), (sx + box_half, sy + box_half), color_six, 2)
                cv2.putText(canvas, f"[six_stage] conf={conf_six:.2f}", (sx - box_half, max(20, sy - box_half - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_six, 2)

            # 4. 頂部狀態列橫幅
            h, w = canvas.shape[:2]
            cv2.rectangle(canvas, (0, 0), (w, 36), (30, 30, 30), -1)
            banner = f"Target: {sub_stage_type} | conf_first: {conf_first:.4f}, conf_six: {conf_six:.4f} | top: {is_top}, bottom: {is_bottom} | {'PASS' if accepted else 'REJECT'}"
            status_color = (0, 255, 0) if accepted else (0, 0, 255)
            cv2.putText(canvas, banner, (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)

            write_debug_image("debug_boss_skull_validation.png", canvas)
        except Exception as exc:
            logging.debug(f"[DebugArtifacts] Failed to write boss skull debug artifact: {exc}")

    def _validate_boss_skull(
        self,
        pos: tuple[int, int] | None,
        rect: dict,
        match_current_frame,
        screen_img=None,
    ) -> tuple[int, int] | None:
        """
        驗證通用骷髏頭 (boss_skull) 是否符合當前子關卡目標 (middle vs final) 所在的頁面邊界。
        若目標為 final，但當前處於 Page 1 (頂部第一小關可見)，或未處於 Page 2 (頂部第六小關可見)，則拒絕該匹配；
        若目標為 middle，但當前處於 Page 2，或未處於 Page 1，則拒絕該匹配。
        """
        if not pos:
            return None
        config = self.machine.config or {}
        sub_stage_type = self._resolve_sub_stage_hint(config)
        if sub_stage_type not in ["middle", "final"]:
            return pos

        thresh_boundary = self.SUB_STAGE_BOUNDARY_THRESHOLD
        pos_six, conf_six = match_current_frame("stages/six_stage.png", threshold=thresh_boundary) if os.path.exists(os.path.join("templates", "stages/six_stage.png")) else (None, 0.0)
        pos_first, conf_first = match_current_frame("stages/first_stage.png", threshold=thresh_boundary) if os.path.exists(os.path.join("templates", "stages/first_stage.png")) else (None, 0.0)

        is_top_page = self._is_top_sub_stage_row(pos_first, rect)
        is_bottom_page = self._is_top_sub_stage_row(pos_six, rect)

        is_debug_mode = logging.getLogger().isEnabledFor(logging.DEBUG) or bool(config.get("debug", False))

        if is_debug_mode:
            logging.debug(
                f"🛡️ [骷髏頭邊界判定] 目標: {sub_stage_type}, conf_first: {conf_first:.4f}, conf_six: {conf_six:.4f}"
            )

        if sub_stage_type == "final" and (is_top_page or not is_bottom_page):
            page_desc = "頂部頁面" if is_top_page else "未確認為底部頁面"
            logging.debug(
                f"🛡️ [骷髏頭防誤判] 目標為 final 但畫面處於{page_desc} "
                f"(conf_first: {conf_first:.4f}, conf_six: {conf_six:.4f})，"
                f"忽略 Stage 5 中間小關骷髏頭,以儲存圖片:debug_boss_skull_validation.png。"
            )
            if is_debug_mode:
                self._save_boss_skull_debug_artifact(
                    screen_img, pos, pos_first, pos_six, conf_first, conf_six,
                    is_top_page, is_bottom_page, sub_stage_type, accepted=False
                )
            return None
        elif sub_stage_type == "middle" and (is_bottom_page or not is_top_page):
            page_desc = "底部頁面" if is_bottom_page else "未確認為頂部頁面"
            logging.debug(
                f"🛡️ [骷髏頭防誤判] 目標為 middle 但畫面處於{page_desc} "
                f"(conf_first: {conf_first:.4f}, conf_six: {conf_six:.4f})，"
                f"忽略 Stage 10 魔王骷髏頭，以儲存圖片:debug_boss_skull_validation.png。"
            )
            if is_debug_mode:
                self._save_boss_skull_debug_artifact(
                    screen_img, pos, pos_first, pos_six, conf_first, conf_six,
                    is_top_page, is_bottom_page, sub_stage_type, accepted=False
                )
            return None

        if is_debug_mode:
            self._save_boss_skull_debug_artifact(
                screen_img, pos, pos_first, pos_six, conf_first, conf_six,
                is_top_page, is_bottom_page, sub_stage_type, accepted=True
            )

        return pos

    def __init__(self, machine):
        super().__init__(machine)
        self.card_alignment_target_tab = None
        self.card_alignment_tab = None
        self.card_alignment_attempts = 0
        self.sub_stage_scroll_attempts = 0

    def _resolve_domain_navigation_templates(self):
        config = self.machine.config or {}
        nav_path = config.get("navigation_path", [])
        tab_template = config.get("domain_tab_btn", "domains/Domains_entry.png")
        target_template = config.get("domain_entry_btn")
        if not target_template:
            target_template = next(
                (
                    template
                    for template in nav_path
                    if template.startswith("domains/")
                    and template.endswith("/entry.png")
                    and template != tab_template
                ),
                None,
            )
        return tab_template, target_template

    def _handle_primary_card_alignment(self, screen_img, rect, scene):
        """Align primary-mode shared cards only after the active tab is observed."""
        config = self.machine.config or {}
        config_type = config.get("type")
        if config_type == "domain":
            desired_tab = "domain"
        elif config_type == "dungeon":
            desired_tab = "dungeon"
        elif config_type == "stage":
            desired_tab = "stage"
        elif config_type in {"mix", "daily"}:
            desired_tab = (
                "dungeon" if self.machine.has_available_dungeon() else "stage"
            )
        else:
            desired_tab = None

        if desired_tab is None:
            self.card_alignment_target_tab = None
            self.card_alignment_tab = None
            self.card_alignment_attempts = 0
            return False

        prev_target = getattr(self, "card_alignment_target_tab", None)
        if prev_target is not None and prev_target != desired_tab:
            self.card_alignment_tab = None
            self.card_alignment_attempts = 0
        self.card_alignment_target_tab = desired_tab

        if desired_tab not in scene.active_tabs:
            return False

        if self.card_alignment_tab == desired_tab:
            return False

        tab = desired_tab

        if tab == "domain":
            _, first_card = self._resolve_domain_navigation_templates()
            match_options = {"brightness_threshold": 0.70}
        elif tab == "dungeon":
            dungeon_entries = config.get("dungeon_entries", [])
            first_card = config.get("dungeon_first_card_btn") or (
                dungeon_entries[0] if dungeon_entries else None
            )
            match_options = None
        else:
            stage_templates = config.get("stage_templates", [])
            first_card = config.get("stage_first_card_btn") or (
                stage_templates[0] if stage_templates else None
            )
            match_options = None
        if not first_card:
            logging.error("Card alignment has no first-card anchor for tab=%s", tab)
            self.machine.request_relaunch(f"{tab}_card_alignment_config_missing")
            return True

        max_attempts = int(
            config.get(
                f"{tab}_reset_max_attempts",
                config.get("card_reset_max_attempts", self.CARD_RESET_MAX_ATTEMPTS),
            )
        )
        threshold = get_template_threshold(first_card, default=ENTRY_THRESHOLD)
        status, attempts, confidence = CardListNavigator.align_first_card(
            screen_img,
            self.matcher,
            self.mouse,
            rect,
            first_card,
            self.card_alignment_attempts,
            max_attempts=max_attempts,
            threshold=threshold,
            duration=0.8,
            inertia=False,
            match_options=match_options,
        )
        self.card_alignment_attempts = attempts

        if status == CardAlignmentStatus.ALIGNED:
            logging.info(
                "Card list aligned: tab=%s first_card=%s confidence=%.4f",
                tab,
                first_card,
                confidence,
            )
            self.card_alignment_tab = tab
            return False

        if status == CardAlignmentStatus.RETRYING:
            logging.info(
                "Resetting shared card list: tab=%s first_card=%s attempt=%d/%d",
                tab,
                first_card,
                attempts,
                max_attempts,
            )
            self.notify_ui_progress()
            time.sleep(1.2)
            return True

        logging.error(
            "Card list alignment exhausted: tab=%s first_card=%s attempts=%d",
            tab,
            first_card,
            max_attempts,
        )
        self.card_alignment_tab = None
        self.card_alignment_attempts = 0
        self.machine.request_relaunch(f"{tab}_card_alignment_failed")
        return True

    def _handle_sub_stage_scroll(
        self,
        rect: dict,
        target_sub_stage_btn: str,
        match_current_frame,
        filtered_nav_path: list[str],
        screen_img=None,
    ) -> bool:
        """
        在普通關卡子關卡抽屜內，當目標子關卡尚未出現在畫面上時，執行自適應雙向滑動。
        回傳 True 代表已執行動作或等待冷卻（應中斷後續點擊）；回傳 False 則代表無需處理。
        """
        if not target_sub_stage_btn:
            return False

        # 1. 缺失計時器防抖 (1.5 秒等待加載穩定)
        missing_time = getattr(self.machine, f"missing_time_{target_sub_stage_btn}", 0.0)
        if not isinstance(missing_time, (int, float)):
            missing_time = 0.0
        now = time.time()
        if missing_time == 0.0:
            self.machine.__setattr__(f"missing_time_{target_sub_stage_btn}", now)
            logging.info(f"⌛ 尋路中：偵測到關卡背景，但目標子關卡 [{target_sub_stage_btn}] 尚未出現，等待載入與穩定中...")
            return True
        elif now - missing_time < self.SUB_STAGE_MISSING_DEBOUNCE:
            return True

        # 2. 收集當前畫面上可見的其他子關卡
        candidates = SubStageListNavigator.get_candidate_sub_stage_templates(filtered_nav_path)
        visible_sub_stages = []
        for cand in candidates:
            if os.path.exists(os.path.join("templates", cand)):
                thresh_cand = get_template_threshold(cand, default=SUB_STAGE_THRESHOLD)
                pos_c, conf_c = match_current_frame(cand, threshold=thresh_cand)
                if pos_c and conf_c >= thresh_cand:
                    if cand in ["stages/first_stage.png", "stages/six_stage.png"]:
                        if not self._is_top_sub_stage_row(pos_c, rect):
                            continue
                    elif "boss_skull" in cand or "skull" in cand:
                        if not self._validate_boss_skull(pos_c, rect, match_current_frame, screen_img=screen_img):
                            continue
                    visible_sub_stages.append(cand)

        # 3. 取得最大重試次數與自適應方向判定
        config = self.machine.config or {}
        max_attempts = int(
            config.get(
                "sub_stage_scroll_max_attempts",
                self.SUB_STAGE_SCROLL_MAX_ATTEMPTS,
            )
        )
        sub_stage_hint = self._resolve_sub_stage_hint(config)
        direction, next_attempts = SubStageListNavigator.evaluate(
            visible_templates=visible_sub_stages,
            target_template=target_sub_stage_btn,
            attempts=self.sub_stage_scroll_attempts,
            max_attempts=max_attempts,
            sub_stage_hint=sub_stage_hint,
        )

        if direction == SubStageDirection.NONE:
            self.sub_stage_scroll_attempts = 0
            return False

        if direction == SubStageDirection.EXHAUSTED:
            logging.warning(
                f"⚠️ [子關卡導航] 已執行 {max_attempts} 次自適應滑動仍未見目標 [{target_sub_stage_btn}]，進入有界恢復..."
            )
            self.sub_stage_scroll_attempts = 0
            self.machine.request_relaunch("sub_stage_scroll_exhausted")
            return True

        # 4. 滾動冷卻時間限制 (1.5 秒)，防範快速連續滾動
        last_scroll = getattr(self.machine, "last_stage_scroll_time", 0.0)
        if now - last_scroll <= self.SUB_STAGE_SCROLL_COOLDOWN:
            return True

        # 5. 計算實體座標並執行拖曳（維持原本 center_y ± 100px 手感）
        start_x, start_y, end_x, end_y = SubStageListNavigator.calculate_drag_coords(
            rect,
            direction,
            offset_y=self.SUB_STAGE_SCROLL_OFFSET_Y,
        )
        dir_text = "向下滾動 (手勢往上拉)" if direction == SubStageDirection.SCROLL_DOWN else "向上滾動 (手勢往下拉)"
        logging.info(
            f"🧭 尋路中：在關卡背景 [stages/stage_label.png]，執行自適應{dir_text}尋找目標 [{target_sub_stage_btn}] "
            f"(第 {next_attempts}/{max_attempts} 次)..."
        )
        self.mouse.drag(start_x, start_y, end_x, end_y)
        self.machine.last_stage_scroll_time = now
        self.sub_stage_scroll_attempts = next_attempts
        time.sleep(0.3)
        return True

    def _parse_time_to_seconds(self, time_str):
        """
        將 OCR 識別出的時間字串解析為總秒數 (委充自 utils.time_parser 共用模組)。
        """
        return parse_time_to_seconds(time_str)

    def _enter_collect_only_after_dungeon_cooldown(self, screen_img, rect, reason):
        """Return to town and enter the collection idle loop for dungeon-only runs."""
        from config import GAME_CONFIGS

        logging.warning("[Dungeon cooldown fallback] %s; returning to town and entering collect_only.", reason)
        pos_back, conf_back = self.matcher.match(
            screen_img, "goback_town.png", threshold=0.75, quiet=True
        )
        if pos_back:
            logging.info("[Dungeon cooldown fallback] Clicking goback_town.png (%.4f).", conf_back)
            self.mouse.click(rect["left"] + pos_back[0], rect["top"] + pos_back[1])
            time.sleep(0.5)
        else:
            logging.warning("[Dungeon cooldown fallback] goback_town.png not found; collect_only will return on its next step.")

        current_config = self.machine.config or {}
        if not getattr(self.machine, "primary_config", None) and (
            current_config.get("enable_dungeon") or current_config.get("type") in ["daily", "mix"]
        ):
            self.machine.primary_config = deepcopy(current_config)

        if current_config.get("auto_resume_dungeon_on_cd", False):
            self.machine.dungeon_cooldown_return_config = deepcopy(current_config)
        else:
            self.machine.dungeon_cooldown_return_config = None

        self.machine.config = GAME_CONFIGS["collect_only"].copy()
        self.machine.transition_to(self.machine.STATE_COLLECT_ONLY)

    def _is_stage_farming_allowed(self) -> bool:
        """Check if stage farming is permitted when dungeons are on cooldown.

        Contract: Strictly prohibits stage farming during stamina retreat or temporary dungeon resume.
        """
        if getattr(self.machine, "stamina_retreat_start_time", None) is not None:
            return False
        if self.machine.config.get("is_dungeon_temporary_resume", False):
            return False
        mode_type = self.machine.config.get("type")
        default_farm = bool(
            mode_type in ["mix", "stage", "daily"]
            or self.machine.config.get("is_tier4_fallback", False)
        )
        return bool(self.machine.config.get("enable_stage_farming", default_farm))

    def _switch_to_stage_or_back(self, screen_img, rect, reason):
        """
        在混合模式下當地下城不可用時，設定短暫冷卻防呆標記，
        列出所有允許地下城的剩餘冷卻時間日誌，並優先點擊同頁面的 common/select_stage.png 切換至普通關卡。
        """
        now = time.time()
        dungeon_names = self.machine.config.get("dungeon_names")
        if dungeon_names is None:
            raise ValueError("配置錯誤：config 未設定 'dungeon_names'，請在 config.py 或啟動設定中指定地下城名稱清單。")
        allowed_indices = self.machine.config.get("greedy_allowed_indices")
        if allowed_indices is None:
            raise ValueError("配置錯誤：config 未設定 'greedy_allowed_indices'，請在 config.py 或啟動設定中指定允許的地下城索引清單。")
        
        report = DungeonCatalog.format_cooldown_report(
            self.machine.dungeon_cooldowns,
            target_indices=allowed_indices,
            now_ts=now,
            custom_names=dungeon_names,
        )
        self.machine.all_dungeons_on_cooldown_until = now + max(30.0, report.min_remaining_seconds)
        logging.info(f"⏳ 混合模式：{reason} ➔ 各地下城冷卻狀態: {report.summary_str}。設定冷卻緩衝 {int(max(30.0, report.min_remaining_seconds))} 秒！")

        if self.machine.is_daily_pipeline_active() and getattr(self.machine, "quest_scheduler", None) is not None and not self.machine.config.get("is_tier4_fallback", False):
            logging.info("⏳ [每日懸賞動態調度] 偵測到當前懸賞目標地下城冷卻中，權立即觸發動態重新排程，順延切換下一個任務...")
            self.machine.evaluate_and_schedule_daily_pipeline()
            return

        daily_policy = getattr(self.machine, "primary_config", None) or {}
        if (
            self.machine.is_daily_pipeline_active()
            and daily_policy.get("tier4_mode") == TIER4_MODE_DOMAIN
        ):
            logging.info("🏛️ [Daily Tier 4] 地下城冷卻中，切換至使用者設定的領地長駐路由。")
            pos_back, _ = self.matcher.match(
                screen_img, "goback_town.png", threshold=0.75, quiet=True
            )
            if pos_back:
                self.mouse.click(rect["left"] + pos_back[0], rect["top"] + pos_back[1])
                time.sleep(0.5)
            self.machine.apply_tier4_fallback_config()
            self.machine.transition_to(self.machine.STATE_NAVIGATING)
            return

        tier4_mode = daily_policy.get("tier4_mode")
        if self.machine.is_daily_pipeline_active() and tier4_mode == TIER4_MODE_NONE:
            self._enter_collect_only_after_dungeon_cooldown(
                screen_img, rect, "地下城冷卻中且 Tier 4 長駐已停用"
            )
            return

        # 若未啟用普通關卡打怪 (enable_stage_farming == False) 或處於體力退避/臨時地下城喚醒，直接返回城鎮轉入 COLLECT_ONLY 待機
        if not self._is_stage_farming_allowed():
            is_in_retreat = getattr(self.machine, "stamina_retreat_start_time", None) is not None
            is_temp_resume = bool(self.machine.config.get("is_dungeon_temporary_resume", False))
            reason = (
                "體力退避或臨時地下城喚醒期間地下城全冷卻，禁止切換至普通關卡"
                if (is_in_retreat or is_temp_resume)
                else "地下城冷卻中且未啟用普通關卡打怪 (enable_stage_farming=False)"
            )
            self._enter_collect_only_after_dungeon_cooldown(screen_img, rect, reason)
            return

        pos_st, conf_st = self.matcher.match(screen_img, "common/select_stage.png", threshold=0.60)
        if pos_st:
            logging.info(f"👉 點擊 [common/select_stage.png] ({conf_st:.4f}) 切換至普通關卡頁籤！")
            self.mouse.click(rect["left"] + pos_st[0], rect["top"] + pos_st[1])
            time.sleep(0.3)
            return
        pos_back, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.75)
        if pos_back:
            self.mouse.click(rect["left"] + pos_back[0], rect["top"] + pos_back[1])
            time.sleep(0.3)

    def _check_dungeon_status(self, screen_img, scale, h_limit, w_limit, i, visible_dungeons):
        """
        檢查指定地下城 i 的冷卻與解鎖狀態。
        如果偵測到冷卻中或未解鎖，會自動更新 self.machine.dungeon_cooldowns[i]，並回傳 True (表示不可打)。
        如果處於就緒狀態，回傳 False (表示可打)。
        """
        import cv2
        if i not in visible_dungeons:
            return False
            
        max_loc, t_w, t_h = visible_dungeons[i]
        dungeon_names = self.machine.config.get("dungeon_names")
        if dungeon_names is None:
            raise ValueError("配置錯誤：config 未設定 'dungeon_names'，請在 config.py 或啟動設定中指定地下城名稱清單。")
        
        # 1. 檢查冷卻木牌
        in_cooldown = False
        ocr_success = False
        crop_y1 = max_loc[1]
        crop_y2 = min(h_limit, max_loc[1] + t_h)
        crop_x1 = max_loc[0]
        crop_x2 = min(w_limit, max_loc[0] + t_w)
        dungeon_crop = screen_img[crop_y1:crop_y2, crop_x1:crop_x2]
        
        cd_seconds = 7200.0
        has_cd, parsed_secs, raw_text = detect_cooldown_sign_and_time(
            dungeon_crop,
            self.machine.get_ocr_reader,
            max_allowed_seconds=cd_seconds,
            threshold=0.58,
            scale=scale
        )
        if has_cd:
            logging.info(f"⏳ 貪婪地下城：[{dungeon_names[i - 1]}] 偵測到畫面中存在冷卻木牌，判定為冷卻中。")
            in_cooldown = True
            if parsed_secs is not None and 0 < parsed_secs < cd_seconds:
                logging.info(f"⏳ 貪婪地下城：[{dungeon_names[i - 1]}] 成功辨識出精確剩餘時間: \"{raw_text}\" ({format_seconds_to_readable(parsed_secs)})")
                self.machine.dungeon_cooldowns[i] = time.time() + parsed_secs
                ocr_success = True
        if in_cooldown:
            if not ocr_success:
                logging.info(f"⏳ 貪婪地下城：[{dungeon_names[i - 1]}] 剩餘時間辨識未成功，使用 30 秒臨時冷卻退避...")
                self.machine.dungeon_cooldowns[i] = time.time() + 30.0
            return True
            
        # 2. 檢查亮骨頭 (解鎖)
        cx = max_loc[0] + t_w // 2
        x1 = cx - int(90.0 * scale)
        y1 = max_loc[1] + int(250.0 * scale)
        y2 = max_loc[1] + int(520.0 * scale)
        w_skull = int(200.0 * scale)
        x2 = x1 + w_skull
        
        if 0 <= x1 and x2 <= w_limit and 0 <= y1 and y2 <= h_limit:
            skull_crop = screen_img[y1:y2, x1:x2]
            light_t_name = "dungeons/light_skull.png"
            if os.path.exists(os.path.join("templates", light_t_name)):
                light_t = cv2.imread(os.path.join("templates", light_t_name))
                if light_t is not None:
                    s_w = int(light_t.shape[1] * scale)
                    s_h = int(light_t.shape[0] * scale)
                    s_w = max(5, s_w)
                    s_h = max(5, s_h)
                    resized_light_t = cv2.resize(light_t, (s_w, s_h))
                    res_s = cv2.matchTemplate(skull_crop, resized_light_t, cv2.TM_CCOEFF_NORMED)
                    _, max_val_skull, _, _ = cv2.minMaxLoc(res_s)
                    logging.info(f"🧭 貪婪地下城：[{dungeon_names[i - 1]}] 亮骨頭匹配相似度: {max_val_skull:.4f} (閾值: 0.75)")
                    if max_val_skull < 0.75:
                        logging.warning(f"🔒 貪婪地下城：[{dungeon_names[i - 1]}] 亮骨頭相似度過低 ({max_val_skull:.4f})，判定為未解鎖或無法自動刷，設為無限冷卻。")
                        self.machine.dungeon_cooldowns[i] = float('inf')
                        return True
                        
        return False

    def handle(self, screen_img, rect):
        """
        尋路導航與自動領體力邏輯。
        """
        if rect is None:
            rect = {"left": 0, "top": 0, "width": int(BASE_RESOLUTION_WIDTH), "height": int(BASE_RESOLUTION_HEIGHT)}
            
        width = rect.get("width") or (rect.get("right", 0) - rect.get("left", 0)) or int(BASE_RESOLUTION_WIDTH)
        height = rect.get("height") or (rect.get("bottom", 0) - rect.get("top", 0)) or int(BASE_RESOLUTION_HEIGHT)
        rect["width"] = width
        rect["height"] = height

        # 0. 全域最高優先防護：若畫面上出現歡迎/關閉彈窗 (common/confirm.png, common/ok.png)，優先點擊關閉以防止遮罩擋住導航與領取
        for popup_btn in ["common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", popup_btn)):
                pos_popup, conf_popup = self.matcher.match(screen_img, popup_btn, threshold=0.90)
                if pos_popup:
                    logging.info(f"👉 [尋路防護] 偵測到可能遮擋的彈窗按鈕 [{popup_btn}] (相似度: {conf_popup:.4f})，優先點擊關閉...")
                    self.mouse.click(rect["left"] + pos_popup[0], rect["top"] + pos_popup[1])
                    time.sleep(0.5)
                    return


        # 呼叫 SceneDetector 進行全場景與 UI 頁籤診斷
        if not hasattr(self, "scene_detector") or self.scene_detector is None or self.scene_detector.matcher != self.matcher:
            self.scene_detector = SceneDetector(self.matcher)

        detection_req = resolve_detection_request(self.machine)
        scene = self.scene_detector.detect(screen_img, machine=self.machine, request=detection_req)
        frame_matches = {}

        def match_current_frame(template_name, **match_options):
            """Reuse an exact template query only while handling this screenshot."""
            normalized_options = {
                "threshold": 0.8,
                "brightness_threshold": 0.0,
                "quiet": False,
                **match_options,
            }
            cache_key = (template_name, tuple(sorted(normalized_options.items())))
            if cache_key not in frame_matches:
                frame_matches[cache_key] = self.matcher.match(screen_img, template_name, **normalized_options)
            return frame_matches[cache_key]

        # 0. 全域最高優先防護：檢查畫面上是否有任務完成彈窗 (task_complete.png) 阻擋
        if scene.scene_type == SceneType.POPUP_TASK_COMPLETE:
            matched = scene.matched_elements.get("task_complete.png")
            conf_task_chk = matched[1] if matched else 0.75
            logging.info(f"🎉 尋路中偵測到【任務完成】彈窗 (信心度: {conf_task_chk:.4f})，啟動「領取任務獎勵」子流程清理彈窗。")
            self.machine._run_task_complete_subflow(rect)
            return

        # 優先判定：如果我們已經看到地下城內部的離開按鈕或其他探索按鈕，說明點擊已經成功並進入內部，轉移狀態！
        if scene.scene_type == SceneType.IN_DUNGEON:
            check_btn = next((k for k in scene.matched_elements.keys() if k.startswith("dungeons/")), "dungeons/leave.png")
            conf = scene.matched_elements.get(check_btn, ((0, 0), 0.8))[1]
            logging.info(f"🧭 尋路中偵測到地下城內部按鈕 [{check_btn}] (信心度: {conf:.4f})，判定已進入地下城，轉移至 DUNGEON_EXPLORING。")
            self.machine.transition_to(self.machine.STATE_DUNGEON_EXPLORING)
            return

        if scene.scene_type == SceneType.DUNGEON_PREPARE:
            matched = scene.matched_elements.get("dungeons/dungeon_fight.png", ((0, 0), 0.8))
            pos_fight, conf_fight = matched[0], matched[1]
            logging.info(f"🧭 尋路中：在畫面上找到地下城戰鬥開始按鈕 [dungeons/dungeon_fight.png] (信心度: {conf_fight:.4f})，點擊進入地下城。")
            self.mouse.click(rect["left"] + pos_fight[0], rect["top"] + pos_fight[1])
            time.sleep(0.5)
            return

        # 領地主場景優先判定：若未標記清理背包且畫面上已經出現領地探索按鈕，說明已進入領地，轉移狀態至 DOMAIN_EXPLORE
        domain_explore_btn = "domains/golden_empire/explore_btn.png"
        if not self.machine.need_bag_cleaning and os.path.exists(os.path.join("templates", domain_explore_btn)):
            pos_de, conf_de = self.matcher.match(screen_img, domain_explore_btn, threshold=0.80)
            if pos_de:
                logging.info(f"🧭 尋路成功！偵測到領地探索按鈕 [{domain_explore_btn}] (信心度: {conf_de:.4f})，已進入領地，狀態轉移至 DOMAIN_EXPLORE。")
                self.machine.transition_to(self.machine.STATE_DOMAIN_EXPLORE)
                return

        # 0. 背包清理優先防護：如果需要整理背包，尋路只能引導我們退回大廳，不得前進
        if self.machine.need_bag_cleaning:
            if scene.is_town or scene.is_lobby:
                town_btn = "common/door.png" if "common/door.png" in scene.matched_elements else "goback_town.png"
                logging.info(f"🎒 尋路中：偵測到大廳/城鎮標誌 [{town_btn}] 且需要清理背包，切換至 BAG_CLEANING 狀態。")
                self.machine.transition_to(self.machine.STATE_BAG_CLEANING)
                return

            for back_btn in ["domains/common/exit_to_lobby.png", "exit_battle.png", "goback_town.png"]:
                if os.path.exists(os.path.join("templates", back_btn)):
                    pos_b, conf_b = self.matcher.match(screen_img, back_btn, threshold=0.8)
                    if pos_b:
                        logging.info(f"🎒 尋路中：需要清理背包，點擊回城/退場按鈕 [{back_btn}] 退回城鎮。")
                        self.mouse.click(rect["left"] + pos_b[0], rect["top"] + pos_b[1])
                        time.sleep(0.1)
                        return

            logging.info("⌛ 尋路中：背包已滿，正在等待退出戰鬥或返回城鎮畫面...")
            return

        # Shared intent policy owns Diamond/Bread/Start precedence.
        stage_select_open = "stage" in scene.active_tabs
        dungeon_select_open = "dungeon" in scene.active_tabs
        routing = resolve_navigation_context(self.machine, scene)
        executor = NavigationDecisionExecutor(self)
        if executor.execute(routing, screen_img, rect):
            return

        if self._handle_primary_card_alignment(screen_img, rect, scene):
            return

        # 檢查體力退避期間是否所有地下城皆已進入冷卻 (僅當前配置非 collect_only 時評估)
        if getattr(self.machine, "stamina_retreat_start_time", None) is not None and getattr(self.machine, "original_config", None) is not None:
            if self.machine.config.get("type") != "collect_only":
                orig_cfg = self.machine.original_config
                if orig_cfg.get("type") in ["dungeon", "mix", "daily"]:
                    try:
                        dungeon_avail = self.machine.has_available_dungeon(target_config=orig_cfg)
                    except Exception:
                        dungeon_avail = False

                    if not dungeon_avail:
                        self._enter_collect_only_after_dungeon_cooldown(
                            screen_img, rect, "體力退避期間所有地下城皆已進入冷卻"
                        )
                        return

        # B. 原本的尋路導航邏輯
        # 如果是地下城模式，且畫面上看見任何一個地下城入口，執行地下城選關邏輯（支援自動貪婪挑選與指定地下城左右滑動尋找）
        config_type = self.machine.config.get("type") if self.machine.config else "stage"
        nav_path = self.machine.config.get("navigation_path", [])
        
        if config_type == "blood_altar":
            self.machine.transition_to(self.machine.STATE_BLOOD_ALTAR)
            self.machine.handlers[self.machine.STATE_BLOOD_ALTAR].handle(screen_img, rect)
            return
        
        # 判斷意圖是否需要地下城卡片掃描。真正的掃描還必須由畫面
        # 證據確認 dungeon 頁籤已開啟；config 只代表想去哪裡，不能代表
        # 現在在哪裡。
        wants_dungeon_scan = False
        if config_type == "dungeon":
            wants_dungeon_scan = True
        elif config_type == "mix":
            wants_dungeon_scan = self.machine.has_available_dungeon()
        should_scan_dungeons = wants_dungeon_scan and dungeon_select_open
        
        # 為了避免在單元測試中使用 MagicMock 時 cv2 運算崩潰，僅在 screen_img 有 shape 屬性時執行 OpenCV 模板匹配
        is_dungeon_page = False
        visible_dungeons = {}
        scale = 1.0
        
        if should_scan_dungeons and type(screen_img).__name__ == "ndarray":
            # === 確保地下城滾動完全靜止後才開始進行圖像辨識，避免在動畫中進行錯誤判定 ===
            # 在單元測試中，我們允許繞過此時間限制，以便連續執行同步模擬
            import sys
            is_testing = "unittest" in sys.modules
            last_scroll = getattr(self.machine, "last_dungeon_scroll_time", 0.0)
            if not isinstance(last_scroll, (int, float)):
                last_scroll = 0.0
            time_diff = time.time() - last_scroll
            if time_diff < 2.2 and not is_testing:
                logging.info(f"⌛ 剛執行過地下城水平滑動 (僅過 {time_diff:.1f} 秒)，等待地圖滾動完全靜止後再進行圖像辨識...")
                return
            import cv2
            h_img, w_img = screen_img.shape[:2]
            standard_widths = [1280, 1366, 1600, 1920, 2560, 3840]
            matched_width = w_img
            for sw in standard_widths:
                if abs(w_img - sw) <= 30:
                    matched_width = sw
                    break
            scale = compute_screen_scale(matched_width)
            
            dungeon_names = self.machine.config.get("dungeon_names")
            if dungeon_names is None:
                raise ValueError("配置錯誤：config 未設定 'dungeon_names'，請在 config.py 或啟動設定中指定地下城名稱清單。")
            entry_templates = self.machine.config.get("dungeon_entries")
            if entry_templates is None:
                raise ValueError("配置錯誤：config 未設定 'dungeon_entries'，請在 config.py 或啟動設定中指定地下城入口模板清單。")
            temp_confidences = {}
            
            for idx, temp_name in enumerate(entry_templates, start=1):
                if os.path.exists(os.path.join("templates", temp_name)):
                    t_img = cv2.imread(os.path.join("templates", temp_name))
                    if t_img is not None:
                        orig_h, orig_w = t_img.shape[:2]
                        t_w = int(orig_w * scale)
                        t_h = int(orig_h * scale)
                        resized_t = cv2.resize(t_img, (t_w, t_h))
                        res = cv2.matchTemplate(screen_img, resized_t, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, max_loc = cv2.minMaxLoc(res)
                        temp_confidences[dungeon_names[idx - 1]] = max_val
                        if max_val >= 0.6:
                            visible_dungeons[idx] = (max_loc, t_w, t_h)
                            is_dungeon_page = True
            
            # 另外偵測鎖定狀態的卡片 locked_entry
            if os.path.exists(os.path.join("templates", "common/locked_entry.png")):
                l_img = cv2.imread(os.path.join("templates", "common/locked_entry.png"))
                if l_img is not None:
                    l_w = int(238.0 * scale)
                    l_h = int(41.0 * scale)
                    resized_l = cv2.resize(l_img, (l_w, l_h))
                    res_l = cv2.matchTemplate(screen_img, resized_l, cv2.TM_CCOEFF_NORMED)
                    _, max_val_l, _, _ = cv2.minMaxLoc(res_l)
                    temp_confidences["LockedEntry"] = max_val_l
                    if max_val_l >= 0.75:
                        is_dungeon_page = True

            if not is_dungeon_page:
                # 僅在真的被判定為非選關介面時印出信心度以供除錯
                conf_str = ", ".join([f"{k}: {v:.4f}" for k, v in temp_confidences.items()])
                logging.info(f"🔍 [除錯] 未偵測到地下城選關介面 (is_dungeon_page=False)。各模板信心度: {conf_str}")

            if is_dungeon_page:
                logging.info("🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。")
                
                if not visible_dungeons:
                    fallback_count = self.card_alignment_attempts
                    max_attempts = int(
                        self.machine.config.get(
                            "dungeon_reset_max_attempts",
                            self.CARD_RESET_MAX_ATTEMPTS,
                        )
                    )
                    if fallback_count < max_attempts:
                        logging.info(
                            "🧭 貪婪地下城：未見任何解鎖卡片，執行拉回左側 %d/%d 次。",
                            fallback_count + 1,
                            max_attempts,
                        )
                        CardListNavigator.reset_to_left(
                            self.mouse,
                            rect,
                            duration=0.8,
                            inertia=False,
                        )
                        self.notify_ui_progress()
                        self.machine.last_dungeon_scroll_time = time.time()
                        self.card_alignment_attempts = fallback_count + 1
                        time.sleep(1.2)
                    else:
                        logging.warning(
                            "⚠️ 地下城拉回已達 %d 次，仍未發現解鎖卡片，開始 recovery。",
                            max_attempts,
                        )
                        if self.machine.config.get("type") == "mix":
                            self.card_alignment_attempts = 0
                            self._switch_to_stage_or_back(screen_img, rect, "地下城頁面經防呆滑動後仍無可打關卡")
                            return
                        pos_back = None
                        if os.path.exists(os.path.join("templates", "goback_town.png")):
                            pos_back, conf_back = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
                        if pos_back:
                            logging.info(f"👉 偵測到返回按鈕 [goback_town.png] (信心度: {conf_back:.4f})，點擊返回。")
                            self.mouse.click(rect["left"] + pos_back[0], rect["top"] + pos_back[1])
                            self.card_alignment_attempts = 0  # 重置計數
                            time.sleep(1.0)
                        else:
                            logging.warning("⚠️ 無法定位返回按鈕 [goback_town.png]，原地等待中...")
                            time.sleep(1.0)
                    return
                
                # 有找到解鎖卡片，重置防呆滑動計數
                self.card_alignment_attempts = 0
                
                target_idx = None
                is_greedy = self.machine.config.get("greedy_dungeon", False)
                h_limit, w_limit = screen_img.shape[:2]
                
                if is_greedy:
                    allowed_indices = self.machine.config.get("greedy_allowed_indices")
                    if allowed_indices is None:
                        raise ValueError("配置錯誤：config 未設定 'greedy_allowed_indices'，請在 config.py 或啟動設定中指定允許的地下城索引清單 (例如: [1, 2, 3, 4, 5, 6])。")
                    # 貪婪模式：從高到低遍歷，尋找第一個就緒且解鎖的地下城
                    for i in range(len(entry_templates), 0, -1):
                        if i not in allowed_indices:
                            continue
                        cooldown_until = self.machine.dungeon_cooldowns.get(i, 0.0)
                        if time.time() < cooldown_until:
                            if cooldown_until == float('inf'):
                                logging.info(f"⏳ 貪婪地下城：[{dungeon_names[i - 1]}] 處於永久不可打狀態，跳過。")
                            else:
                                logging.info(f"⏳ 貪婪地下城：[{dungeon_names[i - 1]}] 處於冷卻中，剩餘 {int(cooldown_until - time.time())} 秒，跳過。")
                            continue
                            
                        # 如果目標地下城在畫面上，我們檢測冷卻與解鎖狀態
                        if i in visible_dungeons:
                            # 呼叫提取出的通用檢查函數
                            is_unavailable = self._check_dungeon_status(
                                screen_img, scale, h_limit, w_limit, i, visible_dungeons
                            )
                            if is_unavailable:
                                continue
                                
                            # 通過所有檢查，該關卡是我們的貪婪目標！
                            target_idx = i
                            break
                        else:
                            # 該關卡是我們想打的最高副本，但是目前不在畫面上，我們需要滑動來尋找它！
                            target_idx = i
                            break
                else:
                    # 非貪婪模式（指定特定副本）：目標 index 直接從 navigation_path 中尋找
                    nav_path = self.machine.config.get("navigation_path", [])
                    target_idx = DungeonCatalog.resolve_index_from_nav_path(nav_path, entry_templates)
                    if target_idx is None:
                        raw_idx = self.machine.config.get("tier4_dungeon_index", self.machine.config.get("dungeon_index"))
                        if raw_idx is not None:
                            try:
                                parsed_idx = int(raw_idx)
                                if 1 <= parsed_idx <= len(entry_templates):
                                    target_idx = parsed_idx
                            except (ValueError, TypeError):
                                pass
                            
                    if target_idx is not None:
                        # 1. 優先檢查記憶體冷卻
                        cooldown_until = self.machine.dungeon_cooldowns.get(target_idx, 0.0)
                        if time.time() < cooldown_until:
                            if self.machine.config.get("type") == "mix" or self.machine.is_daily_pipeline_active():
                                self._switch_to_stage_or_back(screen_img, rect, f"指定副本 [{dungeon_names[target_idx - 1]}] 處於冷卻中")
                                return
                            if self.machine.config.get("type") == "dungeon":
                                self._enter_collect_only_after_dungeon_cooldown(
                                    screen_img, rect, f"target dungeon [{dungeon_names[target_idx - 1]}] is on cooldown"
                                )
                                return
                            if cooldown_until == float('inf'):
                                logging.warning(f"⏳ 貪婪地下城：指定副本 [{dungeon_names[target_idx - 1]}] 處於永久不可打狀態，原地等待中...")
                            else:
                                logging.info(f"⏳ 貪婪地下城：指定副本 [{dungeon_names[target_idx - 1]}] 處於冷卻中，剩餘 {int(cooldown_until - time.time())} 秒，原地等待中...")
                            time.sleep(1.0)
                            return
                            
                        # 2. 如果已在畫面上，進行即時畫面冷卻木牌與解鎖狀態偵測
                        if target_idx in visible_dungeons:
                            is_unavailable = self._check_dungeon_status(
                                screen_img, scale, h_limit, w_limit, target_idx, visible_dungeons
                            )
                            if is_unavailable:
                                if self.machine.config.get("type") == "mix" or self.machine.is_daily_pipeline_active():
                                    self._switch_to_stage_or_back(screen_img, rect, f"畫面偵測指定副本 [{dungeon_names[target_idx - 1]}] 冷卻中")
                                    return
                                if self.machine.config.get("type") == "dungeon":
                                    self._enter_collect_only_after_dungeon_cooldown(
                                        screen_img, rect, f"target dungeon [{dungeon_names[target_idx - 1]}] was detected on cooldown"
                                    )
                                    return
                                time.sleep(1.0)
                                return
                            
                if target_idx is None:
                    is_in_retreat = getattr(self.machine, "stamina_retreat_start_time", None) is not None
                    is_temp_resume = bool(self.machine.config.get("is_dungeon_temporary_resume", False))
                    if is_in_retreat or is_temp_resume or not self._is_stage_farming_allowed():
                        reason = (
                            "體力退避或臨時地下城喚醒期間所有地下城皆已進入冷卻"
                            if (is_in_retreat or is_temp_resume)
                            else "所有地下城皆已進入冷卻且未啟用普通關卡打怪"
                        )
                        self._enter_collect_only_after_dungeon_cooldown(screen_img, rect, reason)
                        return
                    if self.machine.config.get("type") == "dungeon":
                        self._enter_collect_only_after_dungeon_cooldown(
                            screen_img, rect, "all eligible dungeons are on cooldown"
                        )
                        return
                    if self.machine.config.get("type") == "mix" or self.machine.is_daily_pipeline_active():
                        self._switch_to_stage_or_back(screen_img, rect, "地下城頁面偵測到所有地下城均在冷卻中")
                        return

                    logging.warning("⚠️ 貪婪地下城：所有地下城均處於冷卻或不可打狀態，原地等待中...")
                    time.sleep(1.0)
                    return
                    
                # 檢查目標地下城是否已在畫面上
                if target_idx in visible_dungeons:
                    max_loc, t_w, t_h = visible_dungeons[target_idx]
                    click_x = rect["left"] + max_loc[0] + t_w // 2
                    click_y = rect["top"] + max_loc[1] + t_h // 2
                    logging.info(f"👉 貪婪地下城：選擇進入 [{dungeon_names[target_idx - 1]}]，點擊座標 ({click_x}, {click_y})。")
                    self.mouse.click(click_x, click_y)
                    self.machine.current_dungeon_index = target_idx
                    self.machine.is_in_dungeon = True
                    time.sleep(0.2)
                    return
                else:
                    # 不在畫面上，進行左右滑動尋找目標地下城
                    any_visible_idx = list(visible_dungeons.keys())[0]
                    CardListNavigator.swipe_towards_target(self.mouse, rect, any_visible_idx, target_idx, duration=0.8, inertia=False)
                    self.machine.last_dungeon_scroll_time = time.time()
                    time.sleep(1.2)
                    return



        # Global activity switches are inherited by quest-specific stage/dungeon
        # routes. They must not turn a single-route quest into a mix route.
        is_managed_daily = self.machine.is_daily_pipeline_active()
        is_tier4_fallback = bool(self.machine.config.get("is_tier4_fallback", False))
        allow_mix_tab_switching = (not is_managed_daily) or is_tier4_fallback

        if (
            allow_mix_tab_switching
            and self.machine.config.get("type") == "mix"
            and self.machine.has_dungeon_status_context()
        ):
            has_dungeon = self.machine.has_available_dungeon()
            if has_dungeon:
                status_str, avail_names = self.machine.get_dungeon_cooldown_status()
                avail_str = ", ".join(avail_names) if avail_names else "無"
                now = time.time()
                raw_switch = getattr(self.machine, "_last_mix_tab_switch_time", 0.0)
                last_switch = raw_switch if isinstance(raw_switch, (int, float)) else 0.0
                # 若地下城有空位且頁籤尚未開啟，點擊切換至地下城頁籤
                pos_dg, conf_dg = self.matcher.match(screen_img, "dungeons/dungeon.png", threshold=0.60)
                if pos_dg and not dungeon_select_open:
                    if now - last_switch < 1.2:
                        return
                    self.machine._last_mix_tab_switch_time = now
                    logging.info(f"🧭 混合模式：地下城已就緒 (冷卻情形: {status_str} | 判定可挑戰: [{avail_str}])，在活動大廳點擊 [dungeons/dungeon.png] ({conf_dg:.4f}) 切換至地下城頁籤！")
                    self.mouse.click(rect["left"] + pos_dg[0], rect["top"] + pos_dg[1])
                    time.sleep(0.3)
                    return
                nav_path = ["common/door.png", "dungeons/dungeon.png"]
            else:
                # 若未啟用普通關卡打怪 (enable_stage_farming == False) 或處於體力退避/臨時地下城喚醒，直接轉入 COLLECT_ONLY 待機
                if not self._is_stage_farming_allowed():
                    is_in_retreat = getattr(self.machine, "stamina_retreat_start_time", None) is not None
                    is_temp_resume = bool(self.machine.config.get("is_dungeon_temporary_resume", False))
                    reason = (
                        "體力退避或臨時地下城喚醒期間地下城全冷卻，禁止切換至普通關卡"
                        if (is_in_retreat or is_temp_resume)
                        else "地下城全冷卻且未啟用普通關卡打怪 (enable_stage_farming=False)"
                    )
                    self._enter_collect_only_after_dungeon_cooldown(screen_img, rect, reason)
                    return

                # 無可用地下城，退守普通關卡：若尚未處於普通關卡頁籤，點擊 select_stage.png 切換！
                now = time.time()
                raw_switch = getattr(self.machine, "_last_mix_tab_switch_time", 0.0)
                last_switch = raw_switch if isinstance(raw_switch, (int, float)) else 0.0
                status_str, _ = self.machine.get_dungeon_cooldown_status()
                pos_st, conf_st = self.matcher.match(screen_img, "common/select_stage.png", threshold=0.60)
                if pos_st and not stage_select_open:
                    if now - last_switch < 1.2:
                        return
                    self.machine._last_mix_tab_switch_time = now
                    logging.info(f"🧭 混合模式：地下城全冷卻 (冷卻情形: {status_str})，在活動大廳點擊 [common/select_stage.png] ({conf_st:.4f}) 切換至普通關卡頁籤！")
                    self.mouse.click(rect["left"] + pos_st[0], rect["top"] + pos_st[1])
                    time.sleep(0.3)
                    return
                stage_entry = self.machine.config.get("stage_entry", "stages/level6_ice_cave.png")
                stage_target = self.machine.config.get("stage_target", "stages/first_stage.png")
                default_stage_nav = [
                    "common/door.png",
                    "common/select_stage.png",
                    stage_entry,
                    "stages/stage_label.png",
                    stage_target
                ]
                nav_path = self.machine.config.get("stage_navigation_path", default_stage_nav)
        if config_type == "collect_only":
            pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.8, quiet=True)
            if pos_goback:
                logging.info("🧭 [純領取模式] 領取完成後在大廳畫面，點擊 [goback_town.png] 返回城鎮待機...")
                self.mouse.click(rect["left"] + pos_goback[0], rect["top"] + pos_goback[1])
                time.sleep(0.5)
                self.machine.transition_to(self.machine.STATE_COLLECT_ONLY)
                return
            self.machine.transition_to(self.machine.STATE_COLLECT_ONLY)
            return

        if not nav_path:
            self.machine.transition_to(self.machine.STATE_LOBBY)
            return

        # （已於 handle 前段完成頁籤開啟狀態統一對比與判定）

        # 判斷是否已經在關卡內部細節畫面 (提前判定以避免小島在抽屜下方時水平滑動邏輯誤觸)
        in_detail_screen = False
        pos_label = None
        if os.path.exists(os.path.join("templates", "stages/stage_label.png")):
            pos_label, _ = match_current_frame("stages/stage_label.png", threshold=0.70)
        
        # 尋找路徑中是否有魔王關 / 小關卡目標 (first, middle, six, final) 出現在畫面上
        pos_final = None
        target_final_btn = None
        for btn in nav_path:
            if self._is_sub_stage_target(btn):
                target_final_btn = btn
                if os.path.exists(os.path.join("templates", btn)):
                    thresh_btn = get_template_threshold(btn, default=SUB_STAGE_THRESHOLD)
                    pos_f, _ = match_current_frame(btn, threshold=thresh_btn)
                    if pos_f:
                        if "boss_skull" in btn or "skull" in btn:
                            pos_f = self._validate_boss_skull(pos_f, rect, match_current_frame, screen_img=screen_img)
                        if pos_f:
                            pos_final = pos_f
                            self.sub_stage_scroll_attempts = 0
                            # 成功找到目標小關/魔王關，重置其缺失計時器
                            self.machine.__setattr__(f"missing_time_{btn}", 0.0)
                            break

        if pos_label or pos_final:
            in_detail_screen = True

        # 如果處於關卡選擇介面，且目標關卡入口小島尚未出現在畫面上，執行向左滑動清單 (只在尚未進入細節畫面時執行)
        if self.machine.config.get("type") in ["stage", "mix"] and stage_select_open and not in_detail_screen:
            target_level_btn = None
            for btn in nav_path:
                is_sub = self._is_sub_stage_target(btn)
                if not is_sub and "level" in btn and "entry" not in btn:
                    target_level_btn = btn
                    break
            if target_level_btn and os.path.exists(os.path.join("templates", target_level_btn)):
                    # === 確保地圖滾動完全靜止後才開始進行圖像辨識，避免在動畫中進行錯誤判定 ===
                    # 在單元測試中，我們允許繞過此時間限制，以便連續執行同步模擬
                    import sys
                    is_testing = "unittest" in sys.modules
                    last_scroll = getattr(self.machine, "last_stage_scroll_time", 0.0)
                    if not isinstance(last_scroll, (int, float)):
                        last_scroll = 0.0
                    time_diff = time.time() - last_scroll
                    if time_diff < 2.2 and not is_testing:
                        logging.info(f"⌛ 剛執行過水平滑動 (僅過 {time_diff:.1f} 秒)，等待地圖滾動完全靜止後再進行圖像辨識...")
                        return

                    pos_target, _ = self.matcher.match(screen_img, target_level_btn, threshold=0.80)
                    if pos_target:
                        # 成功找到目標小島，重置缺失計時器與水平滾動計數
                        self.machine.__setattr__(f"missing_time_{target_level_btn}", 0.0)
                        self.machine.horizontal_scroll_count = 0
                    else:
                        # 目標關卡尚未在畫面上看見，先等待 1.5 秒讓動畫加載穩定後再滑動
                        missing_time = getattr(self.machine, f"missing_time_{target_level_btn}", 0.0)
                        if not isinstance(missing_time, (int, float)):
                            missing_time = 0.0
                        if missing_time == 0.0:
                            self.machine.__setattr__(f"missing_time_{target_level_btn}", time.time())
                            logging.info(f"⌛ 尋路中：目標關卡 [{target_level_btn}] 暫時未出現在畫面上，等待載入與穩定中...")
                            return
                        elif time.time() - missing_time < 1.5:
                            # 仍處於 1.5 秒等待緩衝期內，暫不執行滑動
                            return

                        scroll_count = getattr(self.machine, "horizontal_scroll_count", 0)
                        
                        if scroll_count >= 8:
                            logging.warning(f"⚠️ 警告：已執行左右滑動各 4 次但仍未發現目標關卡 [{target_level_btn}]，嘗試點擊返回大廳以重設流程...")
                            pos_back = None
                            if os.path.exists(os.path.join("templates", "goback_town.png")):
                                pos_back, conf_back = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
                            if pos_back:
                                logging.info(f"👉 偵測到返回按鈕 [goback_town.png] (信心度: {conf_back:.4f})，點擊返回。")
                                self.mouse.click(rect["left"] + pos_back[0], rect["top"] + pos_back[1])
                                self.machine.horizontal_scroll_count = 0
                                time.sleep(1.2)
                            else:
                                logging.warning("⚠️ 無法定位返回按鈕 [goback_town.png]，重置滑動計數原地等待...")
                                self.machine.horizontal_scroll_count = 0
                                time.sleep(1.0)
                            return

                        if scroll_count < 6:
                            logging.info(f"🧭 尋路中：已在關卡選擇介面，但未見目標關卡 [{target_level_btn}]，執行向左滑動清單 (地圖向右移) 第 {scroll_count + 1}/6 次...")
                            start_x = rect["left"] + int(rect["width"] * 0.62)
                            end_x = rect["left"] + int(rect["width"] * 0.38)
                            self.machine.horizontal_scroll_count = scroll_count + 1
                        else:
                            logging.info(f"🧭 尋路中：已在關卡選擇介面，但仍未見目標關卡 [{target_level_btn}]，執行向右滑動清單 (地圖向左移) 第 {scroll_count - 5}/6 次...")
                            start_x = rect["left"] + int(rect["width"] * 0.38)
                            end_x = rect["left"] + int(rect["width"] * 0.62)
                            self.machine.horizontal_scroll_count = scroll_count + 1

                        y_pos = rect["top"] + int(rect["height"] * 0.3)
                        self.mouse.drag(start_x, y_pos, end_x, y_pos, duration=0.8, inertia=False)
                        self.machine.last_stage_scroll_time = time.time()
                        # 增加靜止等待時間，確保清單滑動動畫完全停止後再進行下一幀偵測與點擊
                        time.sleep(1.2)
                        return

        # 優先檢查：若人在城鎮大門 (common/door.png 相似度 >= 0.90)，且尚未開啟關卡/地下城選單且未在大廳，優先點擊大門進入
        if "common/door.png" in nav_path and not stage_select_open and not dungeon_select_open and not in_detail_screen and not scene.is_lobby:
            pos_door, conf_door = self.matcher.match(screen_img, "common/door.png", threshold=0.90, brightness_threshold=0.70)
            if pos_door:
                click_x = rect["left"] + pos_door[0]
                click_y = rect["top"] + pos_door[1]
                logging.info(f"🚪 [尋路] 偵測到城鎮大門 [common/door.png] (信心度: {conf_door:.4f})，優先點擊大門進入選單...")
                self.mouse.click(click_x, click_y)
                time.sleep(0.3)
                return

        # 逆序掃描導航路徑中可見的按鈕，點擊最深層的那個
        active_tabs = []
        if stage_select_open:
            active_tabs.append("stage")
        if dungeon_select_open:
            active_tabs.append("dungeon")

        filtered_nav_path = filter_navigation_path(nav_path, active_tabs, is_lobby=scene.is_lobby)

        clicked_any = False
        for btn in reversed(filtered_nav_path):

            is_sub_stage_target = self._is_sub_stage_target(btn)

            # 如果已經進入了關卡內部細節畫面，跳過小島選擇入口按鈕以免誤點 (僅跳過非目標子關卡的 level 小島)
            if in_detail_screen and not is_sub_stage_target and "level" in btn and "entry" not in btn:
                continue

            if is_sub_stage_target:
                thresh = get_template_threshold(btn, default=SUB_STAGE_THRESHOLD)
                b_thresh = 0.0
            elif btn == "exit_battle.png":
                thresh = get_template_threshold(btn, default=EXIT_BATTLE_THRESHOLD)  # 0.88 防範城鎮背景產生虛假誤匹配
                b_thresh = 0.70
            elif "door" in btn:
                thresh = get_template_threshold(btn, default=0.88)  # 0.88 防範大廳拱門按鈕誤匹配
                b_thresh = 0.70
            elif "dungeon" in btn or "select_stage" in btn or "entry" in btn or "stage_label" in btn or "level" in btn:
                thresh = get_template_threshold(btn, default=ENTRY_THRESHOLD)
                b_thresh = 0.70
            else:
                thresh = get_template_threshold(btn, default=DEFAULT_THRESHOLD)
                b_thresh = 0.70
            pos, conf = match_current_frame(btn, threshold=thresh, brightness_threshold=b_thresh)
            if pos:
                if "boss_skull" in btn or "skull" in btn:
                    pos = self._validate_boss_skull(pos, rect, match_current_frame, screen_img=screen_img)
            if pos:
                if btn == "stages/stage_label.png":
                    if self._handle_sub_stage_scroll(
                        rect,
                        target_final_btn,
                        match_current_frame,
                        filtered_nav_path,
                        screen_img=screen_img,
                    ):
                        clicked_any = True
                        break
                    return
                else:
                    if is_sub_stage_target:
                        self.sub_stage_scroll_attempts = 0
                    click_x = rect["left"] + pos[0]
                    click_y = rect["top"] + pos[1]
                    if not is_sub_stage_target and "level" in btn and "entry" not in btn:
                        height_to_use = rect.get("height") or screen_img.shape[0] or 1080
                        scale_y = height_to_use / 1080.0
                        offset_y = int(160 * scale_y)
                        click_y -= offset_y
                        logging.info(f"🧭 尋路中：在畫面中找到關卡小島按鈕 [{btn}] (信心度: {conf:.4f})，套用向上偏移 {offset_y} 像素點擊島嶼本體。")
                    else:
                        logging.info(f"🧭 尋路中：在畫面中找到 [{btn}] (信心度: {conf:.4f})，點擊按鈕中心座標 ({click_x}, {click_y})。")
                    self.mouse.click(click_x, click_y)
                    clicked_any = True
                    time.sleep(0.03) # 等待跳轉動畫
                    break

        if not clicked_any:
            # 備用邏輯：若在普通關卡模式下，已進入關卡細節畫面但未看見目標子關卡，執行自適應滑動
            if self.machine.config.get("type") == "stage":
                if pos_label and not pos_final and target_final_btn:
                    if self._handle_sub_stage_scroll(
                        rect,
                        target_final_btn,
                        match_current_frame,
                        filtered_nav_path,
                    ):
                        return

            # 其他情況 (例如動畫播放、切換關卡加載黑屏)，原地等待畫面載入
            logging.info("⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...")
