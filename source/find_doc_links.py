# -*- coding: utf-8 -*-
"""在党内法规索引页里找出目标条例的链接。"""
import re
import urllib.request
from html import unescape

KEYS = ["纪律处分条例", "权利保障条例", "发展党员", "支部工作条例", "问责条例", "廉洁自律准则", "党内监督条例"]


def fetch(u: str) -> str:
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 Chrome/126", "Accept-Language": "zh-CN,zh;q=0.9"})
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")


for idx in ["https://www.12371.cn/special/dzfg/", "https://www.12371.cn/special/dnfg/", "https://www.12371.cn/djxf/djfg/"]:
    try:
        h = fetch(idx)
    except Exception as e:  # noqa: BLE001
        print("IDXFAIL", idx, type(e).__name__)
        continue
    links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', h, re.S)
    keep = [(u, re.sub("<[^>]+>", "", unescape(t)).strip()) for u, t in links]
    hit = [x for x in keep if any(k in x[1] for k in KEYS)]
    print(idx, len(h), "links", len(keep), "hits", len(hit))
    for u, t in hit[:30]:
        print("   ", t, "|", u)
