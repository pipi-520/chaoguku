"""新闻情绪打分 + 合成情绪序列生成。

数据来源优先级：
  1. 若存在 news/daily_sentiment.json（多源聚合器产出），直接使用其市场+个股情绪分；
  2. 否则回退到 akshare 单点抓取（个股新闻 + 东财全球资讯市场情绪）。
另生成确定性合成情绪序列用于历史回测演示。

用法（在项目根目录执行）：
    .venv/Scripts/python.exe scripts/sentiment_score.py
"""

import json
import pathlib
import sys

import numpy as np
import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
NEWS_DIR = ROOT / "news"

try:
    from news_aggregator.sentiment import CN_POS, CN_NEG, score_text
except ImportError:  # pragma: no cover - 独立运行时的最小回退
    CN_POS = ["利好", "增长", "上涨", "涨停", "突破", "超预期", "回购", "增持"]
    CN_NEG = ["利空", "下跌", "跌停", "亏损", "减持", "违规", "处罚", "立案"]

    def score_text(text):
        if not text:
            return 0.0
        t = str(text).lower()
        p = sum(t.count(w) for w in CN_POS)
        n = sum(t.count(w) for w in CN_NEG)
        return (p - n) / (p + n + 1) if p + n else 0.0


def load_config() -> dict:
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def df_from_dict(d: dict) -> pd.DataFrame:
    if not d:
        return pd.DataFrame(columns=["date", "score"])
    return pd.DataFrame({"date": list(d.keys()), "score": list(d.values())})


def load_aggregated_daily() -> dict | None:
    """读取聚合器产物，返回 {symbol: DataFrame(date,score), 'market': DataFrame} 或 None。"""
    p = NEWS_DIR / "daily_sentiment.json"
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    out = {"market": df_from_dict(data.get("market", {}))}
    for sym, dd in (data.get("symbols") or {}).items():
        out[sym] = df_from_dict(dd)
    return out


def news_to_daily(df, title_col, content_col, date_col) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "score"])
    rows = []
    for _, r in df.iterrows():
        d = pd.to_datetime(r[date_col], errors="coerce")
        if pd.isna(d):
            continue
        text = f"{r.get(title_col, '')} {r.get(content_col, '')}"
        rows.append({"date": d.strftime("%Y-%m-%d"), "s": score_text(text)})
    if not rows:
        return pd.DataFrame(columns=["date", "score"])
    daily = pd.DataFrame(rows).groupby("date")["s"].mean().reset_index()
    daily.columns = ["date", "score"]
    daily["score"] = daily["score"].clip(-1.0, 1.0)
    return daily


def fetch_market_daily() -> pd.DataFrame:
    import akshare as ak
    try:
        df = ak.stock_info_global_em()
    except Exception as e:  # noqa: BLE001
        print(f"  !! 市场资讯抓取失败: {e}")
        return pd.DataFrame(columns=["date", "score"])
    return news_to_daily(df, "标题", "摘要", "发布时间")


def fetch_symbol_daily(code: str) -> pd.DataFrame:
    import akshare as ak
    try:
        df = ak.stock_news_em(symbol=code)
    except Exception as e:  # noqa: BLE001
        print(f"  !! 个股新闻抓取失败: {e}")
        return pd.DataFrame(columns=["date", "score"])
    return news_to_daily(df, "新闻标题", "新闻内容", "发布时间")


def reindex_to_trading_days(daily: pd.DataFrame, symbol: str) -> pd.DataFrame:
    bars_path = DATA_DIR / f"bars_{symbol}.csv"
    if not bars_path.exists():
        return daily
    bars = pd.read_csv(bars_path, encoding="utf-8-sig")
    if "date" not in bars.columns or bars.empty:
        return daily
    days = pd.to_datetime(bars["date"]).dt.strftime("%Y-%m-%d")
    grid = pd.DataFrame({"date": days})
    if daily.empty:
        grid["score"] = 0.0
        return grid.drop_duplicates(subset=["date"]).reset_index(drop=True)
    merged = grid.merge(daily, on="date", how="left")
    merged["score"] = merged["score"].ffill().fillna(0.0)
    return merged.drop_duplicates(subset=["date"]).reset_index(drop=True)


def generate_synthetic(days: list, seed: int) -> pd.DataFrame:
    n = len(days)
    if n == 0:
        return pd.DataFrame(columns=["date", "score"])
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, 0.15, n)
    s = np.empty(n)
    s[0] = float(rng.normal(0.0, 0.2))
    for i in range(1, n):
        s[i] = 0.6 * s[i - 1] + e[i]
    s = np.clip(s, -1.0, 1.0)
    return pd.DataFrame({"date": days, "score": s})


def main() -> int:
    cfg = load_config()
    DATA_DIR.mkdir(exist_ok=True)

    agg = load_aggregated_daily()
    if agg is not None:
        print(f"[sentiment] 使用聚合器 {NEWS_DIR / 'daily_sentiment.json'}"
              f"（市场 {len(agg.get('market', []))} 天 / 个股 {len(agg) - 1} 只）")
        market_daily = None
    else:
        print("[sentiment] 未找到聚合结果，回退到 akshare 单点抓取")
        print("[sentiment] 抓取东财全球资讯（市场情绪）...")
        market_daily = fetch_market_daily()

    for item in cfg["symbols"]:
        sym = item["symbol"]
        print(f"[sentiment] {item['name']}({sym}) ...")

        if agg is not None:
            daily = agg.get(sym)
            if daily is None or daily.empty:
                daily = agg.get("market", pd.DataFrame(columns=["date", "score"]))
        else:
            per = fetch_symbol_daily(item["code"]) if item["market"] == "cn" else pd.DataFrame(columns=["date", "score"])
            if per.empty:
                daily = market_daily
            else:
                m = market_daily.rename(columns={"score": "score_m"})
                p = per.rename(columns={"score": "score_p"})
                merged = m.merge(p, on="date", how="outer")
                merged["score"] = merged["score_p"].fillna(merged["score_m"])
                daily = merged[["date", "score"]]

        final = reindex_to_trading_days(daily, sym)
        out = DATA_DIR / f"sentiment_{sym}.csv"
        final.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"  真实情绪 {len(final)} 天 -> {out.name}")

        seed = sum(ord(c) for c in sym)
        synth = generate_synthetic(final["date"].tolist(), seed)
        out2 = DATA_DIR / f"sentiment_synthetic_{sym}.csv"
        synth.to_csv(out2, index=False, encoding="utf-8-sig")
        print(f"  合成情绪 {len(synth)} 天 -> {out2.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
