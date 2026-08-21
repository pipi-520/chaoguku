"""新闻情绪打分 + 合成情绪序列生成。

数据源优先级（就高到低，同日后者覆盖前者）：
  个股情绪：history[symbols] -> daily_sentiment[symbols] -> akshare 个股新闻(近100条, 多日)
  市场情绪：history[market]    -> daily_sentiment[market]  -> akshare 东财全球资讯
最终个股情绪 = 市场情绪打底 + 个股情绪覆盖。
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
    from news_aggregator.sentiment import CN_POS, CN_NEG, score_text, configure_backend
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

    def configure_backend(cfg):  # pragma: no cover
        pass


def load_config() -> dict:
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def df_from_dict(d: dict) -> pd.DataFrame:
    if not d:
        return pd.DataFrame(columns=["date", "score"])
    return pd.DataFrame({"date": list(d.keys()), "score": list(d.values())})


def load_history() -> dict | None:
    p = NEWS_DIR / "sentiment_history.json"
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def load_single_daily() -> dict | None:
    p = NEWS_DIR / "daily_sentiment.json"
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_score_dfs(*dfs) -> pd.DataFrame:
    """按日期合并多个 date/score DataFrame，同日后者覆盖前者。"""
    out = None
    for df in dfs:
        if df is None or df.empty:
            continue
        d = df[["date", "score"]].copy()
        d["score"] = pd.to_numeric(d["score"], errors="coerce")
        if out is None:
            out = d
        else:
            merged = out.merge(d, on="date", how="outer", suffixes=("", "_y"))
            merged["score"] = merged["score_y"].fillna(merged["score"])
            out = merged[["date", "score"]]
    if out is None:
        return pd.DataFrame(columns=["date", "score"])
    return out.dropna(subset=["score"]).reset_index(drop=True)


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


def build_market_daily(history, single) -> pd.DataFrame:
    frames = []
    if history:
        frames.append(df_from_dict(history.get("market", {})))
    if single:
        frames.append(df_from_dict(single.get("market", {})))
    market = merge_score_dfs(*frames)
    if market.empty:
        print("[sentiment] 无历史市场情绪，回退到东财全球资讯实时抓取 ...")
        market = fetch_market_daily()
    return market


def main() -> int:
    cfg = load_config()
    configure_backend(cfg)
    DATA_DIR.mkdir(exist_ok=True)

    history = load_history()
    single = load_single_daily()
    if history is not None:
        print(f"[sentiment] 使用历史情绪库（市场 {len(history.get('market', {}))} 天"
              f" / 个股 {len(history.get('symbols', {}))} 只）")
    elif single is not None:
        print("[sentiment] 使用当日快照 daily_sentiment.json")
    else:
        print("[sentiment] 未找到聚合结果，回退到 akshare 单点抓取")

    market_daily = build_market_daily(history, single)

    for item in cfg["symbols"]:
        sym = item["symbol"]
        print(f"[sentiment] {item['name']}({sym}) ...")

        # 个股情绪来源（后者覆盖前者）
        sym_frames = []
        if history:
            sym_frames.append(df_from_dict((history.get("symbols") or {}).get(sym, {})))
        if single:
            sym_frames.append(df_from_dict((single.get("symbols") or {}).get(sym, {})))
        if item["market"] == "cn":
            per = fetch_symbol_daily(item["code"])
            if not per.empty:
                sym_frames.append(per)
                print(f"  个股新闻直抓 {len(per)} 天")
        sym_daily = merge_score_dfs(*sym_frames)

        # 个股覆盖市场，缺失日沿用最近一次
        daily = merge_score_dfs(market_daily, sym_daily)
        final = reindex_to_trading_days(daily, sym)
        out = DATA_DIR / f"sentiment_{sym}.csv"
        final.to_csv(out, index=False, encoding="utf-8-sig")
        n_pos = int((final["score"] > 0).sum())
        n_neg = int((final["score"] < 0).sum())
        n_nz = n_pos + n_neg
        print(f"  真实情绪 {len(final)} 天（非零 {n_nz}：正 {n_pos} / 负 {n_neg}）-> {out.name}")

        seed = sum(ord(c) for c in sym)
        synth = generate_synthetic(final["date"].tolist(), seed)
        out2 = DATA_DIR / f"sentiment_synthetic_{sym}.csv"
        synth.to_csv(out2, index=False, encoding="utf-8-sig")
        print(f"  合成情绪 {len(synth)} 天 -> {out2.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

