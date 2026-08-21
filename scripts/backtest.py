"""回测脚本：用 vnpy CTA BacktestingEngine 对每个标的跑新闻情绪策略。

用法（在项目根目录执行）：
    .venv/Scripts/python.exe scripts/backtest.py
输出：results/backtest_report.md
"""

import pathlib
import sys
from datetime import datetime

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vnpy_ctastrategy.backtesting import BacktestingEngine  # noqa: E402
from vnpy.trader.constant import Interval  # noqa: E402

from strategies.news_sentiment_strategy import NewsSentimentStrategy  # noqa: E402

RESULTS_DIR = ROOT / "results"
DATA_DIR = ROOT / "data"


def fmt(v, digits: int = 2) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "-"
    return f"{f:,.{digits}f}"


def run_one(item: dict, cfg: dict) -> dict:
    """对单个标的回测，返回统计 dict。"""
    bt = cfg["backtest"]
    sent = cfg["sentiment"]
    start = datetime.strptime(bt["start_date"], "%Y%m%d")
    end = datetime.strptime(bt["end_date"], "%Y%m%d")

    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol=f"{item['symbol']}.{item['exchange']}",
        interval=Interval.DAILY,
        start=start,
        end=end,
        rate=float(bt["rate"]),
        slippage=float(bt["slippage"]),
        size=1,
        pricetick=float(bt["pricetick"]),
        capital=int(bt["capital"]),
    )

    use_synth = bool(bt.get("use_synthetic_sentiment", True))
    fname = f"sentiment_synthetic_{item['symbol']}.csv" if use_synth else f"sentiment_{item['symbol']}.csv"
    sentiment_path = DATA_DIR / fname
    engine.add_strategy(NewsSentimentStrategy, {
        "threshold": float(sent["threshold_long"]),
        "threshold_flat": float(sent["threshold_flat"]),
        "fixed_size": int(item["fixed_size"]),
        "sentiment_path": str(sentiment_path),
    })

    engine.load_data()
    n_bars = len(engine.history_data)
    engine.run_backtesting()
    df = engine.calculate_result()
    stats = engine.calculate_statistics(df, output=False)

    win_rate = None
    pd_ = stats.get("profit_days", 0)
    ld_ = stats.get("loss_days", 0)
    if pd_ + ld_ > 0:
        win_rate = pd_ / (pd_ + ld_) * 100

    return {
        "name": item["name"],
        "symbol": item["symbol"],
        "market": item["market"],
        "n_bars": n_bars,
        "stats": stats,
        "win_rate": win_rate,
    }


def main() -> int:
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    RESULTS_DIR.mkdir(exist_ok=True)

    rows = []
    for item in cfg["symbols"]:
        print(f"[backtest] {item['name']}({item['symbol']}) ...")
        try:
            r = run_one(item, cfg)
        except Exception as e:  # noqa: BLE001
            print(f"  !! 回测失败: {e}")
            r = {"name": item["name"], "symbol": item["symbol"], "market": item["market"],
                 "n_bars": 0, "stats": {}, "win_rate": None}
        rows.append(r)
        st = r["stats"]
        print(f"  bars={r['n_bars']} trades={st.get('total_trade_count', 0)} "
              f"ret={fmt(st.get('total_return'))}% sharpe={fmt(st.get('sharpe_ratio'))}")

    # 写报告
    lines = []
    lines.append("# 新闻情绪策略回测报告")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
    lines.append(f"> 初始资金：{int(cfg['backtest']['capital']):,}")
    lines.append(f"> 回测区间：{cfg['backtest']['start_date']} ~ {cfg['backtest']['end_date']}")
    lines.append(f"> 情绪阈值：开多 >= {cfg['sentiment']['threshold_long']}，平多 <= {cfg['sentiment']['threshold_flat']}")
    mode = "合成情绪（演示策略机制，非真实表现）" if bool(cfg["backtest"].get("use_synthetic_sentiment", True)) else "真实新闻情绪（仅覆盖最近数日）"
    lines.append(f"> 情绪来源：{mode}")
    lines.append("> 说明：只做多头、默认空仓；情绪分由 scripts/sentiment_score.py 预计算，缺失日沿用最近一次情绪（前向填充）。**本报告仅用于学习研究，不构成投资建议。**")
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 标的 | 市场 | K线数 | 总收益率 | 年化收益 | 夏普 | 最大回撤 | 胜率(盈利日) | 成交笔数 | 结束资金 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        st = r["stats"]
        lines.append(
            f"| {r['name']}({r['symbol']}) | {r['market']} | {r['n_bars']} | "
            f"{fmt(st.get('total_return'))}% | {fmt(st.get('annual_return'))}% | "
            f"{fmt(st.get('sharpe_ratio'))} | {fmt(st.get('max_ddpercent'))}% | "
            f"{fmt(r['win_rate']) if r['win_rate'] is not None else '-'}% | "
            f"{st.get('total_trade_count', 0)} | {fmt(st.get('end_balance'), 0)} |"
        )
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- 撮合逻辑：vnpy BAR 回测，当日信号于下一交易日开盘附近成交。")
    lines.append("- 胜率定义为「盈利交易日 / (盈利交易日 + 亏损交易日)」。")
    lines.append("- 合成情绪为确定性 AR(1) 随机序列，仅用于演示策略机制，不代表真实可盈利。")
    lines.append("- 真实情绪文件 data/sentiment_{symbol}.csv：A股取个股新闻 + 东财全球资讯市场情绪；美股因 yfinance 限流，用东财全球资讯市场情绪代理。")
    lines.append("")

    report = RESULTS_DIR / "backtest_report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"[backtest] 报告已写入 {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())




