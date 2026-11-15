# -*- coding: utf-8 -*-
import re, io, os
from collections import defaultdict

ROOT = r"D:\6  题库"
FILES = ["截图1-转录.tsv", "截图1-转录-A.tsv", "截图1-转录-B.tsv"]

TYPES = {"单选": "单选题", "多选": "多选题", "填空": "填空题", "判断": "判断题",
         "单选题": "单选题", "多选题": "多选题", "填空题": "填空题", "判断题": "判断题"}
ORDER = ["单选题", "多选题", "填空题", "判断题"]

rows, rep = [], []
def R(s=""):
    rep.append(s)

for fn in FILES:
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        R("MISSING " + p); continue
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("批次"):
            continue
        parts = [x.strip() for x in line.split("|")]
        if len(parts) < 6:
            R("SHORT: " + line[:60]); continue
        batch, typ, no, stem, opts, ans = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        note = parts[-1] if len(parts) >= 7 else ""
        t = TYPES.get(typ.replace("题", "").strip()) or TYPES.get(typ.strip())
        if not t:
            R("BADTYPE: %s | %s" % (typ, line[:50])); continue
        rows.append(dict(batch=batch, type=t, no=no, stem=stem, opts=opts, ans=ans, note=note, src=fn))

def norm(s):
    return re.sub(r"[\s，。、（）()“”\"'：:；;？?！!\-—·]", "", s or "")

def key(r):
    return (r["type"], norm(r["stem"])[:30])

real = [r for r in rows if not r["stem"].startswith("（题干") and norm(r["stem"])]
ph = [r for r in rows if r["stem"].startswith("（题干")]

merged = {}
for r in real:
    k = key(r)
    if k not in merged:
        merged[k] = dict(r, batches=[r["batch"]], alts=defaultdict(set))
    else:
        m = merged[k]
        if r["batch"] not in m["batches"]:
            m["batches"].append(r["batch"])
        for f in ("ans", "opts"):
            if r[f] and r[f] not in ("待定", "-", "未见", "选项未显示", "选项未拍到") and len(r[f]) > len(m[f] or ""):
                if r[f] != m[f]:
                    m["alts"][f].add(r[f])
                m[f] = r[f]
        if r["note"] and r["note"] not in (m.get("note") or ""):
            m["note"] = ((m.get("note") or "") + " / " + r["note"]).strip(" /")

by_type = defaultdict(list)
for m in merged.values():
    by_type[m["type"]].append(m)

R("原始行 %d｜占位(截断) %d｜真实 %d｜去重后 %d" % (len(rows), len(ph), len(real), len(merged)))
for t in ORDER:
    lst = by_type[t]
    nos = sorted({int(re.sub(r"\D", "", x["no"]) or 0) for x in lst})
    R("%s：%d 题，题号 %s" % (t, len(lst), nos))

R("\n==== 需回图补全/裁决的题 ====")
need = []
for t in ORDER:
    for x in sorted(by_type[t], key=lambda y: (len(y["no"]), y["no"])):
        alts = {k: sorted(v) for k, v in x["alts"].items() if v}
        bad = (x["ans"] in ("待定", "-", "")) or ("待定" in (x["note"] or "")) or alts
        if bad:
            need.append(x)
            R("\n[%s %s] ans=%s batches=%s" % (t, x["no"], x["ans"], ",".join(x["batches"])))
            R("  题干：" + x["stem"][:90])
            R("  选项：" + (x["opts"] or "")[:160])
            if alts: R("  冲突：" + str(alts))
            if x["note"]: R("  备注：" + x["note"][:100])
R("\n需处理共 %d 题" % len(need))

R("\n==== 占位行（完全没录入的真行，需按图补） ====")
for r in ph:
    R("[%s %s] %s | %s" % (r["type"], r["no"], r["stem"][:40], r["note"][:40]))

out = os.path.join(ROOT, "截图1-合并.tsv")
with io.open(out, "w", encoding="utf-8") as f:
    f.write("题型\t题号\t题干\t选项\t答案\t备注\t批次\n")
    for t in ORDER:
        for x in sorted(by_type[t], key=lambda y: (len(y["no"]), y["no"])):
            f.write("\t".join([t, x["no"], x["stem"], x["opts"], x["ans"], (x["note"] or ""), ",".join(x["batches"])]) + "\n")

rp = os.path.join(ROOT, "截图1-复核清单.txt")
io.open(rp, "w", encoding="utf-8").write("\n".join(rep))
print("rows=%d ph=%d merged=%d need=%d" % (len(rows), len(ph), len(merged), len(need)))
print("report ->", rp)
print("merged ->", out)
