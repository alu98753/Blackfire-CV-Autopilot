# 撠?蝬剝??那?瑕極?瑟???(Scripts & Diagnostics Index) ??儭?
## Task closeout

Normal cleanup uses the repository-owned wrapper:

```bat
cmd.exe /d /s /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\task_cleanup.ps1 -Task <task-id> < NUL"
```

Remote deletion is explicit only:

```bat
cmd.exe /d /s /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\task_cleanup.ps1 -Task <task-id> -DeleteRemoteBranch < NUL"
```

The wrapper resolves actual Git worktree topology, validates cleanliness and
ancestry, invokes the narrow `.venv` safety primitive, and performs normal
worktree/local-branch cleanup. It may be launched from any repository
worktree, but destructive Git commands run from validated canonical `main`.
It fails closed on dirty, detached, ambiguous, stale, partial, or unmerged
state and never uses force removal, prune, reset, clean, or pull.

`worktree_cleanup_safety.ps1` remains the low-level junction safety primitive;
do not duplicate its classification logic. Stale/partial failures use the
bounded recovery procedure in `branch_completion_workflow`.

?祉??(`scripts/`) ?葉?嗥????恍?敺?獢????*?蝬剛風?????芥漣璅皞CR 閮箸?瘜典????航??*??
---

## ?? 撌亙皜??揣撘?
| ?單?迂 | ?詨??瑁痊???| 撣貊???誘 |
| :--- | :--- | :--- |
| **[crop_tool.py](crop_tool.py)** | 閬死璅⊥鈭支?撘??芸極??(?芸??詨?銝衣??皞?1080p 璅⊥) | `.\.venv\Scripts\python scripts/crop_tool.py` |
| **[list_windows.py](list_windows.py)** | ??嗅?蝟餌絞??????閬???嗡誨蝣?(HWND, PID, 璅?) | `.\.venv\Scripts\python scripts/list_windows.py` |
| **[set_battle_settings.py](set_battle_settings.py)** | ?圈洛???閫??摮??航???撌亙 | `.\.venv\Scripts\python scripts/set_battle_settings.py --speed 5.0` |
| **[test_single_click.py](test_single_click.py)** | ?桐?璅⊥??瘥????唳芋?祇??蝡那?瑕極??| `.\.venv\Scripts\python scripts/test_single_click.py -t common/quit.png --click` |
| **[analyze_template_brightness.py](analyze_template_brightness.py)** | 璅⊥????啣漲鈭桀漲瘥? (Ratio) ?隡澆漲 (Confidence) ?? | `.\.venv\Scripts\python scripts/analyze_template_brightness.py` |
| **[calibrate_grid.py](calibrate_grid.py)** | ??撌脫遛 18 ?潭滯?箏?????蝬脫韏琿?敺株矽撌亙 | `.\.venv\Scripts\python scripts/calibrate_grid.py` |
| **[calibrate_bag_cleaning_grid.py](calibrate_bag_cleaning_grid.py)** | ??憭折??圾 (134x139.5) 鋆?蝬脫?券??⊥?撌亙 | `.\.venv\Scripts\python scripts/calibrate_bag_cleaning_grid.py` |
| **[diagnose_bulletin_board_ocr.py](diagnose_bulletin_board_ocr.py)** | ?貉??內??OCR ??????銝脫迤閬?閮箸 | `.\.venv\Scripts\python scripts/diagnose_bulletin_board_ocr.py` |
| **[diagnose_quest_ocr.py](diagnose_quest_ocr.py)** | ?貉?隞餃?璇?芣/撌脫鈭瘥???摮儘霅那??| `.\.venv\Scripts\python scripts/diagnose_quest_ocr.py` |
| **[diagnose_task_complete_ocr.py](diagnose_task_complete_ocr.py)** | 隞餃?摰??典?敶????????炎皜祈那??| `.\.venv\Scripts\python scripts/diagnose_task_complete_ocr.py` |
| **[diagnose_dpi_clicks.py](diagnose_dpi_clicks.py)** | 閬?蝮格??DPI 暺??榆瘛勗漲閮箸撌亙 | `.\.venv\Scripts\python scripts/diagnose_dpi_clicks.py` |

---

## ?? ???寥??漁摨西那?瑁牧??
?箔??脫迫??典??箏??臬?蝒?嚗?撘炊?寥??撌脰◤隤踵?????靘??霈??匱蝥???嚗?撅?`TemplateMatcher` ?抒蔭鈭?*?芷?漁摨行?靘?瞈曉**嚗?* **Confidence (?寥??訾撮摨?**嚗penCV ??`cv2.TM_CCOEFF_NORMED` ?寥?摨佗?0.0 ~ 1.0嚗?* **Ratio (撖西釭鈭桀漲瘥?)**嚗??撟喳?鈭桀漲 / 璅⊥撟喳?鈭桀漲`??  * `Ratio >= 0.8`嚗惇?潭迤撣貊??擃漁??嚗?撘??脰?暺???  * `Ratio < 0.8`嚗惇?潸◤暺?桃蔗隤踵????荔?蝔????瞈整?
