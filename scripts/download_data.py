"""下载行情日线到 vnpy SQLite 库，并另存 CSV 供情绪/回测使用。

数据源：腾讯（A股 stock_zh_a_hist_tx）/ 新浪（美股 stock_us_daily），前复权。
用法（在项目根目录执行）：
    .venv/Scripts/python.exe scripts/download_data.py
"""

import pathlib
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

import akshare as ak
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy.trader.object import BarData

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TZ = ZoneInfo("Asia/Shanghai")

EXCHANGE_PREFIX = {"SSE": "sh", "SZSE": "sz", "BSE": "bj"}


def load_config() -> dict:
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def retry(fn, *args, retries: int = 4, delay: float = 2.0, **kwargs):
    last = None
    for i in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(delay * (i + 1))
    raise last


def fetch_bars(item: dict, start: str, end: str) -> pd.DataFrame:
    """拉取日线并统一为 date/open/high/low/close/volume/turnover。"""
    if item["market"] == "cn":
        ak_symbol = f"{EXCHANGE_PREFIX[item['exchange']]}{item['code']}"
        df = retry(
            ak.stock_zh_a_hist_tx,
            symbol=ak_symbol, start_date=start, end_date=end, adjust="qfq",
        )
        df = df.drop(columns=["turnover"], errors="ignore")  # 丢弃换手率列
        df = df.rename(columns={"amount": "turnover"})        # amount=成交额
        cols = ["date", "open", "high", "low", "close", "volume", "turnover"]
    else:
        df = retry(ak.stock_us_daily, symbol=item["symbol"], adjust="qfq")
        df["date"] = pd.to_datetime(df["date"])
        df = df[(df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))]
        df["turnover"] = 0.0
        cols = ["date", "open", "high", "low", "close", "volume", "turnover"]

    if df is None or df.empty:
        return pd.DataFrame()

    df = df[[c for c in cols if c in df.columns]].copy()
    for col in ("open", "high", "low", "close", "volume", "turnover"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def to_bar(row: dict, item: dict) -> BarData:
    dt = datetime.strptime(row["date"], "%Y-%m-%d").replace(tzinfo=TZ)
    return BarData(
        gateway_name="AK",
        symbol=item["symbol"],
        exchange=Exchange(item["exchange"]),
        datetime=dt,
        interval=Interval.DAILY,
        volume=float(row.get("volume") or 0),
        turnover=float(row.get("turnover") or 0),
        open_interest=0.0,
        open_price=float(row["open"]),
        high_price=float(row["high"]),
        low_price=float(row["low"]),
        close_price=float(row["close"]),
    )


def main() -> int:
    cfg = load_config()
    start = cfg["data"]["start_date"]
    end = cfg["data"]["end_date"]
    DATA_DIR.mkdir(exist_ok=True)

    database = get_database()

    for item in cfg["symbols"]:
        print(f"[download] {item['name']}({item['symbol']}) ...")
        try:
            df = fetch_bars(item, start, end)
        except Exception as e:  # noqa: BLE001
            print(f"  !! 拉取失败: {e}")
            continue

        if df.empty:
            print("  !! 无数据，跳过")
            continue

        csv_path = DATA_DIR / f"bars_{item['symbol']}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        bars = [to_bar(r, item) for r in df.to_dict("records")]
        database.save_bar_data(bars)
        print(f"  OK {len(bars)} 根K线 -> {csv_path.name} 与 vnpy 数据库")

    return 0


if __name__ == "__main__":
    sys.exit(main())

