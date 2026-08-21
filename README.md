# chaogu —— 炒股开源项目推荐 + 多源新闻舆情聚合 + vnpy 量化策略

本仓库包含四部分：

1. **《GitHub炒股实用项目推荐.md》**：A股 + 美股的开源炒股项目精选清单。
2. **多源新闻/舆情聚合器（`news_aggregator/`）**：汇聚财联社、东财全球资讯、新浪7×24、
   同花顺7×24、富途牛牛、华尔街见闻、金十快讯等源，打情绪分、按股票打标签、生成日报，
   并可推送到企业微信。
3. **实时事件监测器（`news_aggregator/monitor.py`）**：秒级轮询快讯源，命中「事件关键词 →
   A股概念/行业板块 → 个股」即立即推送告警，供人工决策。
4. **vnpy 新闻情绪量化策略**：基于 VeighNa（vnpy）落地，接入聚合器情绪分，跑通历史回测。

> 仅用于学习研究，**不构成任何投资建议**。

## 一、新闻/舆情聚合器

### 本地运行

```powershell
.\.venv\Scripts\python.exe news_aggregator\run.py            # 抓取 + 生成日报
.\.venv\Scripts\python.exe news_aggregator\run.py --push     # 并推送到企业微信
```

产物：
- `news/raw/{date}.jsonl`        原始新闻（每条含来源/标题/内容/时间/命中股票）
- `news/daily_sentiment.json`    每日情绪分（市场 + 个股）
- `news/sentiment_history.json`  历史情绪分（按日期累积，可回测）
- `news/report/{date}.md`        日报

### GitHub Actions 定时 + 企业微信推送

1. 在 GitHub 新建仓库并把本目录 push 上去（当前本地仓库尚无 remote）。
2. 在仓库 Settings → Secrets and variables → Actions 添加 secret：`WECOM_WEBHOOK`
   （企业微信群机器人 webhook 地址）。
3. 推送后，工作流 `.github/workflows/news-aggregator.yml` 会在每个工作日 18:30（北京时间）
   自动抓取、生成日报、推送到企业微信，并把 `news/` 结果 commit 回仓库；也可手动
   Actions → Run workflow 触发。
4. 本地拉取最新聚合结果：`git pull`。

## 二、实时事件监测器（秒级告警）

```powershell
.\.venv\Scripts\python.exe news_aggregator\monitor.py               # 常驻轮询（默认 15s）
.\.venv\Scripts\python.exe news_aggregator\monitor.py --once        # 只跑一轮即退（测试/定时）
.\.venv\Scripts\python.exe news_aggregator\monitor.py --dry-run     # 只检测不推送
.\.venv\Scripts\python.exe news_aggregator\monitor.py --interval 10  # 自定义轮询秒数
.\.venv\Scripts\python.exe news_aggregator\monitor.py --no-boards    # 跳过板块缓存（更快/离线）
```

- 数据源：复用聚合器的财联社电报/东财7×24/新浪/同花顺/富途/华尔街见闻/金十快讯。
- 事件库：`news_aggregator/themes.yaml`（关键词 → 概念/行业板块），新增主题只改此文件。
- 推送：企业微信 + Server酱(微信) + Telegram + ntfy，开关与密钥见 `config.yaml` 的 `monitor` 段。
- 去重：`news/seen.json` 持久化，重启不重复告警；首次运行只建立基线、不告警历史旧闻。

### 云部署（systemd）

```bash
# 把本目录同步到大陆轻量服务器 /opt/chaogu 后：
sudo bash scripts/install_service.sh /opt/chaogu
systemctl status chaogu-monitor
```

或 Docker：

```bash
docker compose up -d --build
```

## 三、量化策略

```powershell
# 1. 安装依赖（Python 3.12）
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. 下载行情（联网）
.\.venv\Scripts\python.exe scripts\download_data.py

# 3. 生成新闻情绪分（优先用聚合器结果；无则回退 akshare 单点）
.\.venv\Scripts\python.exe scripts\sentiment_score.py

# 4. 回测
.\.venv\Scripts\python.exe scripts\backtest.py

# 5. 本地模拟盘（Paper Trading）
.\.venv\Scripts\python.exe scripts\paper_trade.py            # 用真实情绪分
.\.venv\Scripts\python.exe scripts\paper_trade.py --synthetic # 用合成情绪分演示
.\.venv\Scripts\python.exe scripts\paper_trade.py --reset    # 重置虚拟账户
```

回测结果见 `results/backtest_report.md`。

## 四、关键文件

| 文件 | 说明 |
|---|---|
| `config.yaml` | 标的、情绪阈值、回测参数、新闻源、监测器与推送配置（统一配置） |
| `news_aggregator/` | 多源聚合器 + 实时监测器（fetchers/run/monitor/boards/themes/push/sentiment/tagger） |
| `news_aggregator/themes.yaml` | 事件词 → 板块 主题库（数据驱动，可扩展） |
| `.github/workflows/news-aggregator.yml` | GitHub Actions 定时聚合 + 推送 |
| `deploy/chaogu-monitor.service` | systemd 服务单元（云上 24/7 监测） |
| `strategies/news_sentiment_strategy.py` | vnpy CTA 策略（新闻情绪驱动） |
| `scripts/` | 行情下载 / 情绪打分 / 回测 / 模拟盘 / 一键每日流程 / 云安装脚本 |
| `量化策略说明.md` | 完整运行与模拟盘接入文档 |

## 五、详细说明

见 [量化策略说明.md](量化策略说明.md)。
