# -*- coding: utf-8 -*-
"""文件内近重复检测 + 与站点已有题库比对。"""
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

SRC = Path(r"D:\6  题库\题库-src.json")
SITE = Path(r"D:\6  题库\site\data\sets")


def norm(s: str) -> str:
    s = re.sub(r"[（(]\s*[）)]", "", s)
    s = re.sub(r"[\s，。、；：？！“”‘’（）()《》〈〉·,.;:?!\"'\-—…]+", "", s)
    return s


def main() -> None:
    qs = json.loads(SRC.read_text(encoding="utf-8"))
    for q in qs:
        q["n"] = norm(q["stem"])

    # 1) 文件内近重复（同题型内）
    print("== 文件内近重复 ==")
    dup = 0
    for i in range(len(qs)):
        for j in range(i + 1, len(qs)):
            a, b = qs[i], qs[j]
            if a["type"] != b["type"]:
                continue
            if abs(len(a["n"]) - len(b["n"])) > 12:
                continue
            r = SequenceMatcher(None, a["n"], b["n"]).ratio()
            if r >= 0.93:
                dup += 1
                print("  %s/%s %.2f" % (a["id"], b["id"], r))
                print("    A:", a["stem"][:60])
                print("    B:", b["stem"][:60])
    print("  候选对数:", dup)

    # 2) 与站点已有题比对
    old = []
    for p in sorted(SITE.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        for q in data.get("questions", []):
            old.append((p.stem, q.get("no"), q.get("type"), q.get("stem", ""), norm(q.get("stem", ""))))
    print("\n== 与站点已有 %d 题比对 ==" % len(old))
    hits = 0
    for q in qs:
        best = (0.0, None)
        for s in old:
            if abs(len(q["n"]) - len(s[4])) > 15:
                continue
            r = SequenceMatcher(None, q["n"], s[4]).ratio()
            if r > best[0]:
                best = (r, s)
        if best[0] >= 0.88:
            hits += 1
            s = best[1]
            print("  %s(type=%s) ~ %s#%s(type=%s) %.2f" % (q["id"], q["type"], s[0], s[1], s[2], best[0]))
            print("    新:", q["stem"][:70])
            print("    旧:", s[3][:70])
    print("  命中:", hits)


if __name__ == "__main__":
    main()
