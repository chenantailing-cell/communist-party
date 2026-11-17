# -*- coding: utf-8 -*-
"""把 题库-src.json（1088 题）+ 答案/*.tsv（人工作答）合成第三套：
   - 与站点已有 set 比对，跳过重复题
   - site/data/sets/2026-11-17-03.json
   - 追加 manifest、生成 题库-第三套.md、追加 CHANGELOG
"""
import difflib, io, json, re, sys
from pathlib import Path

ROOT = Path(r"D:\6  题库")
SITE = ROOT / "site"
sys.path.insert(0, str(SITE / "source"))
from md2json import guess_time, tags_of, answer_keys, TYPE_MAP  # noqa

SET_ID = "2026-11-17-03"
SET_TITLE = "入党积极分子在线培训题库（中国海洋大学）"
SRC = ROOT / "题库-src.json"
ANS = {"single": ("答案/single.tsv", "s"), "multiple": ("答案/multi.tsv", "m"),
       "judge": ("答案/judge.tsv", "j"), "blank": ("答案/blank.tsv", "b")}
TYPE_NAME = {"single": "单选题", "multiple": "多选题", "blank": "填空题", "judge": "判断题"}


def norm(s):
    return re.sub(r"[\s\W_]+", "", s or "")


def read_ans(path):
    out = {}
    for line in io.open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("id\t") or line.startswith("#"):
            continue
        parts = [x.strip() for x in line.split("\t")]
        if len(parts) >= 2:
            out[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else "", parts[3] if len(parts) > 3 else "")
    return out


# 站点已有题
existing = []
mf = json.loads((SITE / "data/manifest.json").read_text(encoding="utf-8"))
for name in mf["sets"]:
    if name == SET_ID + ".json":
        continue
    d = json.loads((SITE / "data/sets" / name).read_text(encoding="utf-8"))
    for q in d["questions"]:
        existing.append((norm(q["stem"]), name, q["no"], q.get("answer", "")))
print("站点已有题：", len(existing))

src = json.loads(SRC.read_text(encoding="utf-8"))
questions, dups, noans = [], [], []
for item in src:
    t = item["type"]
    qid = item["id"]
    ansfile, _ = ANS[t]
    ans = read_ans(ROOT / ansfile).get(qid)
    if not ans or not ans[0]:
        noans.append(qid)
        continue
    answer, basis, note = ans
    stem = item["stem"].strip()
    n = norm(stem)
    hit = None
    for e in existing:
        if difflib.SequenceMatcher(None, n, e[0]).ratio() >= 0.86:
            hit = e
            break
    if hit:
        dups.append((qid, stem[:30], hit[1], hit[2]))
        continue
    explain = basis.strip()
    if note and note not in ("-", ""):
        explain = explain + "（" + note + "）"
    options = []
    for o in (item.get("options") or []):
        if isinstance(o, dict):
            options.append("%s. %s" % (o.get("label", ""), o.get("text", "")))
        else:
            options.append(str(o))
    if t == "judge":
        options = ["正确", "错误"]
    questions.append({
        "id": SET_ID + "-" + qid,
        "no": item["no"],
        "type": TYPE_MAP[TYPE_NAME[t]],
        "stem": stem,
        "options": options,
        "answer": answer,
        "answerKeys": answer_keys(answer, TYPE_MAP[TYPE_NAME[t]]),
        "explain": explain,
        "time": guess_time(stem + "\n" + explain),
        "tags": tags_of(stem + "\n" + explain),
    })

obj = {"setId": SET_ID, "title": SET_TITLE, "uploadedAt": "2026-11-17", "questions": questions}
out = SITE / "data/sets" / (SET_ID + ".json")
out.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

m = json.loads((SITE / "data/manifest.json").read_text(encoding="utf-8"))
if SET_ID + ".json" not in m["sets"]:
    m["sets"].append(SET_ID + ".json")
    (SITE / "data/manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")

# md
lines = ["# 题库·第三套（%s）" % SET_TITLE, "",
         "> 来源：D:\\6  题库\\题库\\题库.txt（入党积极分子在线培训题库，http://dxzx.ouc.edu.cn/jjfz/exam_center）。",
         "> 原文件 1088 题（单选 388 / 多选 267 / 判断 251 / 填空 182），逐题作答后去除与站点重复的 %d 题，本套收录 %d 题。" % (len(dups), len(questions)),
         "> 生成时间：2026-11-17。", "", "---", ""]
for t in ["single", "multiple", "blank", "judge"]:
    ty = TYPE_MAP[TYPE_NAME[t]]
    lines.append("## %s" % TYPE_NAME[t])
    lines.append("")
    for q in [x for x in questions if x["type"] == ty]:
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
(ROOT / "题库-第三套.md").write_text("\n".join(lines), encoding="utf-8")

ch = SITE / "CHANGELOG.md"
txt = ch.read_text(encoding="utf-8")
row = "| 2026-11-17 | %s | 单选%s 多选%s 判断%s 填空%s | %d | 无 | 题库.txt 逐题作答，去重后并入 |" % (
    SET_ID,
    sum(1 for q in questions if q["type"] == "单选题"), sum(1 for q in questions if q["type"] == "多选题"),
    sum(1 for q in questions if q["type"] == "判断题"), sum(1 for q in questions if q["type"] == "填空题"),
    len(questions))
if SET_ID not in txt:
    ch.write_text(txt.rstrip() + "\n" + row + "\n", encoding="utf-8")

nodate = sum(1 for q in questions if not q["time"])
print("收录=%d 跳过重复=%d 缺答案=%d 有日期=%d 待定=%d" % (len(questions), len(dups), len(noans), len(questions) - nodate, nodate))
print("json ->", out)
if noans:
    print("缺答案 id:", noans[:20])
