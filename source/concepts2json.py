#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「概念」分类：Markdown 源 → site/data/concepts.json

用法（在题库根目录执行）：
  python site\\source\\concepts2json.py site\\source\\概念.md --out site\\data\\concepts.json

源文件格式（一课一节，每条概念一个小节）：

  ## 第一课 党的性质与指导思想

  ### 第 1 条

  **概念：** 党的性质

  **释义：** 中国共产党是中国工人阶级的先锋队……

  **补充：** （补充释义必须整体用括号括起）

  **时间：** 2022年10月 现行党章      ← 可省略

  **标签：** 党章、性质                ← 可省略，课次标签会自动加

规则：
  * 课次取自「## 第X课」标题，条目 id = concept-课次-条号；
  * 「**补充：**」是唯一允许的补充释义位置，且必须整体用（）括起；
  * 同课内重名、条号重复直接报错，不写入；跨课重名只提示，留给最后统一合并。
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

CN_DIGITS = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
             '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}

FIELDS = [
    ('概念', 'stem'), ('释义', 'answer'), ('补充', 'explain'),
    ('时间', 'time_raw'), ('标签', 'tags'),
]


def cn_num(s):
    """第一课 / 第十一课 / 第12课 → 整数。"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    if '十' in s:
        left, _, right = s.partition('十')
        tens = CN_DIGITS.get(left, 1) if left else 1
        ones = CN_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    n = 0
    for ch in s:
        if ch not in CN_DIGITS:
            raise ValueError(f'无法识别的课次：{s}')
        n = CN_DIGITS[ch]
    return n


def field_hit(line):
    """匹配 **概念：** / **概念**: / **概念**： 等写法。"""
    for label, name in FIELDS:
        m = re.match(r'^\*\*\s*' + label + r'\s*[：:]\s*\*\*\s*(.*)$', line)
        if not m:
            m = re.match(r'^\*\*\s*' + label + r'\s*\*\*\s*[：:]\s*(.*)$', line)
        if m:
            return name, m.group(1)
    return None, None


def parse_md(text):
    lessons, cur_lesson, cur, field = [], None, None, None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r'^##\s*第\s*([一二三四五六七八九十百零〇两\d]+)\s*课\s*(.*)$', line)
        if m:
            if cur:
                cur_lesson['items'].append(cur)
            title = m.group(2).strip(' \u3000|｜:：-—')
            cur_lesson = {'no': cn_num(m.group(1)), 'title': title, 'items': []}
            lessons.append(cur_lesson)
            cur, field = None, None
            continue
        m = re.match(r'^###\s*第\s*(\d+)\s*条', line)
        if m:
            if cur:
                cur_lesson['items'].append(cur)
            cur = {'no': int(m.group(1)), 'stem': '', 'answer': '', 'explain': '',
                   'time_raw': '', 'tags': ''}
            field = None
            continue
        if cur is None:
            continue
        name, val = field_hit(line)
        if name:
            field = name
            cur[name] = val
            continue
        if field and line and not line.startswith(('---', '>', '#')):
            cur[field] += '\n' + line
    if cur:
        cur_lesson['items'].append(cur)
    return lessons


def split_tags(s):
    return [t for t in re.split(r'[、,，;；/\s]+', s.strip()) if t]


def parse_time(raw):
    raw = raw.strip()
    if not raw:
        return None
    m = re.search(r'(\d{4})', raw)
    if not m:
        return None
    y = int(m.group(1))
    mm = re.search(r'(\d{1,2})\s*月', raw)
    mo = int(mm.group(1)) if mm else 0
    return {'label': raw, 'sort': y * 10000 + mo * 100, 'note': '手工标注'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md')
    ap.add_argument('--out', default='site/data/concepts.json')
    ap.add_argument('--date', default='')
    a = ap.parse_args()

    path = Path(a.md)
    if not path.exists():
        sys.exit(f'源文件不存在：{path}')
    lessons = parse_md(path.read_text(encoding='utf-8-sig'))

    errors, warnings = [], []
    seen_no, seen_stem, all_stems = set(), {}, {}

    for lesson in lessons:
        lno = lesson['no']
        if not 1 <= lno <= 11:
            warnings.append(f'第{lno}课不在 1—11 范围内（确认课次是否写错）')
        for item in lesson['items']:
            where = f"第{lno}课第{item['no']}条"
            if not item['stem'].strip():
                errors.append(f'{where}：缺少「概念」')
                continue
            if not item['answer'].strip():
                errors.append(f'{where}「{item["stem"]}」：缺少「释义」')
            stem = item['stem'].strip()
            if (lno, stem) in seen_stem:
                errors.append(f'{where}「{stem}」：同课内重复（{seen_stem[(lno, stem)]}）')
            seen_stem[(lno, stem)] = where
            if (lno, item['no']) in seen_no:
                errors.append(f'{where}：同课内条号重复')
            seen_no.add((lno, item['no']))
            if stem in all_stems and all_stems[stem] != lno:
                warnings.append(f'跨课重名：「{stem}」（第{all_stems[stem]}课 / 第{lno}课），最后统一合并时确认')
            else:
                all_stems.setdefault(stem, lno)
            sup = item['explain'].strip()
            if sup and not (sup.startswith('（') and sup.endswith('）')):
                errors.append(f'{where}「{stem}」：补充释义必须整体用（）括起：{sup[:40]}')

    if errors:
        print('未写入，请先处理以下问题：')
        for e in errors:
            print('  ✗', e)
        for w in warnings:
            print('  ! ', w)
        sys.exit(1)

    items = []
    for lesson in lessons:
        lno = lesson['no']
        for item in lesson['items']:
            tags = split_tags(item['tags'])
            tags = ['概念', f'第{lno}课'] + sorted(set(tags) - {'概念', f'第{lno}课'})
            items.append({
                'id': f'concept-{lno:02d}-{item["no"]:03d}',
                'no': item['no'],
                'lesson': lno,
                'lessonTitle': lesson['title'],
                'type': 'concept',
                'stem': item['stem'].strip(),
                'options': [],
                'answer': item['answer'].strip(),
                'answerKeys': [],
                'explain': item['explain'].strip(),
                'time': parse_time(item['time_raw']),
                'tags': tags,
            })

    lesson_list = [{'no': l['no'], 'title': l['title'], 'count': len(l['items'])} for l in lessons]
    obj = {
        'setId': 'concepts',
        'title': '概念（十一课）',
        'uploadedAt': a.date or date.today().isoformat(),
        'source': '按课次整理，来自用户陆续提供的十一课内容；括号内为补充释义',
        'lessons': lesson_list,
        'items': items,
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f'OK 写入 {out}：{len(items)} 条概念，{len(lesson_list)} 课')
    for l in lesson_list:
        print(f'   第{l["no"]}课{" " + l["title"] if l["title"] else ""}：{l["count"]} 条')
    for w in warnings:
        print('   ! ', w)


if __name__ == '__main__':
    main()
