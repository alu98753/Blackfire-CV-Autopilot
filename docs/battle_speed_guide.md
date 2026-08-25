# 遊戲戰鬥倍速破解與切換指南 (Battle Speed Guide) ⚡

本文件詳細記錄如何透過修改本地 Godot 存檔 `battle_settings.save` 達成 10x ~ 50x 原生超光速戰鬥，以及如何一鍵恢復為原廠預設倍速（2.0x / 1.45）。

---

## 🚀 一、極速戰鬥原理解析

在遊戲本體架構中，戰鬥動畫與結算時鐘由 `time_scale` 變數控制：
- **原廠預設最大值**：UI 介面上的 2.0x 倍速對應儲存數值為 **`1.45`**。
- **破解機制**：
  - 存檔路徑：`%APPDATA%\Godot\app_userdata\Blackfire Crusade\battle_settings.save`
  - 格式為純文字 JSON：`{"time_scale": 50.0}`
  - 為防止遊戲在啟動或退出時將數值覆蓋回原廠設定，修改後必須為該檔案加上 Windows 系統級 **唯讀屬性鎖 (`attrib +r`)**。

---

## 🛠️ 二、一鍵切換與恢復工具 ([set_battle_speed.py](../tools/set_battle_speed.py))

專案已內建全自動設定腳本，自動處理解除唯讀 ➔ 寫入數值 ➔ 加上唯讀鎖：

### 1. 切換為 50 倍速 (極速刷圖模式，戰鬥 1~2 秒結束)
```powershell
.\.venv\Scripts\python tools/set_battle_speed.py --speed 50.0
```

### 2. 切換為 10 倍速 (平穩高速模式)
```powershell
.\.venv\Scripts\python tools/set_battle_speed.py --speed 10.0
```

### 3. 恢復為原廠預設倍速 (2.0x 倍速 / 1.45) 🔄
```powershell
.\.venv\Scripts\python tools/set_battle_speed.py --reset
```

---

## ✋ 三、手動修改教學 (Manual Adjustment)

如果您希望手動修改或確認檔案：

1. **解除唯讀保護**：
   ```powershell
   attrib -r "$env:APPDATA\Godot\app_userdata\Blackfire Crusade\battle_settings.save"
   ```
2. **開啟並編輯檔案**：
   使用記事本開啟 `battle_settings.save`，修改為您要的倍數：
   - 恢復原廠 2.0x：`{ "time_scale": 1.45 }`
   - 50 倍速：`{ "time_scale": 50.0 }`
3. **重新鎖定唯讀**：
   ```powershell
   attrib +r "$env:APPDATA\Godot\app_userdata\Blackfire Crusade\battle_settings.save"
   ```
