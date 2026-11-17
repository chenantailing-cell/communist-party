#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""党史 md → data/history.json

用法：
    python source/history2json.py source/党史.md --out data/history.json

md 约定：
    ## 一、阶段标题（年份区间）
    ### 第 N 条
    **时间：** 1921年7月
    **地点：** ……
    **人物：** ……
    **事件：** ……
    **影响：** ……
    **标签：** 建党；一大

校验：五个要素齐全；时间能解析出年份；条号不重复且按时间递增。
"""
import argparse
import json
import re
import sys
from pathlib import Path

FIELDS = {
    '时间': 'time',
    '地点': 'place',
    '人物': 'people',
    '事件': 'event',
    '影响': 'impact',
    '标签': 'tags',
}
REQUIRED = ['time', 'place', 'people', 'event', 'impact']
FIELD_RE = re.compile(r'^\*\*(时间|地点|人物|事件|影响|标签)：\*\*\s*(.*)$')
HEAD_RE = re.compile(r'^###\s*第\s*(\d+)\s*条\s*$')
STAGE_RE = re.compile(r'^##\s*(.+?)\s*$')
TIME_RE = re.compile(r'(\d{4})\s*年(?:\s*(\d{1,2})\s*月)?(?:\s*(\d{1,2})\s*日)?')


def parse_md(text):
    stages = []
    stage = None
    cur = None
    field = None

    def flush():
        nonlocal cur, field
        if cur is not None:
            if stage is None:
                raise SystemExit(f'第 {cur["no"]} 条不在任何阶段标题下')
            stage['items'].append(cur)
            cur = None
        field = None

    for raw in text.splitlines():
        line = raw.rstrip()
        m = HEAD_RE.match(line)
        if m:
            flush()
            cur = {'no': int(m.group(1)), 'raw': {}}
            continue
        m = STAGE_RE.match(line)
        if m and not line.startswith('###'):
            flush()
            stage = {'title': m.group(1).strip(), 'items': []}
            stages.append(stage)
            continue
        m = FIELD_RE.match(line)
        if m and cur is not None:
            field = FIELDS[m.group(1)]
            cur['raw'][field] = m.group(2).strip()
            continue
        if cur is not None and field and line.strip():
            cur['raw'][field] = (cur['raw'].get(field, '') + '\n' + line.strip()).strip()
        elif not line.strip():
            field = None
    flush()
    return stages


def to_sort(label):
    m = TIME_RE.search(label or '')
    if not m:
        return None
    y = int(m.group(1))
    mo = int(m.group(2) or 1)
    d = int(m.group(3) or 1)
    return y * 10000 + mo * 100 + d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    src = Path(args.src)
    stages = parse_md(src.read_text(encoding='utf-8'))
    events = []
    problems = []
    seen_no = set()
    for si, st in enumerate(stages, 1):
        for it in st['items']:
            no = it['no']
            raw = it['raw']
            if no in seen_no:
                problems.append(f'条号重复：{no}')
            seen_no.add(no)
            for key in REQUIRED:
                if not raw.get(key, '').strip():
                    problems.append(f'第 {no} 条缺{key}')
            label = raw.get('time', '').strip()
            sort = to_sort(label)
            if sort is None:
                problems.append(f'第 {no} 条时间无法解析：{label}')
            tags = [t.strip() for t in re.split(r'[；;、,，]', raw.get('tags', '')) if t.strip()]
            events.append({
                'id': f'history-{no:03d}',
                'no': no,
                'stageNo': si,
                'stage': st['title'],
                'sort': sort,
                'time': label,
                'place': raw.get('place', '').strip(),
                'people': raw.get('people', '').strip(),
                'event': raw.get('event', '').strip(),
                'impact': raw.get('impact', '').strip(),
                'tags': tags,
            })

    events.sort(key=lambda x: (x['sort'] or 0, x['no']))
    for a, b in zip(events, events[1:]):
        if a['sort'] and b['sort'] and a['sort'] > b['sort']:
            problems.append(f'时间顺序颠倒：{a["no"]}（{a["time"]}）在 {b["no"]}（{b["time"]}）之后')

    if problems:
        print('校验失败：', file=sys.stderr)
        for p in problems:
            print('  -', p, file=sys.stderr)
        return 1

    stage_summary = []
    for si, st in enumerate(stages, 1):
        items = [e for e in events if e['stageNo'] == si]
        stage_summary.append({'no': si, 'title': st['title'], 'count': len(items)})

    doc = {
        'setId': 'history',
        'title': '党史专栏',
        'updatedAt': '2026-11-17',
        'intro': '按时间顺序记载中国共产党成立以来的重要历史事件；每条含时间、地点、人物、事件、影响五项，影响另起一段。',
        'stages': stage_summary,
        'events': events,
    }
    out = Path(args.out)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'OK 写入 {out}：{len(events)} 条事件，{len(stage_summary)} 个阶段')
    for s in stage_summary:
        print(f'   {s["title"]}：{s["count"]} 条')
    return 0


if __name__ == '__main__':
    sys.exit(main())
