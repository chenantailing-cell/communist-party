#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把新题与已入库套题做题干相似度匹配，输出"新题号 | 新答案 | 旧题号 | 旧答案 | 相似度"，用于复核。

用法：
    python match_known.py new.tsv            # 第一列题号、第三列题干（| 分隔）
    python match_known.py new.tsv --min 0.5
"""
import argparse
import difflib
import json
import os
import re
import sys


def norm(s):
    s = re.sub(r"[（(]\s*[）)]", "（）", s)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[，。；：、！？“”‘’\"'（）()]", "", s)
    return s


def load_known(root):
    out = []
    d = os.path.join(root, "data", "sets")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            data = json.load(f)
        for q in data.get("questions", []):
            out.append({
                "key": norm(q.get("stem", "")),
                "no": q.get("no"),
                "type": q.get("type"),
                "answer": q.get("answer", ""),
                "stem": q.get("stem", ""),
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tsv")
    ap.add_argument("--root", default=os.path.join(os.path.dirname(__file__), ".."))
    ap.add_argument("--min", type=float, default=0.55)
    a = ap.parse_args()

    known = load_known(os.path.abspath(a.root))
    print("已入库 %d 题" % len(known))
    rows = []
    with open(a.tsv, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            rows.append(parts)

    hits = miss = 0
    for p in rows:
        no, ans, stem = p[0], p[1] if len(p) > 1 else "", p[2]
        nk = norm(stem)
        best, score = None, 0.0
        for k in known:
            r = difflib.SequenceMatcher(None, nk, k["key"]).ratio()
            if r > score:
                best, score = k, r
        if best and score >= a.min:
            hits += 1
            flag = "✔同答案" if ans and ans.replace(" ", "") == str(best["answer"]).replace(" ", "") else "⚠答案不同"
            print("%-4s 新答案%-6s | 旧第%-4s %-6s | %.2f | %s | 旧题干: %s" % (
                no, ans or "-", best["no"], best["answer"], score, flag,
                best["stem"][:34]))
        else:
            miss += 1
            print("%-4s 新答案%-6s | 无匹配（最高 %.2f）" % (no, ans or "-", score))
    print("\n匹配到 %d 题，未匹配 %d 题" % (hits, miss))
    return 0


if __name__ == "__main__":
    sys.exit(main())
