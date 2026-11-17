# -*- coding: utf-8 -*-
"""尝试多个候选 URL，把能取到正文（>2000 字）的存到 资料/。"""
import re
import sys
import urllib.request
from html import unescape
from pathlib import Path

OUT = Path(r"D:\6  题库\资料")
OUT.mkdir(parents=True, exist_ok=True)

CAND = {
    "二十大报告": [
        "http://www.gov.cn/gongbao/content/2022/content_5722378.htm",
        "https://www.12371.cn/2022/10/25/ARTI1666788342254323.shtml",
    ],
    "纪律处分条例2023": [
        "https://www.gov.cn/zhengce/202312/content_6922808.htm",
        "https://www.ccdi.gov.cn/toutiaon/202312/t20231227_317939.html",
        "https://www.12371.cn/2023/12/27/ARTI1703662659876505.shtml",
    ],
    "党员权利保障条例2020": [
        "https://www.gov.cn/zhengce/2020-12/25/content_5573388.htm",
        "https://www.12371.cn/2020/12/25/ARTI1608887706099927.shtml",
    ],
    "发展党员工作细则2014": [
        "https://www.gov.cn/xinwen/2014-06/10/content_2698245.htm",
        "https://www.12371.cn/2014/06/10/ARTI1402405405611185.shtml",
    ],
    "支部工作条例2018": [
        "https://www.gov.cn/zhengce/2018-11/25/content_5343238.htm",
        "https://www.12371.cn/2018/11/25/ARTI1543106051564946.shtml",
    ],
    "问责条例2019": [
        "https://www.gov.cn/zhengce/2019-09/04/content_5427226.htm",
        "https://www.12371.cn/2019/09/04/ARTI1567587081131862.shtml",
    ],
    "廉洁自律准则2015": [
        "https://www.gov.cn/zhengce/2015-10/21/content_5152254.htm",
    ],
    "党内监督条例2016": [
        "https://www.gov.cn/zhengce/2016-11/02/content_5127507.htm",
    ],
}


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.gov.cn/",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read()
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def to_text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h1>|</h2>|</tr>", "\n", html)
    txt = re.sub(r"(?s)<[^>]+>", " ", html)
    txt = unescape(txt)
    txt = re.sub(r"[ \t\u3000]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    return txt.strip()


def main() -> int:
    for name, urls in CAND.items():
        p = OUT / (name + ".txt")
        if p.exists() and p.stat().st_size > 5000:
            print("skip", name, p.stat().st_size)
            continue
        done = False
        for url in urls:
            try:
                txt = to_text(fetch(url))
            except Exception as e:  # noqa: BLE001
                print("  x", name, type(e).__name__, url)
                continue
            if len(txt) < 2000:
                print("  -", name, len(txt), url)
                continue
            p.write_text(txt, encoding="utf-8")
            print("ok", name, len(txt), url)
            done = True
            break
        if not done:
            print("FAIL", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
