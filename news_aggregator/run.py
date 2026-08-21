"""多源新闻/舆情聚合器主入口。

用法（在项目根目录执行）：
    .venv/Scripts/python.exe news_aggregator/run.py [--date YYYYMMDD] [--push]

输出：
    news/raw/{date}.jsonl            原始新闻（每行一条 JSON）
    news/daily_sentiment.json        每日情绪分（市场 + 个股）
    news/report/{date}.md            日报
"""

import argparse
import json
import pathlib
import sys
from collections import defaultdict
from datetime import date, datetime

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from news_aggregator.fetchers import SOURCES, fetch_symbol_news  # noqa: E402
from news_aggregator.sentiment import score_text  # noqa: E402
from news_aggregator.tagger import tag  # noqa: E402
from news_aggregator.push import send_wecom_markdown, get_webhook  # noqa: E402

NEWS_DIR = ROOT / "news"


def load_config() -> dict:
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_all(enabled=None):
    """逐源抓取，单源失败不中断。返回 (items, stats)。"""
    items = []
    stats = {}
    for name, fn in SOURCES:
        if enabled and name not in enabled:
            continue
        try:
            got = fn() or []
            items.extend(got)
            stats[name] = len(got)
            print(f"[fetch] {name}: {len(got)} 条")
        except Exception as e:  # noqa: BLE001
            stats[name] = -1
            print(f"[fetch] {name}: 失败 ({type(e).__name__})")
    return items, stats


def dedupe(items):
    seen = set()
    out = []
    for it in items:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        out.append(it)
    return out


def compute_daily(items):
    market = defaultdict(list)
    per_sym = defaultdict(lambda: defaultdict(list))
    for it in items:
        d = it["date"]
        sc = score_text(f"{it.get('title', '')} {it.get('content', '')}")
        market[d].append(sc)
        for s in it.get("symbols", []):
            per_sym[s][d].append(sc)
    market_out = {d: round(sum(v) / len(v), 4) for d, v in market.items()}
    sym_out = {
        s: {d: round(sum(v) / len(v), 4) for d, v in dd.items()}
        for s, dd in per_sym.items()
    }
    return market_out, sym_out


def build_report(day: str, items, stats, market, sym_out) -> str:
    lines = []
    lines.append(f"# 财经新闻舆情日报 {day}")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
    lines.append("> 数据来源：财联社 / 东财全球资讯 / 新浪7x24 / 同花顺7x24 / 富途牛牛 / 华尔街见闻 / 金十快讯 / 政策公告")
    lines.append("")
    lines.append("## 数据源统计")
    lines.append("")
    lines.append("| 来源 | 条数 |")
    lines.append("|---|---|")
    for name, n in stats.items():
        lines.append(f"| {name} | {n if n >= 0 else '失败'} |")
    lines.append("")
    lines.append(f"**去重后总计：{len(items)} 条**")
    lines.append("")

    # 市场情绪
    lines.append("## 市场情绪（最近）")
    lines.append("")
    if market:
        lines.append("| 日期 | 情绪分 |")
        lines.append("|---|---|")
        for d in sorted(market, reverse=True)[:5]:
            lines.append(f"| {d} | {market[d]:+.3f} |")
    else:
        lines.append("（无数据）")
    lines.append("")

    # 个股情绪
    if sym_out:
        lines.append("## 个股情绪（最新）")
        lines.append("")
        lines.append("| 股票 | 最新情绪分 |")
        lines.append("|---|---|")
        for s, dd in sorted(sym_out.items()):
            latest = sorted(dd)[-1] if dd else "-"
            lines.append(f"| {s} | {dd[latest]:+.3f} ({latest}) |")
        lines.append("")

    # 热门新闻
    scored = []
    for it in items:
        sc = score_text(f"{it.get('title', '')} {it.get('content', '')}")
        scored.append((abs(sc), sc, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    lines.append("## 情绪最强新闻 Top 15")
    lines.append("")
    for _, sc, it in scored[:15]:
        text = (it.get("title") or it.get("content") or "")[:80]
        lines.append(f"- [{it.get('source')}] ({sc:+.2f}) {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().strftime("%Y%m%d"))
    ap.add_argument("--push", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    enabled = (cfg.get("news") or {}).get("enabled_sources") or None

    items, stats = fetch_all(enabled)

    # 个股新闻（为每只 A股抓取并预打标签）
    try:
        sym_items = fetch_symbol_news(cfg["symbols"])
        stats["个股新闻"] = len(sym_items)
        items.extend(sym_items)
        print(f"[fetch] 个股新闻: {len(sym_items)} 条")
    except Exception as e:  # noqa: BLE001
        stats["个股新闻"] = -1
        print(f"[fetch] 个股新闻: 失败 ({type(e).__name__})")

    items = dedupe(items)
    items = tag(items, cfg["symbols"])
    print(f"[agg] 去重后 {len(items)} 条")

    NEWS_DIR.mkdir(exist_ok=True)
    raw_dir = NEWS_DIR / "raw"
    report_dir = NEWS_DIR / "report"
    raw_dir.mkdir(exist_ok=True)
    report_dir.mkdir(exist_ok=True)

    raw_path = raw_dir / f"{args.date}.jsonl"
    with open(raw_path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    market, sym_out = compute_daily(items)
    daily = {
        "generated_at": datetime.now().isoformat(),
        "date": args.date,
        "sources": {k: v for k, v in stats.items()},
        "market": market,
        "symbols": sym_out,
    }
    with open(NEWS_DIR / "daily_sentiment.json", "w", encoding="utf-8") as f:
        json.dump(daily, f, ensure_ascii=False, indent=2)

    md = build_report(args.date, items, stats, market, sym_out)
    report_path = report_dir / f"{args.date}.md"
    report_path.write_text(md, encoding="utf-8")
    print(f"[agg] raw -> {raw_path}")
    print(f"[agg] report -> {report_path}")
    print(f"[agg] daily_sentiment -> {NEWS_DIR / 'daily_sentiment.json'}")

    if args.push:
        send_wecom_markdown(get_webhook(), md)

    return 0


if __name__ == "__main__":
    sys.exit(main())

