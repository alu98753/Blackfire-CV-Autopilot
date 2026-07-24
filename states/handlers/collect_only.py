import os
import time
import logging
from states.handlers.base import BaseStateHandler

class CollectOnlyHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        定時領取模式的狀態處理器：
        - 檢查是否需要領取鑽石或體力。
        - 如果需要領取鑽石，在城鎮則進入領取；在大廳則點擊返回城鎮。
        - 如果需要領取體力，在大廳則進入領取；在城鎮則點擊門進入大廳。
        - 如果目前無領取任務，在大廳則自動返回城鎮，在城鎮則維持原地待機。
        """
        # 0. 檢查體力不足退避恢復機制
        if self.machine.original_config is not None and self.machine.stamina_retreat_start_time is not None:
            retreat_hours = self.machine.config.get("stamina_retreat_duration", 4.0)
            retreat_seconds = float(retreat_hours) * 3600.0
            elapsed = time.time() - self.machine.stamina_retreat_start_time
            
            # 每隔一段時間輸出退避剩餘時間
            now = time.time()
            last_log = getattr(self, "last_log_time", 0.0)
            from config import GLOBAL_SETTINGS
            default_diamond_cd = GLOBAL_SETTINGS.get("default_diamond_cd", 7200.0)
            diamond_cd = self.machine.config.get("diamond_cd", default_diamond_cd)
            default_bread_cd = 7200.0 if self.machine.config.get("type") == "collect_only" else GLOBAL_SETTINGS.get("default_bread_cd", 1800.0)
            bread_cd = self.machine.config.get("bread_cd", default_bread_cd)
            log_interval = min(300.0, diamond_cd, bread_cd)
            
            if now - last_log >= log_interval or last_log == 0.0:
                self.last_log_time = now
                remaining = max(0.0, retreat_seconds - elapsed)
                h = int(remaining // 3600)
                m = int((remaining % 3600) // 60)
                s = int(remaining % 60)
                time_str = f"{h}小時{m}分{s}秒" if h > 0 else (f"{m}分{s}秒" if m > 0 else f"{s}秒")
                logging.info(f"⏳ [體力退避狀態] collect_only 模式已執行 {int(elapsed // 60)} 分鐘。距離回到原掛機模式 [{self.machine.original_config['name']}] 還剩: {time_str}。")
                
            if elapsed >= retreat_seconds:
                logging.warning(f"🔄 [體力退避恢復] collect_only 模式已執行滿 {retreat_hours} 小時，自動恢復為原掛機模式 [{self.machine.original_config['name']}]！")
                self.machine.config = self.machine.original_config
                self.machine.original_config = None
                self.machine.stamina_retreat_start_time = None
                
                # 為了能從原模式的起點（大廳或尋路）開始，重設狀態為 UNKNOWN 進行重新定位
                self.machine.transition_to(self.machine.STATE_UNKNOWN)
                return

            # 檢查是否啟用【體力退避期間地下城冷卻結束自動復歸】
            auto_resume = self.machine.original_config.get("auto_resume_dungeon_on_cd", True)
            if auto_resume and not self.machine.need_diamond_collection:
                saved_cfg = self.machine.config
                self.machine.config = self.machine.original_config
                dungeon_ready = False
                try:
                    dungeon_ready = self.machine.has_available_dungeon()
                except Exception:
                    dungeon_ready = False
                finally:
                    self.machine.config = saved_cfg

                if dungeon_ready:
                    # 若又有體力領取任務，先領一次體力/麵包
                    if self.machine.enable_bread and self.machine.need_bread_collection:
                        logging.info("🍞 [冷卻結束復歸] 偵測到地下城冷卻結束，先執行體力領取...")
                    else:
                        logging.warning(f"🔄 [冷卻結束復歸] 偵測到地下城冷卻結束，暫時離開 collect_only 切回刷地下城！(退避總剩餘時間持續倒數中...)")
                        self.machine.config = self.machine.original_config
                        # 保持 self.machine.original_config 與 self.machine.stamina_retreat_start_time 不變
                        self.machine.transition_to(self.machine.STATE_UNKNOWN)
                        return

        # 1. 取得當前位置狀態
        is_town = False
        is_lobby = False
        
        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.8, quiet=True)
        pos_diamond, _ = self.matcher.match(screen_img, "diamond.png", threshold=0.8, quiet=True)
        if pos_door or pos_diamond:
            is_town = True
            
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.8, quiet=True)
        pos_bread_btn, _ = self.matcher.match(screen_img, "common/bread.png", threshold=0.8, quiet=True)
        if pos_goback or pos_bread_btn:
            is_lobby = True

        # 2. 領鑽石優先流程
        if self.machine.need_diamond_collection:
            if is_town:
                logging.info("💎 定時領取：在城鎮畫面，跳轉至 DIAMOND_COLLECTION。")
                self.machine.transition_to(self.machine.STATE_DIAMOND_COLLECTION)
                self.machine.handlers[self.machine.STATE_DIAMOND_COLLECTION].handle(screen_img, rect)
                return
            elif is_lobby:
                if pos_goback:
                    logging.info("💎 定時領取：在大廳畫面，點擊返回城鎮按鈕 [goback_town.png] 以便領取鑽石。")
                    self.mouse.click(rect["left"] + pos_goback[0], rect["top"] + pos_goback[1])
                    time.sleep(0.5)
                    return
            # 輔助：如果畫面上已經有鑽石圖標，直接跳轉
            if pos_diamond:
                self.machine.transition_to(self.machine.STATE_DIAMOND_COLLECTION)
                self.machine.handlers[self.machine.STATE_DIAMOND_COLLECTION].handle(screen_img, rect)
                return

        # 3. 領體力流程
        elif self.machine.enable_bread and self.machine.need_bread_collection:
            if is_lobby:
                logging.info("🍞 定時領取：在大廳畫面，跳轉至 BREAD_COLLECTION。")
                self.machine.transition_to(self.machine.STATE_BREAD_COLLECTION)
                self.machine.handlers[self.machine.STATE_BREAD_COLLECTION].handle(screen_img, rect)
                return
            elif is_town:
                if pos_door:
                    logging.info("🍞 定時領取：在城鎮畫面，點擊入口 [common/door.png] 進入大廳以領取體力。")
                    self.mouse.click(rect["left"] + pos_door[0], rect["top"] + pos_door[1])
                    time.sleep(0.5)
                    return
            # 輔助：如果畫面上已經有體力圖標，直接跳轉
            if pos_bread_btn:
                self.machine.transition_to(self.machine.STATE_BREAD_COLLECTION)
                self.machine.handlers[self.machine.STATE_BREAD_COLLECTION].handle(screen_img, rect)
                return

        # 4. 如果不需要任何領取，執行待機/返回邏輯
        now = time.time()
        last_log = getattr(self, "last_log_time", 0.0)
        
        # 動態決定 log 間隔：最長為 300 秒 (5分鐘)，若 CD 比 5 分鐘短則跟隨較短的 CD，以利測試
        from config import GLOBAL_SETTINGS
        default_diamond_cd = GLOBAL_SETTINGS.get("default_diamond_cd", 7200.0)
        diamond_cd = self.machine.config.get("diamond_cd", default_diamond_cd)
        default_bread_cd = 7200.0 if self.machine.config.get("type") == "collect_only" else GLOBAL_SETTINGS.get("default_bread_cd", 1800.0)
        bread_cd = self.machine.config.get("bread_cd", default_bread_cd)
        log_interval = min(300.0, diamond_cd, bread_cd)
        
        should_log = (now - last_log >= log_interval)
        if should_log:
            self.last_log_time = now
            
            # 計算剩餘秒數
            dia_rem = max(0.0, diamond_cd - (now - self.machine.last_diamond_collection_time))
            brd_rem = max(0.0, bread_cd - (now - self.machine.last_bread_collection_time))
            
            # 格式化輸出剩餘時間
            def format_time(seconds):
                if seconds <= 0:
                    return "即將執行"
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                if h > 0:
                    return f"{h}小時{m}分{s}秒"
                elif m > 0:
                    return f"{m}分{s}秒"
                else:
                    return f"{s}秒"
                    
            dia_str = format_time(dia_rem)
            brd_str = format_time(brd_rem) if self.machine.enable_bread else "已停用"
            
            logging.info(f"⌛ [定時領取狀態] 運作中。距離下一次領取 💎 鑽石還剩: {dia_str}，🍞 體力還剩: {brd_str}。")

        # 4.1 [心跳防斷線] 每 1 分鐘在城鎮畫面執行一次微幅水平拖曳，模擬活躍操作防止閒置斷線
        last_heartbeat = getattr(self, "last_heartbeat_time", 0.0)
        if last_heartbeat == 0.0:
            # 初始防護：啟動 15 秒後觸發第一次心跳，便於快速驗證
            self.last_heartbeat_time = now - 45.0
        elif now - last_heartbeat >= 60.0:
            self.last_heartbeat_time = now
            if is_town:
                logging.info("💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...")
                center_x = rect["left"] + int(rect["width"] * 0.5)
                center_y = rect["top"] + int(rect["height"] * 0.5)
                # 微幅向右拖曳 60 像素
                self.mouse.drag(center_x, center_y, center_x + 60, center_y, duration=0.5, inertia=False)
                time.sleep(0.8)
                # 微幅拖回原位
                self.mouse.drag(center_x + 60, center_y, center_x, center_y, duration=0.5, inertia=False)
                time.sleep(1.0)
                return

        if is_lobby:
            if pos_goback:
                logging.info("🧭 定時領取：目前在大廳且無領取任務，點擊 [goback_town.png] 返回城鎮...")
                self.mouse.click(rect["left"] + pos_goback[0], rect["top"] + pos_goback[1])
                time.sleep(1.0)
                return
        elif is_town:
            time.sleep(1.0)
            return
        else:
            if should_log:
                logging.warning("⚠️ 定時領取：未處於大廳或城鎮，嘗試原地等待重新偵測...")
            time.sleep(1.0)
            return
