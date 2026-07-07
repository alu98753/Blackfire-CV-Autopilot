with open("states/handlers/bag_cleaning.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Keep first 222 lines (index 0 to 221)
clean_lines = lines[:222]

# Append the closing statements
clean_lines.append("\n")
clean_lines.append("        logging.info(\"⌛ 背包清理流程中，正在等待背包相關畫面或按鈕載入...\")\n")
clean_lines.append("        time.sleep(0.05)\n")

with open("states/handlers/bag_cleaning.py", "w", encoding="utf-8") as f:
    f.writelines(clean_lines)

print("File truncated and fixed successfully!")
