#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""党课题库：Markdown 源 → 静态网页数据（每套一个 set JSON）

用法（在题库根目录执行，Windows 示例）：
  python site\\source\\md2json.py 党课题库.md ^
      --set 2026-11-15-01 --title "第一套（1—100题）" ^
      --out site\\data\\sets --manifest site\\data\\manifest.json

只导出新做的一套题（按原题号区间）：
  python site\\source\\md2json.py 党课题库.md --set 2026-11-16-01 ^
      --title "第二套" --from 101 --to 200 ^
      --out site\\data\\sets --manifest site\\data\\manifest.json

规则：
  * 题干下的「**时间：**1924—1927」行优先；没有则按 TIME_RULES 关键词自动猜；
  * 自动猜不到的把时间留空，网页归入「时间待定」组，可用 corrections.json 补。
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

TYPE_MAP = {'单选题': 'single', '多选题': 'multiple', '填空题': 'blank', '判断题': 'judge'}

# (正则, 显示标签, 排序值 YYYYMM00) —— 从上往下匹配，先匹配先生效，可按需增删
TIME_RULES = [
    # ① 党的全国代表大会与中央全会（先具体、后笼统）
    (r'二十大|党的二十大', '2022年10月 二十大', 20221016),
    (r'十九届六中全会', '2021年11月 十九届六中全会', 20211111),
    (r'十九届五中全会', '2020年10月 十九届五中全会', 20201026),
    (r'十九届四中全会', '2019年10月 十九届四中全会', 20191028),
    (r'十九届三中全会', '2018年2月 十九届三中全会', 20180226),
    (r'十八届六中全会', '2016年10月 十八届六中全会', 20161024),
    (r'十八届五中全会', '2015年10月 十八届五中全会', 20151026),
    (r'十八届中央纪委五次全会', '2015年1月 十八届中央纪委五次全会', 20150113),
    (r'十八届四中全会', '2014年10月 十八届四中全会', 20141020),
    (r'十八届三中全会', '2013年11月 十八届三中全会', 20131109),
    (r'十九大|党的十九大', '2017年10月 十九大', 20171018),
    (r'十八大', '2012年11月 十八大', 20121108),
    (r'十七大', '2007年10月 十七大', 20071015),
    (r'十六大', '2002年11月 十六大', 20021108),
    (r'十五大', '1997年9月 十五大', 19970912),
    (r'十四大', '1992年10月 十四大', 19921012),
    (r'十三大', '1987年10月 十三大', 19871025),
    (r'十二大', '1982年9月 十二大', 19820901),
    (r'十一届六中全会|历史问题的决议', '1981年6月 十一届六中全会', 19810627),
    (r'十一届三中全会', '1978年12月 十一届三中全会', 19781218),
    (r'九大', '1969年4月 九大', 19690401),
    # ② 党史重大事件
    (r'遵义会议', '1935年1月 遵义会议', 19350115),
    (r'抗日|日本帝国主义|抗战', '1937—1945年 抗战', 19370000),
    (r'大革命', '1924—1927年 大革命', 19240000),
    (r'秋收起义|井冈山', '1927年9月 秋收起义', 19270909),
    (r'南昌起义', '1927年8月 南昌起义', 19270801),
    (r'新中国成立|中华人民共和国成立', '1949年10月 新中国成立', 19491001),
    (r'三大改造|社会主义改造', '1956年 社会主义改造完成', 19560000),
    (r'七大|论联合政府', '1945年4月 七大', 19450423),
    (r'1941\s*年', '1941年 延安时期', 19410000),
    (r'列宁|1902\s*年', '1902年 列宁《怎么办？》', 19020000),
    (r'实践论|矛盾论', '1937年7月 两论', 19370700),
    (r'解放战争', '1946年6月 解放战争', 19460600),
    (r'惩前毖后|治病救人|整风', '1942年 延安整风', 19420000),
    (r'基本路线', '1987年10月 党的基本路线', 19871025),
    (r'改革开放', '1978年12月 改革开放', 19781218),
    (r'生态文明|绿水青山', '2012年11月 生态文明建设', 20121108),
    # ③ 制度类：按文件出台/修订时间（题干若有历史事件，上面的规则会先命中）
    (r'纪律处分条例|留党察看|开除党籍|严重警告', '2023年12月 纪律处分条例', 20231219),
    (r'问责条例', '2019年9月 问责条例', 20190904),
    (r'党员权利保障条例', '2020年12月 党员权利保障条例', 20201225),
    (r'发展党员工作细则', '2014年5月 发展党员工作细则', 20140528),
    (r'党章', '2022年10月 现行党章', 20221016),
    (r'宪法', '2018年3月 宪法修正案', 20180311),
]

TAG_RULES = [
    (r'二十大|十九大|十八大', ['重要讲话']),
    (r'纪律处分条例|留党察看|开除党籍|严重警告|警告|处分', ['纪律处分']),
    (r'党章', ['党章']),
    (r'入党|预备党员|积极分子|入党动机', ['入党']),
    (r'生态文明|绿水青山|自然', ['生态文明']),
    (r'马克思主义|列宁|毛泽东|邓小平|三个代表|科学发展观|实事求是', ['理论']),
    (r'大革命|起义|抗日|解放战争|革命', ['党史']),
    (r'统一战线|多党合作|政协', ['统战']),
    (r'军队|强军|国防', ['军事']),
]

FIELDS = {'**题干：**': 'stem', '**选项：**': 'options', '**答案：**': 'answer',
          '**解析：**': 'explain', '**时间：**': 'time'}


def parse_md(text):
    section, cur, field, out = None, None, None, []
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r'^##\s*[一二三四五六七八九十]+、\s*(\S+)', line)
        if m:
            if cur:
                out.append(cur)   # 切换题型前先收下上一题型最后一题
            section = TYPE_MAP.get(m.group(1))
            cur, field = None, None
            continue
        m = re.match(r'^###\s*(?:补充)?第\s*(\d+)\s*题', line)
        if m:
            if cur:
                out.append(cur)
            cur = {'no': int(m.group(1)), 'type': section, 'stem': '', 'options': '',
                   'answer': '', 'explain': '', 'time_raw': ''}
            field = None
            continue
        if cur is None:
            continue
        hit = next(((p, n) for p, n in FIELDS.items() if line.startswith(p)), None)
        if hit:
            prefix, name = hit
            field = name
            val = line[len(prefix):].strip()
            if name == 'time':
                cur['time_raw'] = val
            else:
                cur[name] = val
            continue
        if field and line and not line.startswith('---') and not line.startswith('>'):
            if field == 'time':
                cur['time_raw'] += line
            else:
                cur[field] += '\n' + line
    if cur:
        out.append(cur)
    return out


def split_options(s):
    if not s:
        return []
    parts = re.split(r'[\s\u3000]+(?=[A-D][.、])', s.strip())
    return [p.strip() for p in parts if p.strip()]


def answer_keys(ans, qtype):
    if qtype == 'judge':
        return ['正确'] if '正确' in ans else (['错误'] if '错误' in ans else [])
    if qtype == 'blank':
        return []
    return sorted(set(re.findall(r'(?<![A-Za-z])([A-D])(?![A-Za-z])', ans)))


def parse_time(raw):
    if not raw:
        return None
    m = re.search(r'(\d{4})', raw)
    if not m:
        return None
    y = int(m.group(1))
    mm = re.search(r'(\d{1,2})\s*月', raw)
    mo = int(mm.group(1)) if mm else 0
    return {'label': raw.split('|')[0].strip(), 'sort': y * 10000 + mo * 100, 'note': '手工标注'}


def guess_time(text):
    for pat, label, sort in TIME_RULES:
        if re.search(pat, text):
            short, _, rest = label.partition(' ')
            return {'label': short, 'sort': sort, 'note': '按题干关键词标注：' + (rest or short)}
    return None


def tags_of(text):
    ts = []
    for pat, t in TAG_RULES:
        if re.search(pat, text):
            ts += t
    return sorted(set(ts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md')
    ap.add_argument('--set', required=True)
    ap.add_argument('--title', default='')
    ap.add_argument('--date', default='')
    ap.add_argument('--from', dest='q_from', type=int, default=0, help='起始原题号（含）')
    ap.add_argument('--to', dest='q_to', type=int, default=10 ** 9, help='结束原题号（含）')
    ap.add_argument('--out', default='data/sets')
    ap.add_argument('--manifest', default='')
    ap.add_argument('--no-manifest', action='store_true')
    a = ap.parse_args()

    text = Path(a.md).read_text(encoding='utf-8-sig')
    parsed = parse_md(text)
    questions, used, nodate = [], set(), []
    for q in parsed:
        if not q['stem'] or not (a.q_from <= q['no'] <= a.q_to):
            continue
        qid = f"{a.set}-{q['no']:03d}"
        k = 1
        while qid in used:
            k += 1
            qid = f"{a.set}-{q['no']:03d}-{k}"
        used.add(qid)
        t = parse_time(q['time_raw']) or guess_time(q['stem'] + '\n' + q['explain'])
        if not t:
            nodate.append(q['no'])
        questions.append({
            'id': qid,
            'no': q['no'],
            'type': q['type'],
            'stem': q['stem'].strip(),
            'options': split_options(q['options']),
            'answer': q['answer'].strip(),
            'answerKeys': answer_keys(q['answer'], q['type']),
            'explain': q['explain'].strip(),
            'time': t,
            'tags': tags_of(q['stem'] + '\n' + q['explain']),
        })

    if not questions:
        sys.exit('没有解析到题目：检查 --from/--to 区间或 Markdown 格式（### 第 N 题 / **题干：** 等）。')

    date = a.date or (a.set[:10] if re.match(r'^\d{4}-\d{2}-\d{2}', a.set) else '')
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{a.set}.json"
    obj = {'setId': a.set, 'title': a.title or a.set, 'uploadedAt': date, 'questions': questions}
    (out_dir / fname).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')

    if a.manifest and not a.no_manifest:
        mp = Path(a.manifest)
        data = json.loads(mp.read_text(encoding='utf-8')) if mp.exists() else {'sets': []}
        if fname not in data['sets']:
            data['sets'].append(fname)
            mp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')

    c = Counter(q['type'] for q in questions)
    print(f"OK 写入 {out_dir / fname}：{len(questions)} 题"
          f"（单选 {c['single']}、多选 {c['multiple']}、填空 {c['blank']}、判断 {c['judge']}）")
    print(f"   已标时间 {len(questions) - len(nodate)} 题；时间待定 {len(nodate)} 题"
          + (f" → 题号 {nodate}" if nodate else ''))
    if a.manifest and not a.no_manifest:
        print(f"   manifest 已更新：{a.manifest}")


if __name__ == '__main__':
    main()
