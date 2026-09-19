# 開發環境

開發環境以純遊戲執行環境為基底，額外加入測試套件（pytest）、Node workflow 與 OpenCode 結構化審查工具。

## 前置條件：先完成 Runtime 環境建置

**在開始設定開發環境前，請務必先完成 [setup_runtime.md](./setup_runtime.md) 的步驟。**因為 `setup_runtime.md` 環境是遊戲自動化腳本運作的必要項目。開發環境是在這個已經具備遊戲控制與視窗邏輯的基底上，進一步疊加測試與輔助工具。

---

## 1. 測試依賴與驗證

請確保已依 `setup_runtime.md` 建立好專案根目錄的 `.venv` Junction。接著在專案根目錄安裝測試工具：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
```

驗證依賴與測試搜集：

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest --collect-only -q
```

---

## 2. 遊戲邏輯測試

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

---

## 3. Node workflow 環境

Node.js/npm 只供 AI workflow 與 OpenCode 結構化 review 工具使用，不是遊戲 runtime 的必要依賴。

### 安裝 Node.js
依 `package.json` 規範，Node.js 版本需為 **`>=18.17`**（建議安裝 LTS 版本）：

```powershell
winget install OpenJS.NodeJS.LTS
```

> **注意**：
> 1. 安裝完成後請**重新開啟 PowerShell** 讓環境變數生效。
> 2. 若在 PowerShell 執行 npm 時出現「因為這個系統上已停用指令碼執行，所以無法載入...」的安全性原則錯誤，請先執行以下指令放寬目前使用者權限：
>    ```powershell
>    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
>    ```

### 安裝專案 Node 依賴
建議直接執行專案提供的安裝腳本（此腳本會自動檢查 Node 版本並透過 `npm ci` 依 `package-lock.json` 建立 `node_modules`）：

```powershell
.\scripts\bootstrap_node_workflow_deps.ps1
```

---

## 4. OpenCode CLI (選用)

OpenCode CLI 是全域工具，不等同於專案的 `@opencode-ai/sdk`。依專案版本契約安裝並驗證：

```powershell
.\scripts\bootstrap_opencode.ps1
opencode --version
```

若不需要使用 OpenCode 來進行LLM協作開發，可跳過此步驟。

---

## 5. 依賴檔案責任

```text
requirements.txt        遊戲 runtime 直接依賴
requirements-test.txt   pytest 測試工具
requirements-lock.txt   目前開發環境的完整 pip 快照
package.json            Node workflow 直接依賴與 Node 版本契約
package-lock.json       Node 完整依賴樹與精確版本
```

目前的 `requirements-lock.txt` 是從包含 pytest 的開發環境產生，因此不應被當作純遊戲安裝清單。若日後需要完全重建兩種環境，應分別產生 runtime lock 與 development lock。
