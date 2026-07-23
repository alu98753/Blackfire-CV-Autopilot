import re

def parse_time_to_seconds(time_str: str) -> int | None:
    """
    將 OCR 識別出的時間字串 (如 "00:17:10", "01:30:44", "17:10", "0130:44", "1635" 或 "013044") 解析為總秒數。
    當冒號漏讀時，支援從右至左兩兩拆解 (秒、分、時)。
    """
    if not time_str:
        return None
    
    cleaned = re.sub(r"[^0-9:]", "", time_str)
    if not cleaned:
        return None
        
    parts = [p for p in cleaned.split(":") if p]
    
    # 展開零件中漏讀冒號的四位或六位純數字塊 (例如 "1635" -> "16", "35"; "0130" -> "01", "30")
    expanded_parts = []
    for p in parts:
        if len(p) == 4 and p.isdigit():
            expanded_parts.append(p[:2])
            expanded_parts.append(p[2:])
        elif len(p) == 6 and p.isdigit():
            expanded_parts.append(p[:2])
            expanded_parts.append(p[2:4])
            expanded_parts.append(p[4:])
        else:
            expanded_parts.append(p)
            
    parts = expanded_parts
    try:
        if len(parts) >= 3:  # 時:分:秒 (hh:mm:ss)
            h = int(parts[-3])
            m = int(parts[-2])
            s = int(parts[-1])
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:  # 分:秒 (mm:ss)
            m = int(parts[0])
            s = int(parts[1])
            return m * 60 + s
        elif len(parts) == 1 and parts[0]:  # 單純秒數
            return int(parts[0])
    except ValueError:
        pass
    return None

def format_seconds_to_readable(seconds: int) -> str:
    """
    將總秒數格式化為易讀字串，包含小時、分鐘與秒數。
    例如 5444 秒 ➔ "1 小時 30 分 44 秒"
    """
    if seconds is None or seconds < 0:
        return "0 秒"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    
    if h > 0:
        return f"{h} 小時 {m} 分 {s} 秒"
    elif m > 0:
        return f"{m} 分 {s} 秒"
    else:
        return f"{s} 秒"
