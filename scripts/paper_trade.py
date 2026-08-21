"""本地模拟盘（Paper Trading）引擎。

- 用真实情绪分（data/sentiment_{symbol}.csv，来自多源聚合器）驱动新闻情绪策略。
- 撮合规则：T 日收盘用当日情绪生成信号，T+1 开盘成交（与 vnpy BAR 回测一致）。
- 持久化虚拟账户：paper/paper_state.json + paper/trades.csv；重复运行只会处理新增交易日。

用法（在项目根目录执行）：
    .venv/Scripts/python.exe scripts/paper_trade.py            # 用真实情绪分
    .venv/Scripts/python.exe scripts/paper_trade.py --synthetic  # 用合成情绪分演示
    .venv/Scripts/python.exe scripts/paper_trade.py --reset    # 重置虚拟账户
"""

import argparse
import json
import pathlib
import sys
from datetime import datetime

import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PAPER_DIR = ROOT / "paper"
STATE_PATH = PAPER_DIR / "paper_state.json"
TRADES_PATH = PAPER_DIR / "trades.csv"


def load_config() -> dict:
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state(capital: float) -> dict:
    if STATE_PATH.exists():
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"cash": capital, "positions": {}, "last_processed": {}, "trades": []}


def save_state(state: dict) -> None:
    PAPER_DIR.mkdir(exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_series(symbol: str, synthetic: bool) -> tuple[pd.DataFrame, dict]:
    """返回 (bars DataFrame[date,open,close], sentiment dict[date->score])。"""
    bars = pd.read_csv(DATA_DIR / f"bars_{symbol}.csv", encoding="utf-8-sig")
    bars["date"] = pd.to_datetime(bars["date"]).dt.strftime("%Y-%m-%d")
    bars = bars.sort_values("date").reset_index(drop=True)
    fname = f"sentiment_synthetic_{symbol}.csv" if synthetic else f"sentiment_{symbol}.csv"
    sent_df = pd.read_csv(DATA_DIR / fname, encoding="utf-8-sig")
    sent_df["date"] = pd.to_datetime(sent_df["date"]).dt.strftime("%Y-%m-%d")
    sent = dict(zip(sent_df["date"], sent_df["score"]))
    return bars, sent


def process_symbol(sym: str, item: dict, th: float, tf: float, state: dict, synthetic: bool):
    bars, sent = load_series(sym, synthetic)
    if bars.empty:
        return
    last = state["last_processed"].get(sym)
    qty = state["positions"].get(sym, {}).get("qty", 0.0)
    avg_cost = state["positions"].get(sym, {}).get("avg_cost", 0.0)

    # 起点：上次已处理日之后；首次则从第一条开始（信号需要前一日，因此 i 从 1 开始）
    start_idx = 0
    if last is not None:
        idx = bars.index[bars["date"] == last].tolist()
        if idx:
            start_idx = idx[0]

    for i in range(max(start_idx, 0), len(bars)):
        if i == 0:
            continue  # 第一条仅作为首个信号日
        sig_date = bars.loc[i - 1, "date"]
        trade_date = bars.loc[i, "date"]
        open_price = float(bars.loc[i, "open"])
        score = float(sent.get(sig_date, 0.0))
        size = int(item.get("fixed_size", 100))

        if qty == 0 and score >= th:
            cost = open_price * size
            if cost <= state["cash"]:
                state["cash"] -= cost
                avg_cost = open_price
                qty = size
                state["trades"].append({
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "signal_date": sig_date,
                    "date": trade_date,
                    "symbol": sym,
                    "side": "BUY",
                    "qty": size,
                    "price": round(open_price, 4),
                    "cash_after": round(state["cash"], 2),
                })
        elif qty > 0 and score <= tf:
            state["cash"] += open_price * qty
            state["trades"].append({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "signal_date": sig_date,
                "date": trade_date,
                "symbol": sym,
                "side": "SELL",
                "qty": qty,
                "price": round(open_price, 4),
                "cash_after": round(state["cash"], 2),
            })
            qty = 0
            avg_cost = 0.0

        state["last_processed"][sym] = trade_date

    state["positions"][sym] = {"qty": qty, "avg_cost": round(avg_cost, 4), "last_close": float(bars["close"].iloc[-1])}


def write_trades(state: dict) -> None:
    if state["trades"]:
        df = pd.DataFrame(state["trades"])
        PAPER_DIR.mkdir(exist_ok=True)
        df.to_csv(TRADES_PATH, index=False, encoding="utf-8-sig")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="用合成情绪分演示")
    ap.add_argument("--reset", action="store_true", help="重置虚拟账户")
    args = ap.parse_args()

    cfg = load_config()
    sent_cfg = cfg["sentiment"]
    capital = float(cfg["backtest"]["capital"])
    th = float(sent_cfg["threshold_long"])
    tf = float(sent_cfg["threshold_flat"])

    if args.reset and STATE_PATH.exists():
        STATE_PATH.unlink()
        print("[paper] 已重置虚拟账户")

    state = load_state(capital)
    for item in cfg["symbols"]:
        sym = item["symbol"]
        print(f"[paper] {item['name']}({sym}) ...")
        try:
            process_symbol(sym, item, th, tf, state, args.synthetic)
        except Exception as e:  # noqa: BLE001
            print(f"  !! 处理失败: {e}")

    save_state(state)
    write_trades(state)

    # 汇总
    equity = state["cash"]
    print("\n==== 虚拟账户概览 ====")
    print(f"现金：{state['cash']:,.2f}")
    print("持仓：")
    for sym, pos in state["positions"].items():
        val = pos.get("qty", 0) * pos.get("last_close", 0)
        equity += val
        print(f"  {sym}: {pos.get('qty', 0)} 股 @ 成本 {pos.get('avg_cost', 0):.4f}"
              f" / 最新价 {pos.get('last_close', 0):.4f} / 市值 {val:,.2f}")
    print(f"总资产（现金+持仓市值）：{equity:,.2f}")
    print(f"累计成交：{len(state['trades'])} 笔")
    print("（撮合规则：T 日信号，T+1 开盘成交；仅作模拟，不构成投资建议）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
