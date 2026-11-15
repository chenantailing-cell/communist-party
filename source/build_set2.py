# -*- coding: utf-8 -*-
"""把 截图1-合并.tsv（转录去重版）+ 截图1-答案.tsv（人工答案）合成第二套题：
   - site/data/sets/2026-11-15-02.json
   - 追加 site/data/manifest.json
   - 生成人类可读的 题库-第二套.md
   - 追加 site/CHANGELOG.md 一行
"""
import io, json, os, re, sys
from pathlib import Path

ROOT = Path(r"D:\6  题库")
SITE = ROOT / "site"
sys.path.insert(0, str(SITE / "source"))
from md2json import TIME_RULES, TAG_RULES, guess_time, tags_of, split_options, answer_keys, TYPE_MAP  # noqa

SET_ID = "2026-11-15-02"
SET_TITLE = "2026.11 入党积极分子模拟测试"
TYPES = ["单选题", "多选题", "填空题", "判断题"]
SHORT = {"单选题": "s", "多选题": "m", "填空题": "b", "判断题": "j"}


def read_tsv(p, cols):
    out = []
    for line in io.open(p, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#") or line.startswith("批次") or line.startswith("题型"):
            continue
        parts = line.split("\t") if "\t" in line else line.split("|")
        parts = [x.strip() for x in parts]
        if len(parts) < len(cols):
            parts += [""] * (len(cols) - len(parts))
        out.append(dict(zip(cols, parts[:len(cols)])))
    return out


def clean(s):
    s = (s or "").strip()
    s = re.sub(r"[（(]\s*1\s*分\s*[)）]\s*$", "", s).strip()
    return s


# ---- 1. 合并转录，按 (题型, 题号) 取信息最全的一条 ----
rows = read_tsv(ROOT / "截图1-合并.tsv", ["题型", "题号", "题干", "选项", "答案", "备注", "批次"])
best = {}
for r in rows:
    t, no = r["题型"], re.sub(r"\D", "", r["题号"])
    if t not in TYPES or not no:
        continue
    k = (t, int(no))
    score = len(clean(r["题干"])) + len(r["选项"] or "")
    if k not in best or score > best[k]["score"]:
        best[k] = dict(r, no=int(no), score=score)

# ---- 2. 答案表 ----
ans = {}
for r in read_tsv(ROOT / "截图1-答案.tsv", ["题型", "题号", "答案", "解析"]):
    ans[(r["题型"], int(re.sub(r"\D", "", r["题号"]) or 0))] = (r["答案"].strip(), r["解析"].strip())

questions, missing = [], []
for t in TYPES:
    for k in sorted([x for x in best if x[0] == t], key=lambda x: x[1]):
        r = best[k]
        a = ans.get(k)
        if not a:
            missing.append(k)
            continue
        answer, explain = a
        stem = clean(r["题干"])
        opts = split_options(r["选项"]) if t in ("单选题", "多选题") else (["正确", "错误"] if t == "判断题" else [])
        qid = "%s-%s%02d" % (SET_ID, SHORT[t], r["no"])
        questions.append({
            "id": qid,
            "no": r["no"],
            "type": TYPE_MAP[t],
            "stem": stem,
            "options": opts,
            "answer": answer,
            "answerKeys": answer_keys(answer, TYPE_MAP[t]),
            "explain": explain,
            "time": guess_time(stem + "\n" + explain),
            "tags": tags_of(stem + "\n" + explain),
        })

if missing:
    print("缺答案:", missing)

# 重编号：同一题型内按题号，页面上用 setId + no 显示，无需担心重复
obj = {"setId": SET_ID, "title": SET_TITLE, "uploadedAt": "2026-11-15", "questions": questions}
out = SITE / "data" / "sets" / (SET_ID + ".json")
out.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

# manifest 追加
mf = SITE / "data" / "manifest.json"
m = json.loads(mf.read_text(encoding="utf-8"))
if SET_ID + ".json" not in m["sets"]:
    m["sets"].append(SET_ID + ".json")
    mf.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")

# ---- 3. 生成 md（归位，便于日后比对/再转换）----
lines = ["# 题库·第二套（%s）" % SET_TITLE, "",
         "> 来源：D:\\6  题库\\截图1（99 张截图，8 批并行转录后人工复核）。",
         "> 本卷四类题各自独立编号（单选题 1—30、多选题 1—30、填空题 1—20、判断题 1—20），共 %d 题。" % len(questions),
         "> 生成时间：2026-11-15。", "", "---", ""]
for t in TYPES:
    lines.append("## %s" % t)
    lines.append("")
    for q in [x for x in questions if x["type"] == TYPE_MAP[t]]:
        lines.append("### 第 %d 题" % q["no"])
        lines.append("")
        lines.append("**题干：** " + q["stem"])
        lines.append("")
        if q["options"]:
            lines.append("**选项：** " + "　".join(q["options"]))
            lines.append("")
        lines.append("**答案：** " + q["answer"])
        lines.append("")
        lines.append("**解析：** " + q["explain"])
        lines.append("")
    lines.append("---")
    lines.append("")
(ROOT / "题库-第二套.md").write_text("\n".join(lines), encoding="utf-8")

# ---- 4. CHANGELOG ----
ch = SITE / "CHANGELOG.md"
txt = ch.read_text(encoding="utf-8")
row = "| 2026-11-15 | %s | 单选30 多选30 填空20 判断20 | %d | 无（新建） | 截图1 转录复核后并入 |" % (SET_ID, len(questions))
if SET_ID not in txt:
    ch.write_text(txt.rstrip() + "\n" + row + "\n", encoding="utf-8")

nodate = [q["no"] for q in questions if not q["time"]]
print("questions=%d  有时间=%d  待定时间=%d  %s" % (len(questions), len(questions) - len(nodate), len(nodate), nodate))
print("json ->", out)
