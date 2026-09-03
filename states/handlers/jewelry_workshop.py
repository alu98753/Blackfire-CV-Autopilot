import time
import os
import sys
import logging
from states.handlers.base import BaseStateHandler

class JewelryWorkshopHandler(BaseStateHandler):
    """
    珠寶加工廠出售 (Jewelry Workshop) 處理器：
    1. 於城鎮點擊珠寶加工廠建築 (Jewelry_workshop.png) 進入建築。
    2. 點擊出售選單按鈕 (sell_out.png) 進入出售選單。
    3. 商品輪詢與出售子流程 (SELL_MENU_OPEN)：
       - 遍歷 goods 模板 (Sandworm_scales, Spider_silk, Spider_venom_glands, The_cloth_wrapped_around_the_dead, Warcraft_Fang, lizard_skin, scrap)。
       - 頂層未找到 ➔ 向下滑動兩下 ➔ 若仍未找到 ➔ 向上滑動兩下還原高度 ➔ 繼續下一個商品。
       - 找到商品 ➔ 點擊商品 ➔ 點擊 sell.png ➔ 點擊 sell_max.png ➔ 點擊 ok.png / confirm.png。
    4. 退出階段 (ALL_DONE_EXITING)：
       - 點擊離開建築按鈕 (exitfromhouse_and_to_town.png) 返回城鎮。
       - 完成獨立模式並安全退出程式。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, ENTERED_BUILDING, SELL_MENU_OPEN, ALL_DONE_EXITING
        self.last_action_time = 0.0
        self.current_goods_idx = 0
        self.goods_scroll_state = "TOP"  # TOP, SCROLLED_DOWN
        self.item_sub_step = "SEARCH"    # SEARCH, CLICKED_ITEM, CLICKED_SELL, CLICKED_MAX
        self.repeat_sell_count = 0
        self.pre_tidy_done = False
        from states.handlers.bag_cleaning import BagCleaningHandler
        self.bag_handler = BagCleaningHandler(machine)
        self.bag_handler.matcher = self.matcher
        self.bag_handler.mouse = self.mouse
        self.bag_handler.capturer = self.capturer

    def reset_state(self):
        self.step_phase = "INIT"
        self.last_action_time = 0.0
        self.current_goods_idx = 0
        self.goods_scroll_state = "TOP"
        self.item_sub_step = "SEARCH"
        self.repeat_sell_count = 0
        self.pre_tidy_done = False

    def _record_completion(self):
        """記錄 DailyManager 珠寶加工廠今日已完成"""
        dm = getattr(self.machine, "daily_manager", None)
        if dm and hasattr(dm, "record_subflow_completed"):
            dm.record_subflow_completed("jewelry_workshop")

    def _get_enabled_goods(self, goods_dir, goods_settings):
        """
        掃描 goods_dir (含顏色子資料夾 gray/, green/, blue/, purple/ 或直接平鋪檔案)，
        並根據 goods_settings 字典中各顏色區塊下每一個商品的 True/False 狀態，
        整理出需要出售的相對模板路徑清單。
        """
        full_dir = os.path.join("templates", goods_dir)
        if not os.path.exists(full_dir):
            return []

        if not isinstance(goods_settings, dict):
            return []

        enabled_goods = []
        for color, items in goods_settings.items():
            if isinstance(items, dict):
                for item_name, is_enabled in items.items():
                    if is_enabled:
                        rel_path_sub = os.path.join(color, item_name)
                        if os.path.exists(os.path.join(full_dir, f"{rel_path_sub}.png")):
                            enabled_goods.append(rel_path_sub)
                        elif os.path.exists(os.path.join(full_dir, f"{item_name}.png")):
                            enabled_goods.append(item_name)
            elif isinstance(items, bool) and items:
                # 平鋪格式相容
                item_name = color
                if os.path.exists(os.path.join(full_dir, f"{item_name}.png")):
                    enabled_goods.append(item_name)

        return enabled_goods

    def _ensure_in_town(self, screen_img, rect=None):
        """
        獨立導航輔助函式：若目前位於大廳 (看得到 goback_town.png)，點擊返回城鎮 (配對確認直到消失)。
        """
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
        if pos_goback:
            logging.info("💎 [珠寶加工廠] 偵測到目前處於大廳畫面，點擊 [goback_town.png] 返回城鎮 (配對確認直到消失)...")
            left = rect["left"] if rect else 0
            top = rect["top"] if rect else 0
            self.click_and_wait_until_gone("goback_town.png", left + pos_goback[0], top + pos_goback[1], rect)
            self.last_action_time = time.time()
            return False
        return True

    def handle(self, screen_img=None, rect=None):
        if screen_img is None and self.capturer:
            rect = rect or self.capturer.get_window_rect()
            if rect:
                screen_img = self.capturer.capture(rect)
        if screen_img is None:
            return

        # 防死鎖門禁：若獨立模式或城鎮流水線已不需要珠寶加工廠出售 且處於 INIT 階段，直接 return！
        cfg_type = self.machine.config.get("type") if getattr(self.machine, "config", None) else None
        is_needed = getattr(self.machine, "need_jewelry_workshop", False) or cfg_type == "jewelry_workshop"
        if not is_needed and self.step_phase == "INIT":
            return

        now = time.time()
        if now - self.last_action_time < 0.6:
            return

        # 🛡️ 場景感知防護 (Scene Guard)：若非 INIT/EXITING 階段但畫面上已看見 common/door.png (確定在城鎮 Town)，代表已離場
        if self.step_phase in ["SELL_MENU_OPEN", "ENTERED_BUILDING"]:
            pos_door_chk, conf_door_chk = self.matcher.match(screen_img, "common/door.png", threshold=0.80)
            if pos_door_chk:
                logging.warning(f"💎 [珠寶加工廠] 防護攔截 - 處於 [{self.step_phase}] 階段但畫面上已看見城鎮大門 [common/door.png] ({conf_door_chk:.4f})，結束出售流程。")
                self.reset_state()
                self.machine.need_jewelry_workshop = False
                self._record_completion()
                self.last_action_time = now
                self.machine.pop_and_next_town_subflow()
                return

        # 優先檢查是否需要從小圖示大廳退回城鎮
        if not self._ensure_in_town(screen_img, rect):
            return


        left = rect["left"] if rect else 0
        top = rect["top"] if rect else 0

        cfg = self.machine.config or {}
        building_btn = cfg.get("building_btn", "town_building/Jewelry_workshop/Jewelry_workshop.png")
        sell_out_btn = cfg.get("sell_out_btn", "town_building/sell_out.png")
        sell_btn = cfg.get("sell_btn", "town_building/sell.png")
        sell_max_btn = cfg.get("sell_max_btn", "town_building/sell_max.png")
        exit_building_btn = cfg.get("exit_building_btn", "town_building/exitfromhouse_and_to_town.png")

        goods_settings = cfg.get("sell_goods", cfg.get("goods_settings"))
        if goods_settings is None:
            from config import GAME_CONFIGS
            workshop_config = GAME_CONFIGS.get("jewelry_workshop", {})
            goods_settings = workshop_config.get(
                "sell_goods", workshop_config.get("goods_settings", {})
            )
        goods_dir = cfg.get("goods_dir", "town_building/Jewelry_workshop/goods")

        # 整理要出售的商品清單 (支援品質子目錄 gray/green/blue/purple 與特例覆蓋)
        enabled_goods = self._get_enabled_goods(goods_dir, goods_settings)

        # 0. 通用防呆：若出現 common/confirm.png 彈窗，點擊確認
        conf_name = "common/confirm.png"
        if os.path.exists(os.path.join("templates", conf_name)):
            pos_conf, _ = self.matcher.match(screen_img, conf_name, threshold=0.8)
            if pos_conf:
                logging.info(f"💎 [珠寶加工廠] 點擊確認按鈕 [{conf_name}]...")
                self.mouse.click(left + pos_conf[0], top + pos_conf[1])
                self.last_action_time = now
                self.machine.notify_ui_progress()

                return

        # =========================================================================
        # 1. 出售選單開啟狀態 (SELL_MENU_OPEN) - Goods 滑動搜尋與出售閉環
        # =========================================================================
        if self.step_phase == "SELL_MENU_OPEN":
            if self.current_goods_idx >= len(enabled_goods):
                logging.info("💎 [珠寶加工廠] 所有指定商品清單比對與出售處理完畢！進入退出階段...")
                # 若當前仍處於向下滾動狀態，平滑拖曳滾回頂端
                if self.goods_scroll_state == "SCROLLED_DOWN":
                    center_x = left + (rect["width"] // 2 if rect and "width" in rect else 960)
                    height = rect["height"] if rect and "height" in rect else 1080
                    drag_start_y = top + int(height * 0.75)
                    drag_end_y = top + int(height * 0.25)
                    self.mouse.drag(center_x, drag_end_y, center_x, drag_start_y, duration=0.5, inertia=False)
                    self.goods_scroll_state = "TOP"
                    time.sleep(0.3)
                self.step_phase = "ALL_DONE_EXITING"
                self.last_action_time = now
                self.machine.notify_ui_progress()

                return

            goods_name = enabled_goods[self.current_goods_idx]
            template_path = os.path.join(goods_dir, f"{goods_name}.png")

            # 滾動與拖曳座標計算 (由畫面 60% 高度拖曳至 40% 高度)
            center_x = left + (rect["width"] // 2 if rect and "width" in rect else 960)
            height = rect["height"] if rect and "height" in rect else 1080
            drag_start_y = top + int(height * 0.75)
            drag_end_y = top + int(height * 0.25)

            # 步驟 A: 嘗試在當前畫面匹配目標商品
            pos_goods = None
            conf_goods = 0.0
            goods_threshold = cfg.get("goods_threshold", 0.75)
            if os.path.exists(os.path.join("templates", template_path)):
                pos_goods, conf_goods = self.matcher.match(screen_img, template_path, threshold=goods_threshold)

            # 若未找到商品且當前在頂部，執行向下滑動 (向上拖曳 200 像素)
            if not pos_goods and self.goods_scroll_state == "TOP":
                logging.info(f"💎 [珠寶加工廠] 頂層未找到商品 [{goods_name}] (門檻: {goods_threshold})，執行平滑拖曳向下滑動再次搜尋...")
                self.mouse.drag(center_x, drag_start_y, center_x, drag_end_y, duration=0.5, inertia=False)
                self.goods_scroll_state = "SCROLLED_DOWN"
                time.sleep(0.8)
                self.last_action_time = now
                self.machine.notify_ui_progress()

                return

            # 若向下滑動後仍未找到商品 ➔ 認定背包無此商品 ➔ 向上滑動還原高度 (向下拖曳 200 像素) ➔ 繼續下一個商品
            if not pos_goods and self.goods_scroll_state == "SCROLLED_DOWN":
                logging.info(f"💎 [珠寶加工廠] 滑動後仍未發現商品 [{goods_name}]，判定未持有。平滑拖曳還原原位高度並比對下一個商品...")
                self.mouse.drag(center_x, drag_end_y, center_x, drag_start_y, duration=0.5, inertia=False)
                self.goods_scroll_state = "TOP"
                self.repeat_sell_count = 0
                self.current_goods_idx += 1
                time.sleep(0.8)
                self.last_action_time = now
                self.machine.notify_ui_progress()

                return

            # 若找到商品，執行出售流程
            if pos_goods:
                logging.info(f"💎 [珠寶加工廠] 發現可出售商品 [{goods_name}] (信心度: {conf_goods:.4f})，點擊選擇該商品...")
                self.mouse.click(left + pos_goods[0], top + pos_goods[1])
                time.sleep(0.3)

                latest_img = self.capturer.capture(rect) if (self.capturer and rect) else screen_img
                if latest_img is not None:
                    # 點擊 sell.png
                    pos_sell, _ = self.matcher.match(latest_img, sell_btn, threshold=0.75)
                    if pos_sell:
                        logging.info(f"💎 [珠寶加工廠] 點擊出售按鈕 [{sell_btn}]...")
                        self.mouse.click(left + pos_sell[0], top + pos_sell[1])
                        time.sleep(0.2)
                        latest_img = self.capturer.capture(rect) if (self.capturer and rect) else latest_img

                    # 點擊 sell_max.png
                    pos_max, _ = self.matcher.match(latest_img, sell_max_btn, threshold=0.75)
                    if pos_max:
                        logging.info(f"💎 [珠寶加工廠] 點擊 MAX 數量按鈕 [{sell_max_btn}]...")
                        self.mouse.click(left + pos_max[0], top + pos_max[1])
                        time.sleep(0.2)
                        latest_img = self.capturer.capture(rect) if (self.capturer and rect) else latest_img

                    # 點擊 confirm/ok (配對確認直到彈窗徹底消失)
                    for conf_btn in ["common/ok.png", "common/confirm.png"]:
                        if os.path.exists(os.path.join("templates", conf_btn)):
                            pos_c, _ = self.matcher.match(latest_img, conf_btn, threshold=0.75)
                            if pos_c:
                                logging.info(f"💎 [珠寶加工廠] 點擊確認出售按鈕 [{conf_btn}] (配對確認直到消失)...")
                                self.click_and_wait_until_gone(conf_btn, left + pos_c[0], top + pos_c[1], rect, post_delay=0.3)
                                time.sleep(0.3)
                                latest_img = self.capturer.capture(rect) if (self.capturer and rect) else latest_img
                                break

                    # 二次防呆：若出現第二層 confirm/ok 彈窗 (如 ok 點完後又彈 confirm)，連續清理
                    for conf_btn in ["common/confirm.png", "common/ok.png"]:
                        if latest_img is not None and os.path.exists(os.path.join("templates", conf_btn)):
                            pos_c2, _ = self.matcher.match(latest_img, conf_btn, threshold=0.75)
                            if pos_c2:
                                logging.info(f"💎 [珠寶加工廠] 點擊二次確認按鈕 [{conf_btn}] (配對確認直到消失)...")
                                self.click_and_wait_until_gone(conf_btn, left + pos_c2[0], top + pos_c2[1], rect, post_delay=0.3)
                                time.sleep(0.3)

                # 賣完一次後，確保彈窗與動畫已完全消失沉澱，再重新擷取畫面二次比對
                time.sleep(0.4)
                self.repeat_sell_count += 1
                max_repeat = cfg.get("max_repeat_per_item", 5)

                post_sell_img = self.capturer.capture(rect) if (self.capturer and rect) else None
                still_has_goods = False
                if post_sell_img is not None and os.path.exists(os.path.join("templates", template_path)):
                    pos_goods_again, conf_again = self.matcher.match(post_sell_img, template_path, threshold=goods_threshold)
                    if pos_goods_again:
                        still_has_goods = True

                if still_has_goods and self.repeat_sell_count < max_repeat:
                    logging.info(f"💎 [珠寶加工廠] 同一商品 [{goods_name}] 畫面中仍有可出售項目 (第 {self.repeat_sell_count} 次出售)，繼續對該商品執行出售...")
                    self.last_action_time = now
                    self.machine.notify_ui_progress()
                    return


                # 若畫面不再有該商品，或達到最大重複次數 (max_repeat)
                if still_has_goods and self.repeat_sell_count >= max_repeat:
                    logging.warning(f"💎 [珠寶加工廠] 商品 [{goods_name}] 已連續出售 {self.repeat_sell_count} 次，達到安全上限 {max_repeat} 次，進行換項...")

                # 若有向下滾動，賣完後向上還原滾動高度
                if self.goods_scroll_state == "SCROLLED_DOWN":
                    self.mouse.drag(center_x, drag_end_y, center_x, drag_start_y, duration=0.5, inertia=False)
                    self.goods_scroll_state = "TOP"
                    time.sleep(0.2)

                self.repeat_sell_count = 0
                self.current_goods_idx += 1
                self.last_action_time = now
                self.machine.notify_ui_progress()

                return

            return

        # =========================================================================
        # 2. 退出階段 (ALL_DONE_EXITING)
        # =========================================================================
        if self.step_phase == "ALL_DONE_EXITING":
            pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
            pos_building, _ = self.matcher.match(screen_img, building_btn, threshold=0.75)
            if pos_door or pos_building:
                logging.info("✅ [珠寶加工廠] 偵測到目前已處於城鎮大門畫面，視為已退回城鎮，完成出售流程！")
                self.reset_state()
                self.machine.need_jewelry_workshop = False
                self._record_completion()
                self.last_action_time = now
                self.machine.notify_ui_progress()

                logging.info("💎 [珠寶加工廠] 出售流程完成，消費城鎮佇列中的下一個任務...")
                self.machine.pop_and_next_town_subflow()
                return

            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
            if pos_quit:
                logging.info("💎 [珠寶加工廠] 點擊關閉視窗 [common/quit.png]...")
                self.mouse.click(left + pos_quit[0], top + pos_quit[1])
                self.last_action_time = now
                self.machine.notify_ui_progress()

                return

            pos_exit, _ = self.matcher.match(screen_img, exit_building_btn, threshold=0.75)
            if pos_exit:
                logging.info(f"💎 [珠寶加工廠] 點擊離開建築按鈕 [{exit_building_btn}] 返回城鎮...")
                self.mouse.click(left + pos_exit[0], top + pos_exit[1])
                self.reset_state()
                self.machine.need_jewelry_workshop = False
                self._record_completion()
                self.last_action_time = now
                self.machine.notify_ui_progress()

                logging.info("💎 [珠寶加工廠] 出售流程完成，消費城鎮佇列中的下一個任務...")
                self.machine.pop_and_next_town_subflow()
                return
            return

        # =========================================================================
        # 3. 城鎮與建築內起點階段 (INIT / ENTERED_BUILDING)
        # =========================================================================
        # 3.1 檢查是否已開啟出售選單 (畫面上有 sell_btn 或 sell_max_btn)
        pos_sell_chk, _ = self.matcher.match(screen_img, sell_btn, threshold=0.75)
        pos_max_chk, _ = self.matcher.match(screen_img, sell_max_btn, threshold=0.75)
        if pos_sell_chk or pos_max_chk:
            logging.info("💎 [珠寶加工廠] 辨識到目前已處於出售選單畫面，直接進入出售階段...")
            self.step_phase = "SELL_MENU_OPEN"
            self.current_goods_idx = 0
            self.goods_scroll_state = "TOP"
            self.last_action_time = now
            return

        # 3.2 檢查是否已在建築內部 (sell_out.png 與 exitfromhouse_and_to_town.png 同時存在)
        pos_sell_out, conf_so = self.matcher.match(screen_img, sell_out_btn, threshold=0.80)
        pos_exit_init, conf_exit = self.matcher.match(screen_img, exit_building_btn, threshold=0.80)
        if pos_sell_out and pos_exit_init:
            logging.info(f"💎 [珠寶加工廠] 辨識到已在建築物內部 (sell_out.png 可見)，點擊開啟出售選單...")
            self.mouse.click(left + pos_sell_out[0], top + pos_sell_out[1])
            self.step_phase = "SELL_MENU_OPEN"
            self.current_goods_idx = 0
            self.goods_scroll_state = "TOP"
            time.sleep(0.8)
            self.last_action_time = now
            return

        # 3.3 城鎮點擊珠寶加工廠建築 (Jewelry_workshop.png) (進場前優先發起城鎮背包預先整理)
        if is_needed:
            # 3.3.1 若目前背包已處於開啟狀態（不受城鎮大門/建築被背包遮擋影響），優先執行「整理」與「退出」
            if self.bag_handler.is_backpack_opened(screen_img):
                if not getattr(self.machine, "bag_tidied", False):
                    if self.bag_handler.tidy_backpack(screen_img, rect):
                        self.last_action_time = now
                        return
                else:
                    pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.7)
                    if pos_quit:
                        logging.info("💎 [珠寶加工廠] 城鎮背包預先整理完畢，點擊關閉退出背包...")
                        self.click_and_wait_until_gone("common/quit.png", left + pos_quit[0], top + pos_quit[1], rect, threshold=0.7)
                    self.machine.bag_tidied = False
                    self.machine.bag_opened_clicked = False
                    self.pre_tidy_done = True
                    self.last_action_time = now
                    return

            # 3.3.2 若背包未開啟，且處於城鎮 (pos_building & pos_door 可見)
            pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
            pos_building, conf_building = self.matcher.match(screen_img, building_btn, threshold=0.65, brightness_threshold=0.70, quiet=True)
            if pos_building and pos_door:
                if not self.pre_tidy_done:
                    logging.info("💎 [珠寶加工廠] 進入前執行城鎮背包預先整理，優先開啟背包...")
                    if self.bag_handler.open_backpack(screen_img, rect):
                        self.last_action_time = now
                        return

                logging.info(f"💎 [珠寶加工廠] 於城鎮發現珠寶加工廠建築 [{building_btn}] (信心度: {conf_building:.4f})，點擊進入...")
                self.mouse.click(left + pos_building[0], top + pos_building[1])
                self.step_phase = "ENTERED_BUILDING"
                self.last_action_time = now
                self.machine.notify_ui_progress()

                return

        if pos_sell_out:
            logging.info(f"💎 [珠寶加工廠] 發現出售選單按鈕 [{sell_out_btn}]，點擊開啟選單...")
            self.mouse.click(left + pos_sell_out[0], top + pos_sell_out[1])
            self.step_phase = "SELL_MENU_OPEN"
            self.current_goods_idx = 0
            self.goods_scroll_state = "TOP"
            time.sleep(0.8)
            self.last_action_time = now
            return
