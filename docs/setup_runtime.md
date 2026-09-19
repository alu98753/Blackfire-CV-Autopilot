# 純遊戲執行環境

這份文件只描述在新 Windows 電腦上啟動遊戲自動化程式所需的環境。不包含 pytest、Node.js、npm 或 OpenCode。

## 必要條件

- Windows
- Python **3.11.2**
- 本專案完整檔案
- 遊戲本體與必要的視窗設定
- Steam 帳號已登入（是否開啟遊戲不影響）
- 遊戲使用一般視窗模式，按右上角最大化；不是 F11 全螢幕模式
- 遊戲畫面解析度設定為 **1920×1080**

純遊戲執行不需要：

- Node.js 或 npm
- `package.json` 或 `package-lock.json`
- pytest
- OpenCode CLI
- AI workflow 依賴

## 建立環境

先確認 Python 版本：

```powershell
py -0p
```

必須找到 Python 3.11.2。若 Python Launcher 無法以版本號選取該 patch 版本，使用 `py -0p` 顯示的 Python 3.11.2 完整路徑建立虛擬環境：

```powershell
& "C:\Path\To\Python311\python.exe" -m venv .venv
```

確認虛擬環境版本：

```powershell
.\.venv\Scripts\python.exe --version
```

輸出必須是：

```text
Python 3.11.2
```

安裝遊戲執行依賴：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

檢查依賴是否有衝突：

```powershell
.\.venv\Scripts\python.exe -m pip check
```

## 啟動遊戲

執行專案根目錄的：

```powershell
.\run.bat
```

`run.bat` 會直接使用 `.venv\Scripts\python.exe`，不需要先啟用 virtualenv。

預設模式使用 Windows 後台視窗操作，不會搶走目前使用中的滑鼠控制。不要使用 `--foreground`，因為該模式是 Demo 使用，會進行實體滑鼠操作。

## 環境邊界

`requirements.txt` 是純遊戲執行的直接依賴清單。`requirements-test.txt`、`pytest.ini`、`package.json`、`package-lock.json` 與 OpenCode 啟動腳本屬於開發或 AI workflow 環境，不是啟動遊戲的必要條件。
