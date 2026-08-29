# Fail-Fast 與單一真理來源 (Single Source of Truth) 開發指南

## 1. 原則聲明

> **「單一真理來源與快速失敗：拒絕隱式硬編碼，改以資料驅動決策，並在配置缺失時立即顯式報錯。」**

在專案開發中，所有業務參數（如副本名稱、允許索引、範本清單、點擊門檻）必須統一維護於 `config.py`。狀態處理器 (Handlers) 與狀態機絕不自行內聯寫死，也不允許使用隱式默認 fallback。

---

## 2. 禁忌與反面模式 (Anti-Patterns)

❌ **嚴禁在程式碼中硬編碼 Fallback 陣列**：
```python
# 錯誤：隱式預設陣列，掩蓋配置缺失問題
dungeon_names = self.config.get("dungeon_names", ["黏糊糊的石窟", "幽影地穴", "森林迷宮", "神秘遺跡", "冰雪洞窟"])
allowed_indices = self.config.get("greedy_allowed_indices", [0, 1, 2, 3, 4])
```

❌ **嚴禁在 Handler 內部寫死模板檔名陣列**：
```python
# 錯誤：修改配置時此處無法同步，破壞單一真理來源
entry_templates = [
    "dungeons/Slime_entry.png",
    "dungeons/Ghost_entry.png",
    "dungeons/Forest_entry.png"
]
```

---

## 3. 標準正確實踐 (Best Practices)

✅ **由配置檔驅動，缺失時主動拋出 `ValueError` (Fail-Fast)**：
```python
dungeon_names = self.config.get("dungeon_names")
if dungeon_names is None:
    raise ValueError("配置錯誤：config 未設定 'dungeon_names'，請在 config.py 或啟動設定中指定地下城名稱清單。")

allowed_indices = self.config.get("greedy_allowed_indices")
if allowed_indices is None:
    raise ValueError("配置錯誤：config 未設定 'greedy_allowed_indices'，請在 config.py 或啟動設定中指定允許的地下城索引清單。")
```

---

## 4. 單元測試保護規範

* 當測試中需要實例化 `GameStateMachine` 並設置 `config` 時，必須傳入全量配置字典（如 `GAME_CONFIGS["dungeon"].copy()` 或 `GAME_CONFIGS["mix"].copy()`），禁止使用欠缺必要鍵值的裸字典 `{"type": "dungeon"}`。
* 防範測試環境與實際運行環境在配置驗證上的非對稱死角。
