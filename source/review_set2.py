# -*- coding: utf-8 -*-
"""复核：把我的答案（截图1-答案.tsv）与转录员答案（截图1-合并.tsv）逐题比对，列出差异。"""
import io, re
from pathlib import Path

ROOT = Path(r"D:\6  题库")

def rows(p, cols, skip_first=True):
    out = []
    for i, line in enumerate(io.open(p, encoding="utf-8")):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.split("\t")] if "\t" in line else [x.strip() for x in line.split("|")]
        if len(parts) < len(cols):
            parts += [""] * (len(cols) - len(parts))
        d = dict(zip(cols, parts))
        if d.get(cols[0]) in ("题型", "批次") or d.get(cols[1]) == "题号":
            continue
        out.append(d)
    return out

mine = {}
for r in rows(ROOT / "截图1-答案.tsv", ["题型", "题号", "答案", "解析"]):
    mine[(r["题型"], int(re.sub(r"\D", "", r["题号"])))] = r["答案"]

theirs = {}
for r in rows(ROOT / "截图1-合并.tsv", ["题型", "题号", "题干", "选项", "答案", "备注", "批次"]):
    k = (r["题型"], int(re.sub(r"\D", "", r["题号"]) or 0))
    a = (r["答案"] or "").strip()
    if k not in theirs and a and a not in ("待定", "-"):
        theirs[k] = a
    elif k in theirs and len(a) > len(theirs[k]) and a not in ("待定", "-"):
        theirs[k] = a

def norm(a):
    a = a.replace("正确", "对").replace("错误", "错")
    ls = re.findall(r"[A-EＡ-Ｅ]", a)
    return "".join(sorted(set(ls))) if ls else a.strip()

diff = []
for k, my in sorted(mine.items(), key=lambda x: (x[0][0], x[0][1])):
    th = theirs.get(k)
    if th and norm(th) != norm(my):
        diff.append((k, th, my))

print("我答案题数=%d 有转录答案=%d 不一致=%d" % (len(mine), len(theirs), len(diff)))
for k, th, my in diff:
    print("%s %s | 转录: %s | 我的: %s" % (k[0], k[1], th, my))
