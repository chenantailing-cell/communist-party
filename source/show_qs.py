# -*- coding: utf-8 -*-
"""按段打印题目，便于逐题作答。用法: python show_qs.py 类型 起始序号 结束序号"""
import json
import sys
from pathlib import Path

qs = json.loads(Path(r"D:\6  题库\题库-src.json").read_text(encoding="utf-8"))
t = sys.argv[1]
lo = int(sys.argv[2])
hi = int(sys.argv[3])
for q in qs:
    if q["type"] == t and lo <= q["no"] <= hi:
        opts = " ".join("%s.%s" % (o["label"], o["text"]) for o in q["options"])
        print("%s|%s|%s" % (q["id"], q["stem"], opts))
