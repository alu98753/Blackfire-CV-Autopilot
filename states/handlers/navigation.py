import os
import time
import logging
from states.handlers.base import BaseStateHandler

class NavigationHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        尋路導航與自動領體力邏輯。
        """
        if rect is None:
            rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
            
        # 安全取得寬度與高度，相容實體執行與單體測試 mock 格式
        width = rect.get("width") or (rect.get("right", 0) - rect.get("left", 0)) or 1920
        height = rect.get("height") or (rect.get("bottom", 0) - rect.get("top", 0)) or 1080
        
        # 回寫至 rect 中，確保後續呼叫 rect["width"] 與 rect["height"] 不會報 KeyError
        rect["width"] = width
        rect["height"] = height

        # 優先判定：如果我們已經看到任何地下城探索或結束按鈕，說明點擊已經成功並進入內部，直接轉移狀態！
        if self.machine.config.get("type") == "dungeon":
            for check_btn in ["dungeons/dungeon_fight.png", "dungeons/dungeon_bless.png", "dungeons/Treasure.png", "dungeons/gungeon_godown.png"]:
                if os.path.exists(os.path.join("templates", check_btn)):
                    pos, conf = self.matcher.match(screen_img, check_btn, threshold=0.8)
                    if pos:
                        logging.info(f"🧭 尋路中偵測到地下城專屬按鈕 [{check_btn}] (信心度: {conf:.4f})，判定已進入地下城，轉移至 DUNGEON_EXPLORING。")
                        self.machine.transition_to(self.machine.STATE_DUNGEON_EXPLORING)
                        return

        # 0. 背包清理優先防護：如果需要整理背包，尋路只能引導我們退回大廳，不得前進
        if self.machine.need_bag_cleaning:
            # 1. 檢查是否已經離開關卡回到了大廳/城鎮 (看到了 common/door.png 或 goback_town.png)
            for town_btn in ["common/door.png", "goback_town.png"]:
                if os.path.exists(os.path.join("templates", town_btn)):
                    pos_t, conf_t = self.matcher.match(screen_img, town_btn, threshold=0.8)
                    if pos_t:
                        logging.info(f"🎒 尋路中：偵測到大廳/城鎮標誌 [{town_btn}] 且需要清理背包，切換至 BAG_CLEANING 狀態。")
                        self.machine.transition_to(self.machine.STATE_BAG_CLEANING)
                        return
            
            # 2. 如果還在大地圖或結算退出介面，只允許點擊回城/退出按鈕 (如 exit_battle.png 或 goback_town.png)
            for back_btn in ["exit_battle.png", "goback_town.png"]:
                if os.path.exists(os.path.join("templates", back_btn)):
                    pos_b, conf_b = self.matcher.match(screen_img, back_btn, threshold=0.8)
                    if pos_b:
                        logging.info(f"🎒 尋路中：需要清理背包，點擊回城按鈕 [{back_btn}] 退回城鎮。")
                        self.mouse.click(rect["left"] + pos_b[0], rect["top"] + pos_b[1])
                        time.sleep(0.1)
                        return
            
            # 其他情況原地等待回城
            logging.info("⌛ 尋路中：背包已滿，正在等待退出戰鬥或返回城鎮畫面...")
            return

        # A1. 如果需要領鑽石，執行領鑽石分支流程 (優先於領體力)
        if self.machine.need_diamond_collection:
            # 情況一：如果已經點過免費鑽石並確認了，我們尋找退出按鈕關閉彈窗
            if self.machine.diamond_collected_this_run:
                for quit_btn in ["common/quit.png"]:
                    if os.path.exists(os.path.join("templates", quit_btn)):
                        pos_quit, conf_quit = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                        if pos_quit:
                            logging.info(f"💎 領鑽石：偵測到退出按鈕 [{quit_btn}] ({conf_quit:.4f})，點擊關閉，領鑽石流程結束。")
                            self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                            self.machine.need_diamond_collection = False
                            self.machine.diamond_collected_this_run = False
                            self.machine.last_diamond_collection_time = time.time()
                            time.sleep(0.03)
                            return
            else:
                # 情況二：尚未領取或確認，進行領取步驟
                # 1. 彈窗內的確認按鈕 (獲得鑽石確認)
                pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    logging.info(f"💎 領鑽石：偵測到確認按鈕 [{conf_conf:.4f}]，點擊確認。")
                    self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
                    self.machine.diamond_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return
                
                pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
                if pos_ok:
                    logging.info(f"💎 領鑽石：偵測到 OK 按鈕 [{conf_ok:.4f}]，點擊 OK。")
                    self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
                    self.machine.diamond_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return

                # 檢查是否在領鑽石彈窗內 (尋找退出/關閉按鈕)
                in_diamond_window = False
                active_quit_btn = None
                quit_pos = None
                for quit_btn in ["common/quit.png"]:
                    if os.path.exists(os.path.join("templates", quit_btn)):
                        pos_quit, conf_quit = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                        if pos_quit:
                            # 有退出按鈕在畫面上，高機率已經在彈窗內
                            in_diamond_window = True
                            active_quit_btn = quit_btn
                            quit_pos = pos_quit
                            break

                if in_diamond_window:
                    # 2. 如果在彈窗內，只嘗試領取免費鑽石 (diamond_free.png)
                    # 使用較高閥值 (0.90) 以避免誤判到付費的 $4.99 按鈕
                    if os.path.exists(os.path.join("templates", "free.png")):
                        pos_free, conf_free = self.matcher.match(screen_img, "free.png", threshold=0.90)
                        if pos_free:
                            logging.info(f"💎 領鑽石：在視窗內偵測到免費鑽石按鈕 [{conf_free:.4f}]，點擊領取。")
                            self.mouse.click(rect["left"] + pos_free[0], rect["top"] + pos_free[1])
                            time.sleep(0.03)
                            return

                    # 3. 如果在彈窗內但沒有免費鑽石按鈕，說明鑽石正處於冷卻，點點退出按鈕關閉
                    logging.info(f"💎 領鑽石：鑽石視窗已開啟但無免費按鈕 (處於冷卻)，點擊退出按鈕 [{active_quit_btn}] 退出。")
                    self.mouse.click(rect["left"] + quit_pos[0], rect["top"] + quit_pos[1])
                    self.machine.need_diamond_collection = False
                    self.machine.diamond_collected_this_run = False
                    self.machine.last_diamond_collection_time = time.time()
                    time.sleep(0.08)
                    return

                # 4. 如果不在彈窗內，再嘗試點擊鑽石入口或返回城鎮
                # 3. 鑽石按鈕 (diamond.png)
                if os.path.exists(os.path.join("templates", "diamond.png")):
                    pos_dia, conf_dia = self.matcher.match(screen_img, "diamond.png", threshold=0.8)
                    if pos_dia:
                        logging.info(f"💎 領鑽石：在畫面偵測到鑽石按鈕 [{conf_dia:.4f}]，點擊打開領取畫面。")
                        self.mouse.click(rect["left"] + pos_dia[0], rect["top"] + pos_dia[1])
                        time.sleep(0.03)
                        return

                # 4. 返回城鎮按鈕 (goback_town.png)
                if os.path.exists(os.path.join("templates", "goback_town.png")):
                    pos_town, conf_town = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
                    if pos_town:
                        logging.info(f"💎 領鑽石：在畫面中偵測到返回城鎮按鈕 [{conf_town:.4f}]，點擊返回。")
                        self.mouse.click(rect["left"] + pos_town[0], rect["top"] + pos_town[1])
                        time.sleep(0.03)
                        return

            logging.info("⌛ 領鑽石流程中，正在等待鑽石畫面或按鈕載入...")
            time.sleep(0.01)
            return

        # A. 如果啟用且需要領體力，執行領體力分支流程
        if self.machine.enable_bread and self.machine.need_bread_collection:
            # 依優先級檢查領體力相關按鈕
            
            # 情況一：如果已經確認領過體力（或體力已滿確認了），我們只專心尋找退出按鈕，不要重複按領取或體力按鈕
            if self.machine.bread_collected_this_run:
                # 4. 關閉體力視窗按鈕 (quit bread)
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
                if pos_quit:
                    logging.info(f"🍞 領體力：偵測到退出體力按鈕 [{conf_quit:.4f}]，點擊關閉，領取體力流程結束。")
                    self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                    self.machine.need_bread_collection = False
                    self.machine.bread_collected_this_run = False  # 重設狀態
                    self.machine.last_bread_collection_time = time.time()
                    time.sleep(0.03)
                    return
            else:
                # 情況二：尚未領取或尚未點擊確認，正常進行領取步驟
                # 1. 彈窗內的確認按鈕 (獲得體力確認或體力已滿提示確認)
                pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    logging.info(f"🍞 領體力：偵測到體力確認按鈕 [{conf_conf:.4f}]，點擊確認。")
                    self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
                    self.machine.bread_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return

                # 2. 彈窗內的 OK 按鈕 (同樣代表確認)
                pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
                if pos_ok:
                    logging.info(f"🍞 領體力：偵測到體力 OK 按鈕 [{conf_ok:.4f}]，點擊 OK。")
                    self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
                    self.machine.bread_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return

                # 3. 領體力按鈕 (嘗試匹配通用 collect.png 或專屬 bread_collection.png，使用 0.70 的容錯閥值)
                pos_coll = None
                conf_coll = 0.0
                matched_template = None
                
                for template_name in ["common/collect.png", "common/bread_collection.png"]:
                    if os.path.exists(os.path.join("templates", template_name)):
                        pos, conf = self.matcher.match(screen_img, template_name, threshold=0.70)
                        if pos:
                            pos_coll = pos
                            conf_coll = conf
                            matched_template = template_name
                            break
                            
                if pos_coll:
                    logging.info(f"🍞 領體力：偵測到領體力按鈕 [{matched_template}] (信心度: {conf_coll:.4f})，進行點擊領取。")
                    self.mouse.click(rect["left"] + pos_coll[0], rect["top"] + pos_coll[1])
                    self.machine.bread_click_attempted = True
                    time.sleep(0.03)
                    return

                # 新增防禦性相對座標點擊：
                # 如果體力視窗已開啟 (看到 quit.png)，但沒偵測到「收集」按鈕，
                # 且我們在本次流程中「尚未點擊過領取」，則使用相對 quit.png 的座標執行一次點擊 (收集食物)。
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
                if pos_quit:
                    if not getattr(self.machine, "bread_click_attempted", False):
                        # 關閉按鈕匹配中心為 (X, Y)，「收集食物」按鈕相對於 X 的偏移為 dx=-208, dy=612
                        click_x = rect["left"] + pos_quit[0] - 208
                        click_y = rect["top"] + pos_quit[1] + 612
                        logging.warning(f"⚠️ 領體力：未匹配到領體力按鈕，執行相對座標防禦性點擊 (收集食物): ({click_x}, {click_y})")
                        self.mouse.click(click_x, click_y)
                        self.machine.bread_click_attempted = True
                        time.sleep(0.1)
                        return
                    else:
                        # 如果已經嘗試點擊過領取 (不論是匹配還是相對點擊)，但畫面上依然沒有確認彈窗，說明確實處於冷卻或已領完，此時點點退出關閉視窗
                        logging.info(f"🍞 領體力：已嘗試過點擊領取但無效，判定為冷卻或已領完，點擊退出體力按鈕 [{conf_quit:.4f}] 退出。")
                        self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                        self.machine.need_bread_collection = False
                        self.machine.bread_collected_this_run = False
                        self.machine.bread_click_attempted = False  # 重置標記
                        self.machine.last_bread_collection_time = time.time()
                        time.sleep(0.03)
                        return

                # 5. 打開體力視窗按鈕 (bread)
                pos_bread, conf_bread = self.matcher.match(screen_img, "common/bread.png", threshold=0.8)
                if pos_bread:
                    logging.info(f"🍞 領體力：在大廳偵測到體力按鈕 [{conf_bread:.4f}]，點擊打開體力視窗。")
                    self.mouse.click(rect["left"] + pos_bread[0], rect["top"] + pos_bread[1])
                    time.sleep(0.03)
                    return

                # 6. 入口按鈕 (door)
                pos_door, conf_door = self.matcher.match(screen_img, "common/door.png", threshold=0.8)
                if pos_door:
                    logging.info(f"🍞 領體力：在主畫面偵測到入口按鈕 [{conf_door:.4f}]，點擊進入大廳。")
                    self.mouse.click(rect["left"] + pos_door[0], rect["top"] + pos_door[1])
                    time.sleep(0.03)
                    return

                # 7. 返回城鎮按鈕 (goback_town.png)
                if os.path.exists(os.path.join("templates", "goback_town.png")):
                    pos_town, conf_town = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
                    if pos_town:
                        logging.info(f"🍞 領體力：在畫面中偵測到返回城鎮按鈕 [{conf_town:.4f}]，點擊返回。")
                        self.mouse.click(rect["left"] + pos_town[0], rect["top"] + pos_town[1])
                        time.sleep(0.03)
                        return

            logging.info("⌛ 領體力流程中，正在等待體力畫面或按鈕載入...")
            time.sleep(0.01)
            return

        # B. 原本的尋路導航邏輯
        # 如果是自動貪婪地下城模式，且畫面上看見第一個地下城入口，執行貪婪選關邏輯
        # B. 原本的尋路導航邏輯
        # 如果是自動貪婪地下城模式，且畫面上看見任何一個地下城入口，執行貪婪選關邏輯
        if self.machine.config.get("greedy_dungeon", False):
            import cv2
            
            # 使用擷取的影像寬度計算縮放比例，並對齊至標準遊戲解析度寬度以消除視窗邊框干擾
            h_img, w_img = screen_img.shape[:2]
            standard_widths = [1280, 1366, 1600, 1920, 2560, 3840]
            matched_width = w_img
            for sw in standard_widths:
                if abs(w_img - sw) <= 30:
                    matched_width = sw
                    break
            scale = matched_width / 1920.0
            
            dungeon_names = ["黏糊糊的石窟", "幽影地穴", "森林迷宮", "神秘遺跡"]
            entry_templates = [
                "dungeons/Slime_entry.png",
                "dungeons/Ghost_entry.png",
                "dungeons/Forest_entry.png",
                "dungeons/Ruins_entry.png"
            ]
            
            # 檢查目前是否確實在地下城選關介面 (至少要能識別到一個入口)
            any_entry_found = False
            for temp_name in entry_templates:
                if os.path.exists(os.path.join("templates", temp_name)):
                    t_img = cv2.imread(os.path.join("templates", temp_name))
                    if t_img is not None:
                        t_w = int(346.0 * scale)
                        t_h = int(341.0 * scale)
                        resized_t = cv2.resize(t_img, (t_w, t_h))
                        res = cv2.matchTemplate(screen_img, resized_t, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(res)
                        if max_val >= 0.75:
                            any_entry_found = True
                            break
                            
            if any_entry_found:
                logging.info("🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊選關。")
                selected_index = None
                click_target = None
                
                # 從 4 到 1 逆序遍歷
                for i in range(3, -1, -1):
                    cooldown_until = self.machine.dungeon_cooldowns.get(i, 0.0)
                    if time.time() < cooldown_until:
                        if cooldown_until == float('inf'):
                            logging.info(f"⏳ 貪婪地下城：[{dungeon_names[i]}] 處於永久不可打狀態，跳過。")
                        else:
                            logging.info(f"⏳ 貪婪地下城：[{dungeon_names[i]}] 處於冷卻中，剩餘 {int(cooldown_until - time.time())} 秒，跳過。")
                        continue
                        
                    temp_name = entry_templates[i]
                    if not os.path.exists(os.path.join("templates", temp_name)):
                        continue
                        
                    t_img = cv2.imread(os.path.join("templates", temp_name))
                    if t_img is None:
                        continue
                        
                    t_w = int(346.0 * scale)
                    t_h = int(341.0 * scale)
                    resized_t = cv2.resize(t_img, (t_w, t_h))
                    
                    # 匹配入口中心
                    res = cv2.matchTemplate(screen_img, resized_t, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    
                    if max_val < 0.75:
                        # 該地下城不在當前畫面中 (滾動到其他地方)
                        continue
                        
                    # === 檢測該地下城是否在冷卻中 (畫面木牌比對) ===
                    in_cooldown = False
                    h_limit, w_limit = screen_img.shape[:2]
                    crop_y1 = max_loc[1]
                    crop_y2 = min(h_limit, max_loc[1] + t_h)
                    crop_x1 = max_loc[0]
                    crop_x2 = min(w_limit, max_loc[0] + t_w)
                    dungeon_crop = screen_img[crop_y1:crop_y2, crop_x1:crop_x2]
                    
                    for cd_temp in ["dungeons/cooldown_left.png", "dungeons/cooldown_right.png"]:
                        if os.path.exists(os.path.join("templates", cd_temp)):
                            cd_img = cv2.imread(os.path.join("templates", cd_temp))
                            if cd_img is not None:
                                cd_w = int(cd_img.shape[1] * scale)
                                cd_h = int(cd_img.shape[0] * scale)
                                cd_w = max(5, cd_w)
                                cd_h = max(5, cd_h)
                                resized_cd = cv2.resize(cd_img, (cd_w, cd_h))
                                
                                res_cd = cv2.matchTemplate(dungeon_crop, resized_cd, cv2.TM_CCOEFF_NORMED)
                                _, max_val_cd, _, _ = cv2.minMaxLoc(res_cd)
                                if max_val_cd >= 0.75:
                                    logging.info(f"⏳ 貪婪地下城：[{dungeon_names[i]}] 偵測到畫面中存在冷卻木牌 [{cd_temp}] (相似度: {max_val_cd:.4f})，判定為冷卻中。")
                                    in_cooldown = True
                                    break
                                    
                    if in_cooldown:
                        # 設為 30 秒冷卻，避免每一影格重複進行模板匹配運算
                        self.machine.dungeon_cooldowns[i] = time.time() + 30.0
                        continue
                        
                    cx = max_loc[0] + t_w // 2
                    cy = max_loc[1] + t_h // 2
                    
                    # 使用寬度 200 像素的容錯區間裁切並匹配亮骨頭
                    x1 = cx - int(90.0 * scale)
                    y1 = cy + int(240.0 * scale)
                    w_skull = int(200.0 * scale)
                    h_skull = int(60.0 * scale)
                    x2 = x1 + w_skull
                    y2 = y1 + h_skull
                    
                    h_limit, w_limit = screen_img.shape[:2]
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
                                
                                # 執行匹配
                                res_s = cv2.matchTemplate(skull_crop, resized_light_t, cv2.TM_CCOEFF_NORMED)
                                _, max_val_skull, _, _ = cv2.minMaxLoc(res_s)
                                
                                logging.info(f"🧭 貪婪地下城：[{dungeon_names[i]}] 亮骨頭匹配相似度: {max_val_skull:.4f} (閾值: 0.75)")
                                
                                if max_val_skull < 0.75:
                                    logging.warning(f"🔒 貪婪地下城：[{dungeon_names[i]}] 亮骨頭相似度過低 ({max_val_skull:.4f})，判定為未解鎖或無法自動刷，設為無限冷卻。")
                                    self.machine.dungeon_cooldowns[i] = float('inf')
                                    continue
                            else:
                                logging.warning(f"⚠️ 找不到亮骨頭模板圖片 {light_t_name}，跳過解鎖判定。")
                        else:
                            logging.warning(f"⚠️ 模板檔案不存在 {light_t_name}，跳過解鎖判定。")
                    else:
                        logging.warning(f"🧭 貪婪地下城：[{dungeon_names[i]}] 骨頭裁切座標超出畫面，無法檢測，跳過。")
                        continue
                        
                    # 成功找到可點擊的最高等地下城
                    selected_index = i
                    click_target = (cx, cy)
                    break
                    
                if selected_index is not None:
                    # 點擊該卡片門扉中心進入
                    click_x = rect["left"] + click_target[0]
                    click_y = rect["top"] + click_target[1]
                    logging.info(f"👉 貪婪地下城：選擇進入第 {selected_index+1} 個地下城 [{dungeon_names[selected_index]}]，點擊座標 ({click_x}, {click_y})。")
                    self.mouse.click(click_x, click_y)
                    
                    self.machine.current_dungeon_index = selected_index
                    time.sleep(0.2)
                    return
                else:
                    logging.warning("⚠️ 貪婪地下城：所有地下城均處於冷卻或不可打狀態，原地等待中...")
                    time.sleep(1.0)
                    return

        nav_path = self.machine.config.get("navigation_path", [])
        if not nav_path:
            # 如果沒有設定尋路路徑 (例如普通關卡)，直接進入大廳狀態
            self.machine.transition_to(self.machine.STATE_LOBBY)
            return

        # 0. 優先判定：如果已經可以直接匹配到大廳開始按鈕，說明已經成功抵達準備大廳，直接移轉狀態！
        lobby_btn = self.machine.config.get("lobby_start_btn")
        if lobby_btn and os.path.exists(os.path.join("templates", lobby_btn)):
            pos_start, conf_start = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
            if pos_start:
                logging.info(f"🧭 尋路成功！偵測到準備大廳開始按鈕 [{lobby_btn}] (信心度: {conf_start:.4f})，已抵達準備大廳，狀態轉移至 LOBBY。")
                self.machine.transition_to(self.machine.STATE_LOBBY)
                return

        # （已將地下城專屬按鈕的主動判定移至 handle 方法最前頭，作為最高優先權判定）

        # 判斷是否處於關卡選擇介面 (看見任何一個關卡入口小島)
        stage_select_open = False
        for lvl in ["stages/level1_sky_plains.png", "stages/level2_barren_rocks.png", "stages/level3_ancient_forest.png", "stages/level4_desert_ruins.png"]:
            if os.path.exists(os.path.join("templates", lvl)):
                # 調降閾值至 0.70，容忍小島按鈕的縮放與抖動，確保精準識別關卡選擇清單開啟
                pos_lvl, _ = self.matcher.match(screen_img, lvl, threshold=0.70)
                if pos_lvl:
                    stage_select_open = True
                    break

        # 如果處於關卡選擇介面，且目標關卡入口小島尚未出現在畫面上，執行向左滑動清單
        if self.machine.config.get("type") == "stage" and stage_select_open:
            if len(nav_path) > 3:
                target_level_btn = nav_path[3]
                if os.path.exists(os.path.join("templates", target_level_btn)):
                    lvl_thresh = 0.70 if "level" in target_level_btn else 0.80
                    pos_target, _ = self.matcher.match(screen_img, target_level_btn, threshold=lvl_thresh)
                    if pos_target:
                        # 成功找到目標小島，重置缺失計時器與水平滾動計數
                        self.machine.__setattr__(f"missing_time_{target_level_btn}", 0.0)
                        self.machine.horizontal_scroll_count = 0
                    else:
                        # 目標關卡尚未在畫面上看見，先等待 1.5 秒讓動畫加載穩定後再滑動
                        missing_time = getattr(self.machine, f"missing_time_{target_level_btn}", 0.0)
                        if missing_time == 0.0:
                            self.machine.__setattr__(f"missing_time_{target_level_btn}", time.time())
                            logging.info(f"⌛ 尋路中：目標關卡 [{target_level_btn}] 暫時未出現在畫面上，等待載入與穩定中...")
                            return
                        elif time.time() - missing_time < 1.5:
                            # 仍處於 1.5 秒等待緩衝期內，暫不執行滑動
                            return

                        last_scroll = getattr(self.machine, "last_stage_scroll_time", 0.0)
                        if time.time() - last_scroll > 1.2:
                            scroll_count = getattr(self.machine, "horizontal_scroll_count", 0)
                            if scroll_count == 0:
                                logging.info(f"🧭 尋路中：已在關卡選擇介面，但未見目標關卡 [{target_level_btn}]，執行微小緩慢向左滑動清單 (地圖向右移)...")
                                start_x = rect["left"] + int(rect["width"] * 0.58)
                                end_x = rect["left"] + int(rect["width"] * 0.42)
                                self.machine.horizontal_scroll_count = 1
                            else:
                                logging.info(f"🧭 尋路中：已在關卡選擇介面，但仍未見目標關卡 [{target_level_btn}]，改為向右滑動清單返回主區 (地圖向左移)...")
                                start_x = rect["left"] + int(rect["width"] * 0.42)
                                end_x = rect["left"] + int(rect["width"] * 0.58)
                                self.machine.horizontal_scroll_count = scroll_count + 1

                            y_pos = rect["top"] + int(rect["height"] * 0.5)
                            self.mouse.drag(start_x, y_pos, end_x, y_pos, duration=0.8)
                            self.machine.last_stage_scroll_time = time.time()
                            # 增加靜止等待時間，確保清單滑動動畫完全停止後再進行下一幀偵測與點擊
                            time.sleep(1.2)
                        else:
                            logging.info("⌛ 剛執行過水平滑動，等待關卡清單載入或定位中...")
                        return

        # 判斷是否已經在關卡內部細節畫面
        in_detail_screen = False
        pos_label = None
        if os.path.exists(os.path.join("templates", "stages/stage_label.png")):
            pos_label, _ = self.matcher.match(screen_img, "stages/stage_label.png", threshold=0.70)
        
        # 尋找路徑中是否有魔王關 (包含 final) 出現在畫面上
        pos_final = None
        target_final_btn = None
        for btn in nav_path:
            if "final" in btn:
                target_final_btn = btn
                if os.path.exists(os.path.join("templates", btn)):
                    pos_f, _ = self.matcher.match(screen_img, btn, threshold=0.75)
                    if pos_f:
                        pos_final = pos_f
                        # 成功找到魔王關，重置其缺失計時器
                        self.machine.__setattr__(f"missing_time_{btn}", 0.0)
                        break

        if pos_label or pos_final:
            in_detail_screen = True

        # 逆序掃描導航路徑中可見的按鈕，點擊最深層的那個
        clicked_any = False
        for btn in reversed(nav_path):
            # 防重入：如果在關卡選擇介面，跳過 common/select_stage.png 避免重複開啟或誤點
            if btn == "common/select_stage.png" and stage_select_open:
                continue

            # 如果已經進入了關卡內部細節畫面，跳過小島選擇入口按鈕以免誤點 (小島名稱包含 level 且不含 final 或 entry)
            if in_detail_screen and "level" in btn and "final" not in btn and "entry" not in btn:
                continue

            # 針對 level/entry/stage_label 類背景特徵圖，調降閾值至 0.70，容忍縮放與像素抖動
            thresh = 0.70 if ("entry" in btn or "stage_label" in btn or "level" in btn) else 0.80
            pos, conf = self.matcher.match(screen_img, btn, threshold=thresh)
            if pos:
                if btn == "stages/stage_label.png":
                    # 特別處置：如果是分關入口背景，代表需要向下滾動尋找魔王關
                    # 為了讓魔王關卡載入與 scan 完全，引入 1.5 秒的缺失計時器
                    if target_final_btn:
                        missing_time = getattr(self.machine, f"missing_time_{target_final_btn}", 0.0)
                        if missing_time == 0.0:
                            self.machine.__setattr__(f"missing_time_{target_final_btn}", time.time())
                            logging.info(f"⌛ 尋路中：偵測到關卡背景，但魔王關 [{target_final_btn}] 尚未出現，等待載入與穩定中...")
                            return
                        elif time.time() - missing_time < 1.5:
                            # 仍處於 1.5 秒等待緩衝期內，暫不執行滾動
                            return

                    # 為了防範快速連續滾動，限制滾動 CD 為 1.5 秒
                    last_scroll = getattr(self.machine, "last_stage_scroll_time", 0.0)
                    if time.time() - last_scroll > 1.5:
                        logging.info("🧭 尋路中：偵測到第二關畫面 [stages/stage_label.png] 但未見魔王關，執行溫和滑動向下滾動...")
                        center_x = rect["left"] + rect["width"] // 2
                        center_y = rect["top"] + rect["height"] // 2
                        self.mouse.scroll(-400, center_x, center_y)
                        self.machine.last_stage_scroll_time = time.time()
                        clicked_any = True
                        time.sleep(0.3)
                        break
                else:
                    click_x = rect["left"] + pos[0]
                    click_y = rect["top"] + pos[1]
                    if "level" in btn and "final" not in btn and "entry" not in btn:
                        click_y -= 160
                        logging.info(f"🧭 尋路中：在畫面中找到關卡小島按鈕 [{btn}] (信心度: {conf:.4f})，套用向上偏移 160 像素點擊島嶼本體。")
                    else:
                        logging.info(f"🧭 尋路中：在畫面中找到 [{btn}] (信心度: {conf:.4f})，點擊跳轉。")
                    self.mouse.click(click_x, click_y)
                    clicked_any = True
                    time.sleep(0.03) # 等待跳轉動畫
                    break

        if not clicked_any:
            # 如果能直接匹配到大廳開始按鈕，說明已經成功抵達準備大廳
            lobby_btn = self.machine.config.get("lobby_start_btn")
            if lobby_btn and os.path.exists(os.path.join("templates", lobby_btn)):
                pos_start, conf_start = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
                if pos_start:
                    logging.info(f"🧭 尋路完成：偵測到準備大廳開始按鈕 [{lobby_btn}] (信心度: {conf_start:.4f})，已抵達大廳。")
                    self.machine.transition_to(self.machine.STATE_LOBBY)
                    return

            # 備用邏輯：若在普通關卡模式下，已進入關卡細節畫面但未看見魔王關 (final.png)，則向下滾動尋找魔王關
            if self.machine.config.get("type") == "stage":
                if pos_label and not pos_final:
                    if target_final_btn:
                        missing_time = getattr(self.machine, f"missing_time_{target_final_btn}", 0.0)
                        if missing_time == 0.0:
                            self.machine.__setattr__(f"missing_time_{target_final_btn}", time.time())
                            logging.info(f"⌛ 尋路中：判定已在細節畫面但未見魔王關 [{target_final_btn}]，等待載入與穩定中...")
                            return
                        elif time.time() - missing_time < 1.5:
                            # 仍處於 1.5 秒等待緩衝期內，暫不執行滾動
                            return

                    last_scroll = getattr(self.machine, "last_stage_scroll_time", 0.0)
                    if time.time() - last_scroll > 1.5:
                        logging.info("🧭 尋路中：判定已在關卡細節畫面但未見魔王關，執行溫和向下滑動滾動尋找魔王...")
                        center_x = rect["left"] + rect["width"] // 2
                        center_y = rect["top"] + rect["height"] // 2
                        self.mouse.scroll(-400, center_x, center_y)
                        self.machine.last_stage_scroll_time = time.time()
                        clicked_any = True
                        time.sleep(0.3)
                        return

            # 其他情況 (例如動畫播放、切換關卡加載黑屏)，原地等待畫面載入
            logging.info("⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...")
