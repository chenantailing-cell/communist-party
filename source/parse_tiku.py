# -*- coding: utf-8 -*-
"""解析 D:\\6  题库\\题库\\题库.txt -> 题库-src.json

格式：
    单选题（共 388 道）
    001. 题干
         A. 选项
         B. 选项
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(r"D:\6  题库\题库\题库.txt")
OUT = Path(r"D:\6  题库\题库-src.json")

SEC_RE = re.compile(r"^(单选题|多选题|填空题|判断题)（共\s*(\d+)\s*道）")
ITEM_RE = re.compile(r"^(\d{3})\.\s*(.*)$")
OPT_RE = re.compile(r"^([A-H])[.、]\s*(.*)$")

TYPE_KEY = {"单选题": "single", "多选题": "multiple", "填空题": "blank", "判断题": "judge"}


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    cur_type = None
    cur = None
    out = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = SEC_RE.match(line.strip())
        if m:
            if cur:
                out.append(cur)  # 分节切换前先落盘本节最后一题
            cur_type = TYPE_KEY[m.group(1)]
            cur = None
            continue
        m = ITEM_RE.match(line.strip())
        if m and cur_type:
            if cur:
                out.append(cur)
            cur = {
                "type": cur_type,
                "no": int(m.group(1)),
                "stem": m.group(2).strip(),
                "options": [],
            }
            continue
        m = OPT_RE.match(line.strip())
        if m and cur is not None:
            cur["options"].append({"label": m.group(1), "text": m.group(2).strip()})
            continue
        if cur is not None:
            # 续行（题干或选项折行）
            if cur["options"]:
                cur["options"][-1]["text"] += " " + line.strip()
            else:
                cur["stem"] += " " + line.strip()
    if cur:
        out.append(cur)

    for i, q in enumerate(out, 1):
        q["id"] = "%s%03d" % ({"single": "s", "multiple": "m", "blank": "b", "judge": "j"}[q["type"]], q["no"])
        q["seq"] = i
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter
    c = Counter(q["type"] for q in out)
    print("total", len(out), dict(c))
    for t in ("blank", "judge", "multiple"):
        sample = [q for q in out if q["type"] == t][:2]
        for q in sample:
            print(t, q["no"], q["stem"][:60], "|opts:", [o["text"][:12] for o in q["options"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
