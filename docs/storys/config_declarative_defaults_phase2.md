# Config Declarative Defaults Phase 2

## Purpose

移除主設定分散於 Python 常數與巢狀字典的維護負擔，讓使用者能在不閱讀程式邏輯的情況下檢視與調整預設值。

## Action

將全域冷卻、任務限制、OCR 裁切、地下城與關卡清單、所有主模式與城鎮子流程、裝備與活動預設值搬到 `config/defaults.toml`。`config.py` 改為相容載入層，持續提供既有的公開設定名稱與 `normalize_config`。

## Result

既有 `from config import GAME_CONFIGS` 呼叫不需改動；Python 僅保留載入、型別相容轉換、設定正規化與動態設定 API。TOML 讀取同樣由 transactional config manager 保護。

## So What

日常可調資料已不再與遊戲操作邏輯混在同一支 Python 檔案，之後可安全建立 `local.toml` 覆寫與執行期套用機制。

## Influence

第三階段會合併 `defaults.toml` 與未追蹤的 `local.toml`，並在狀態機安全轉移點更新正在執行腳本的模式快照。
