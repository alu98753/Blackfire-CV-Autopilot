# 開發環境

開發環境包含純遊戲執行環境，另外加入測試、Node workflow 與 OpenCode reviewer 所需工具。若只想執行遊戲，請使用 `setup_runtime.md`。

開發與實機驗證前請先登入 Steam，不需要事先開啟遊戲。仍應使用一般視窗模式，按右上角最大化（不是 F11 全螢幕），解析度設定為 **1920×1080**。一般執行使用後台視窗操作，不會搶滑鼠；只有明確使用 `--foreground` 進行Demo時，才會切換到可見的前景實體滑鼠模式。

## Python 環境

Python 版本固定為 **3.11.2**。建立虛擬環境：

```powershell
& "C:\Path\To\Python311\python.exe" -m venv .venv
```

安裝遊戲執行依賴與測試工具：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
```

驗證：

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest --collect-only -q
```

## 遊戲邏輯測試

AI workflow 測試已使用 `pytest.mark.ai_workflow` 標記。一般遊戲邏輯驗證排除這些測試：

```powershell
chcp 65001
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -X utf8 -u -m pytest -m "not ai_workflow" -v
```

只跑 AI workflow 測試：

```powershell
.\.venv\Scripts\python.exe -X utf8 -u -m pytest -m ai_workflow -v
```

完整測試（包含 AI workflow）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -u -m pytest -v
```

## Node workflow 環境

Node.js/npm 只供 AI workflow 與 OpenCode 結構化 review 工具使用，不是遊戲 runtime 的必要依賴。安裝符合 `package.json` engines 的 Node.js 後，在專案根目錄執行：

```powershell
node --version
npm --version
npm ci
```

`npm ci` 依照 `package-lock.json` 建立 worktree 本地的 `node_modules`。不要以手動 `npm install` 取代它作為可重現的初始安裝流程。

## OpenCode CLI

OpenCode CLI 是另一個全域工具，不等同於專案的 `@opencode-ai/sdk`。依專案版本契約安裝並驗證：

```powershell
.\scripts\bootstrap_opencode.ps1
opencode --version
```

若只執行遊戲，不需要執行這個步驟。

## 依賴檔案責任

```text
requirements.txt        遊戲 runtime 直接依賴
requirements-test.txt   pytest 測試工具
requirements-lock.txt   目前開發環境的完整 pip 快照
package.json            Node workflow 直接依賴與 Node 版本契約
package-lock.json       Node 完整依賴樹與精確版本
```

目前的 `requirements-lock.txt` 是從包含 pytest 的開發環境產生，因此不應被當作純遊戲安裝清單。若日後需要完全重建兩種環境，應分別產生 runtime lock 與 development lock。
