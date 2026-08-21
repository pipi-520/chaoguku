"""多源快讯抓取器：每个源独立容错，返回归一化 news item 列表。

归一化字段：id, ts, date, source, title, content, url, symbols
"""

import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

TZ = ZoneInfo("Asia/Shanghai")


def _parse_dt(v):
    """把多种时间格式解析为 tz-aware datetime，失败返回 None。"""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(int(v), tz=TZ)
        except (ValueError, OSError, OverflowError):
            return None
    s = str(v).strip()
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.isna(dt):
            return None
        dt = dt.to_pydatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except (ValueError, TypeError):
        return None


def _mk(dt, source, title, content, url=""):
    if dt is None:
        return None
    title = (title or "").strip()
    content = (content or "").strip()
    key = f"{source}|{title or content[:40]}|{dt.isoformat()}"
    return {
        "id": hashlib.md5(key.encode("utf-8")).hexdigest()[:16],
        "ts": dt.isoformat(),
        "date": dt.strftime("%Y-%m-%d"),
        "source": source,
        "title": title,
        "content": content,
        "url": url or "",
        "symbols": [],
    }


def _rows_to_items(df, source, title_col, content_col, time_col, url_col=None):
    items = []
    if df is None or df.empty:
        return items
    for _, r in df.iterrows():
        try:
            dt = _parse_dt(r.get(time_col))
            title = str(r.get(title_col) or "") if title_col else ""
            content = str(r.get(content_col) or "") if content_col else ""
            url = str(r.get(url_col) or "") if url_col else ""
            it = _mk(dt, source, title, content, url)
            if it:
                items.append(it)
        except Exception:  # noqa: BLE001
            continue
    return items


# ---- 财联社电报 ----
def fetch_cls():
    import akshare as ak
    df = ak.stock_info_global_cls()
    items = []
    if df is not None and not df.empty:
        for _, r in df.iterrows():
            dt = _parse_dt(f"{r.get('发布日期', '')} {r.get('发布时间', '')}")
            it = _mk(dt, "财联社", r.get("标题", ""), r.get("内容", ""), "")
            if it:
                items.append(it)
    return items


# ---- 东财全球资讯(7x24) ----
def fetch_em():
    import akshare as ak
    df = ak.stock_info_global_em()
    return _rows_to_items(df, "东财全球资讯", "标题", "摘要", "发布时间", "链接")


# ---- 新浪7x24 ----
def fetch_sina():
    import akshare as ak
    df = ak.stock_info_global_sina()
    items = []
    if df is not None and not df.empty:
        for _, r in df.iterrows():
            dt = _parse_dt(r.get("时间", ""))
            it = _mk(dt, "新浪7x24", r.get("内容", ""), r.get("内容", ""), "")
            if it:
                items.append(it)
    return items


# ---- 同花顺7x24 ----
def fetch_ths():
    import akshare as ak
    df = ak.stock_info_global_ths()
    return _rows_to_items(df, "同花顺7x24", "标题", "内容", "发布时间", "链接")


# ---- 富途牛牛快讯 ----
def fetch_futu():
    import akshare as ak
    df = ak.stock_info_global_futu()
    return _rows_to_items(df, "富途牛牛", "标题", "内容", "发布时间", "链接")


# ---- 华尔街见闻实时快讯 ----
def fetch_wallstcn():
    import requests
    url = "https://api-one.wallstcn.com/apiv1/content/lives"
    r = requests.get(url, params={"channel": "global-channel", "limit": "50"}, timeout=12)
    r.raise_for_status()
    items = []
    for it in r.json().get("data", {}).get("items", []):
        content = it.get("content_text") or it.get("content") or ""
        title = it.get("title") or ""
        dt = _parse_dt(it.get("display_time"))
        uri = it.get("uri") or ""
        url = f"https://wallstreetcn.com{uri}" if uri else ""
        obj = _mk(dt, "华尔街见闻", title, content, url)
        if obj:
            items.append(obj)
    return items


# ---- 金十数据快讯 ----
def fetch_jin10():
    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.jin10.com/",
        "x-app-id": "bVBF4FyRTn5NJF5n",
        "x-version": "1.0.0",
    }
    url = "https://flash-api.jin10.com/get_flash_list"
    r = requests.get(url, params={"max_time": ""}, headers=headers, timeout=12)
    r.raise_for_status()
    items = []
    for it in r.json().get("data", []):
        body = it.get("data", {})
        content = body.get("content") or ""
        dt = _parse_dt(body.get("time") or it.get("time"))
        obj = _mk(dt, "金十快讯", "", content, "")
        if obj:
            items.append(obj)
    return items


# ---- 政策公告（best-effort，国务院政策 RSS） ----
def fetch_policy():
    import requests
    import xml.etree.ElementTree as ET
    url = "https://www.gov.cn/zhengce/zuixin/rss.xml"
    r = requests.get(url, timeout=12)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    items = []
    for node in root.findall(".//item"):
        title = node.findtext("title") or ""
        desc = node.findtext("description") or ""
        link = node.findtext("link") or ""
        pub = node.findtext("pubDate") or ""
        dt = _parse_dt(pub)
        obj = _mk(dt, "政策公告", title, desc, link)
        if obj:
            items.append(obj)
    return items


SOURCES = [
    ("财联社", fetch_cls),
    ("东财全球资讯", fetch_em),
    ("新浪7x24", fetch_sina),
    ("同花顺7x24", fetch_ths),
    ("富途牛牛", fetch_futu),
    ("华尔街见闻", fetch_wallstcn),
    ("金十快讯", fetch_jin10),
    ("政策公告", fetch_policy),
]

# ---- 个股新闻（为每只 A股抓取并预打标签） ----
def fetch_symbol_news(symbols_cfg):
    import akshare as ak
    items = []
    for s in symbols_cfg:
        if s.get("market") != "cn":
            continue
        code = str(s.get("code") or "")
        if not code:
            continue
        try:
            df = ak.stock_news_em(symbol=code)
        except Exception:  # noqa: BLE001
            continue
        if df is None or df.empty:
            continue
        for _, r in df.iterrows():
            dt = _parse_dt(r.get("发布时间", ""))
            it = _mk(dt, "个股新闻", r.get("新闻标题", ""), r.get("新闻内容", ""),
                     r.get("新闻链接", ""))
            if it:
                it["symbols"] = [s["symbol"]]
                items.append(it)
    return items
