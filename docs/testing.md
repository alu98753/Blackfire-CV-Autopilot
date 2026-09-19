# 測試執行方式

專案測試目前仍以 `unittest.TestCase` 為主要測試實作，使用 pytest 作為測試收集與篩選入口。Python 執行環境固定為 Python 3.11.2；測試工具版本固定於 `requirements-test.txt`。

AI workflow、OpenCode、task orchestration 與 worktree 契約測試，會在測試模組中標記 `pytest.mark.ai_workflow`。遊戲邏輯測試維持現有路徑，不需要搬移測試檔案或重寫 import。

在 PowerShell 中執行遊戲邏輯測試：

```powershell
chcp 65001
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -X utf8 -u -m pytest -m "not ai_workflow" -v
```

執行全部測試（包含 AI workflow）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -u -m pytest -v
```

只執行 AI workflow 測試：

```powershell
.\.venv\Scripts\python.exe -X utf8 -u -m pytest -m ai_workflow -v
```

測試範圍驗證以 `--collect-only` 為低成本檢查：

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not ai_workflow" --collect-only -q
```

AI agent 平常只執行與變更直接相關的測試；完整測試由使用者明確要求後執行。
