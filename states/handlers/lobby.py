import logging
import os
import time

from states.handlers.base import BaseStateHandler
from states.navigation_routing import (
    NavigationDecisionExecutor,
    resolve_navigation_context,
)
from utils.scene_detector import SceneDetector


class LobbyHandler(BaseStateHandler):
    def __init__(self, machine):
        super().__init__(machine)
        self.start_first_click_time = None
        self.last_start_click_time = None
        self.start_retry_interval = 1.0
        self.start_max_timeout = 5.0
        self.scene_detector = SceneDetector(self.matcher)

    def reset_state(self):
        self.start_first_click_time = None
        self.last_start_click_time = None

    def handle(self, screen_img, rect):
        """Handle lobby prerequisites and start-stage confirmation."""
        for feat in ["common/auto.png", "battle/battle_features_1.png", "battle/battle_features_2.png"]:
            if not os.path.exists(os.path.join("templates", feat)):
                continue
            threshold = 0.65 if feat == "common/auto.png" else 0.70
            pos, confidence = self.matcher.match(screen_img, feat, threshold=threshold, quiet=True)
            if pos:
                logging.info("Battle feature [%s] detected (confidence %.4f); entering BATTLE.", feat, confidence)
                self.reset_state()
                self.machine.battle_start_time = time.time()
                self.machine.transition_to(self.machine.STATE_BATTLE)
                return

        for popup_btn in ["common/confirm.png", "common/ok.png"]:
            if not os.path.exists(os.path.join("templates", popup_btn)):
                continue
            pos, confidence = self.matcher.match(screen_img, popup_btn, threshold=0.90)
            if pos:
                logging.info("Lobby popup [%s] detected (confidence %.4f); dismissing it.", popup_btn, confidence)
                self.reset_state()
                self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                time.sleep(0.5)
                return

        # Clicking Start commits an asynchronous UI action.  While that action
        # is still waiting for visual confirmation, newly latched scheduler
        # work (for example the periodic bread collection) must not preempt it.
        # Keep polling the committed action until it succeeds or times out;
        # pending work remains latched and will be handled at the next safe
        # navigation/result boundary.
        if self.start_first_click_time is not None:
            self._handle_start_button(screen_img, rect)
            return

        if self._handle_preconditions(screen_img, rect):
            return

        scene = self.scene_detector.detect(screen_img, machine=self.machine)
        routing = resolve_navigation_context(self.machine, scene)
        executor = NavigationDecisionExecutor(self)
        if executor.execute(
            routing,
            screen_img,
            rect,
            start_callback=lambda: self._handle_start_button(screen_img, rect),
        ):
            return
        self._handle_start_button(screen_img, rect)

    def _handle_preconditions(self, screen_img, rect):
        """Handle flows that take priority over normal stage farming."""
        if self.machine.config.get("type") == "bag_clean":
            logging.info("Lobby: bag-clean mode; entering BAG_CLEANING.")
            self.reset_state()
            self.machine.transition_to(self.machine.STATE_BAG_CLEANING)
            return True

        if self.machine.need_bag_cleaning:
            logging.info("Lobby: bag cleaning is required; entering BAG_CLEANING.")
            self.reset_state()
            self.machine.transition_to(self.machine.STATE_BAG_CLEANING)
            return True

        is_lord_boss_mode = (
            self.machine.config.get("type") == "lord_boss"
            or getattr(self.machine, "current_town_subflow", None) == "lord_boss"
        )
        if is_lord_boss_mode:
            daily_manager = getattr(self.machine, "daily_manager", None)
            if daily_manager and self.machine.has_available_selected_lord_boss():
                logging.info("Lobby: available lord boss found; entering LORD_BOSS.")
                self.reset_state()
                self.machine.transition_to(self.machine.STATE_LORD_BOSS)
                return True

            logging.info("Lobby: lord-boss flow complete; proceeding to the next town subflow.")
            if daily_manager and hasattr(daily_manager, "record_subflow_completed"):
                daily_manager.record_subflow_completed("lord_boss")
            self.reset_state()
            self.machine.pop_and_next_town_subflow()
            return True

        stage_farming_enabled = self.machine.config.get("enable_stage_farming", False)
        if not stage_farming_enabled and not getattr(self.machine, "is_in_dungeon", False):
            logging.info("Lobby: stage farming disabled; entering COLLECT_ONLY.")
            pos_back, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.75, quiet=True)
            if pos_back:
                self.mouse.click(rect["left"] + pos_back[0], rect["top"] + pos_back[1])
                time.sleep(0.5)
            self.reset_state()
            self.machine.transition_to(self.machine.STATE_COLLECT_ONLY)
            return True

        return False

    def _handle_start_button(self, screen_img, rect):
        """Re-click the start button without blocking until it disappears or times out."""
        lobby_btn = self.machine.config.get("lobby_start_btn", "stages/start.png")
        pos, confidence = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        now = time.time()

        if not pos:
            if self.start_first_click_time is not None:
                logging.info("Lobby start button disappeared; entering LOADING.")
                self.reset_state()
                self.notify_ui_progress()
                self.machine.last_lobby_start_click_time = now
                self.machine.run_count += 1
                self.machine.dungeon_defeat_count = 0
                self.machine.transition_to(self.machine.STATE_LOADING)
                return

            logging.info("Lobby start button is absent before a click; leaving the lobby flow.")
            next_state = (
                self.machine.STATE_COLLECT_ONLY
                if self.machine.is_in_collect_only_mode()
                else self.machine.STATE_NAVIGATING
            )
            self.machine.transition_to(next_state)
            return

        if self.start_first_click_time is None:
            logging.info("Lobby start button [%s] detected (confidence %.4f); clicking.", lobby_btn, confidence)
            self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
            self.start_first_click_time = now
            self.last_start_click_time = now
            return

        total_elapsed = now - self.start_first_click_time
        if total_elapsed > self.start_max_timeout:
            logging.warning(
                "Lobby start button remained visible for %.1fs; resetting click tracking.",
                total_elapsed,
            )
            self.reset_state()
            return

        if now - self.last_start_click_time >= self.start_retry_interval:
            logging.info(
                "Lobby start button is still visible after %.1fs; retrying click.",
                total_elapsed,
            )
            self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
            self.last_start_click_time = now
