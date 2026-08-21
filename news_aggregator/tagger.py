"""按股票代码/名称给新闻打标签。"""

import re


def build_matchers(symbols_cfg):
    """返回 [(symbol, 匹配器列表)]，每个匹配器是 (keyword, is_ticker) 。"""
    matchers = []
    for s in symbols_cfg:
        keys = []
        code = str(s.get("code") or "")
        name = str(s.get("name") or "")
        ticker = str(s.get("symbol") or "")
        if s.get("market") == "cn":
            keys.append((code, False))
            if name:
                keys.append((name, False))
        else:
            keys.append((ticker, True))
        matchers.append((s.get("symbol"), keys))
    return matchers


def tag(items, symbols_cfg):
    """为每条新闻填充 symbols 字段（命中的股票 symbol 列表）。"""
    matchers = build_matchers(symbols_cfg)
    for it in items:
        text = f"{it.get('title', '')} {it.get('content', '')}"
        hit = []
        for sym, keys in matchers:
            matched = False
            for kw, is_ticker in keys:
                if not kw:
                    continue
                if is_ticker:
                    if re.search(r"\b" + re.escape(kw) + r"\b", text, re.I):
                        matched = True
                        break
                else:
                    if kw in text:
                        matched = True
                        break
            if matched:
                hit.append(sym)
        it["symbols"] = hit
    return items
