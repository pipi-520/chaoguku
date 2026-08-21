"""新闻情绪驱动 CTA 策略（vnpy CtaTemplate）。

信号逻辑（只做多头，默认空仓）：
- 当日新闻情绪分 >= threshold  -> 开多（固定股数）
- 当日新闻情绪分 <= threshold_flat -> 平多
情绪分由 scripts/sentiment_score.py 预计算，按日期写入 CSV。
"""

import csv
import os

from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.object import BarData


def load_sentiment(path: str) -> dict:
    """读取 sentiment CSV（列: date, score），返回 {date(str): score(float)}。"""
    result: dict = {}
    if not path or not os.path.exists(path):
        return result
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = (row.get("date") or "").strip()
            try:
                result[d] = float(row.get("score") or 0.0)
            except (TypeError, ValueError):
                continue
    return result


class NewsSentimentStrategy(CtaTemplate):
    """"""

    author: str = "chaogu"

    threshold: float = 0.3
    threshold_flat: float = -0.3
    fixed_size: int = 100
    sentiment_path: str = ""

    parameters: list = ["threshold", "threshold_flat", "fixed_size", "sentiment_path"]
    variables: list = ["score"]

    def on_init(self) -> None:
        """策略初始化：载入情绪数据。"""
        self.sentiment: dict = load_sentiment(self.sentiment_path)
        self.score: float = 0.0
        self.write_log(f"载入情绪数据 {len(self.sentiment)} 天")

    def on_start(self) -> None:
        self.write_log("策略启动（新闻情绪驱动，只做多头）")

    def on_stop(self) -> None:
        self.write_log("策略停止")

    def on_bar(self, bar: BarData) -> None:
        """逐日 K 线回调。"""
        d: str = bar.datetime.strftime("%Y-%m-%d")
        self.score = float(self.sentiment.get(d, 0.0))

        # 开多
        if self.pos == 0 and self.score >= self.threshold:
            self.buy(bar.close_price, float(self.fixed_size))

        # 平多
        elif self.pos > 0 and self.score <= self.threshold_flat:
            self.sell(bar.close_price, abs(self.pos))
