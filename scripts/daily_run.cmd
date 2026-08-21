@echo off
rem Daily pipeline: aggregate news -> sentiment -> paper trade -> backtest
rem Run from project root, or schedule via Windows Task Scheduler.
cd /d "%~dp0.."

echo [1/4] news aggregation + history accumulation
".venv\Scripts\python.exe" news_aggregator\run.py
if errorlevel 1 goto :fail

echo [2/4] generate sentiment scores
".venv\Scripts\python.exe" scripts\sentiment_score.py
if errorlevel 1 goto :fail

echo [3/4] paper trading
".venv\Scripts\python.exe" scripts\paper_trade.py
if errorlevel 1 goto :fail

echo [4/4] backtest
".venv\Scripts\python.exe" scripts\backtest.py
if errorlevel 1 goto :fail

echo.
echo Done. outputs: news/, data/sentiment_*.csv, results/backtest_report.md, paper/trades.csv
exit /b 0

:fail
echo Pipeline stopped (exit code %errorlevel%)
exit /b 1
