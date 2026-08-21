# GitHub 炒股实用项目推荐（A股 + 美股）

> 调研基准日：2026-08-21。Star 数为参考值，会随时间波动。
> 本文仅做工具推荐与介绍，**不构成任何投资建议**。
> 同源/近似 fork 只推荐 canonical（原始）仓库，并在条目中注明。

## 一页速览 · Top 5

| 排名 | 项目 | 一句话定位 | 最适合谁 |
|---|---|---|---|
| 1 | **TrendRadar**（`lizouzt/TrendRadar`） | 35 平台热点聚合 + 关键词筛选 + AI 分析 + 多端推送 | 想第一时间收 A股/财经资讯、又不想自己写爬虫的人 |
| 2 | **vnpy / VeighNa**（`vnpy/vnpy`） | A股量化事实标准：回测 + 本地模拟盘 + 券商实盘 | 想跑量化策略、回测、模拟盘（本项目落地平台） |
| 3 | **AKShare**（`akfamily/akshare`） | 免费 A股/港股/美股数据与新闻接口，免注册 | 需要免费行情与新闻数据做分析的人 |
| 4 | **TradingAgents**（`TauricResearch/TradingAgents`）+ A股 fork | AI 多智能体投研，自动出中文个股研究报告 | 想让 AI 解读新闻与财报、给决策参考的人 |
| 5 | **QuickFinews**（`Howe813/QuickFinews`） | 财联社/东财等财经新闻实时推送到 Telegram | 想要财经快讯主动推送到手机的人 |

---

## 分类① 新闻舆情汇聚（重点）

### 1. TrendRadar — 多平台热点聚合 + AI 分析 + 多端推送
- 仓库：https://github.com/lizouzt/TrendRadar （另有 `teddyguo94/TrendRadar-0124`、`Rui-R/TrendRadar_new` 等同源版本，推荐以 `lizouzt/TrendRadar` 为主）
- 市场：A股/泛财经（华尔街见闻、财联社、抖音、知乎、B站等 35 个平台）
- 功能：关键词组合筛选（如「A股 + 涨停」）、增量监控、AI 对话分析（趋势/情感/相似检索）、支持企业微信/个人微信/飞书/钉钉/Telegram/邮件/ntfy/bark/slack 推送
- 部署：Docker 一键部署，约 30 秒起服务，无需编程
- Star 参考：数千级（社区项目，以实际为准）
- 难度：★☆☆☆☆　推荐：★★★★★

### 2. QuickFinews — 财经新闻实时推送机器人
- 仓库：https://github.com/Howe813/QuickFinews
- 市场：A股 + 美股（财联社、东方财富、TuShare 新闻、Finnhub）
- 功能：集成 TuShare 新闻接口 + Finnhub API + Telegram 机器人，有新闻立即推送
- 部署：Python 应用，配置 Token 后运行
- Star 参考：数百级　难度：★★☆☆☆　推荐：★★★★☆

### 3. cailianpress-unified — 财联社统一数据接口
- 仓库：https://github.com/caimao9539/cailianpress-unified
- 市场：A股（财联社电报/加红/热度/文章）
- 功能：统一「电报、加红、热度、文章详情」查询接口，可审计的数据访问入口
- 部署：Python，作为数据源接入自研工具
- Star 参考：数百级　难度：★★☆☆☆　推荐：★★★★☆

### 4. jiuyan-crawler — 韭研公社每日舆情日报
- 仓库：https://github.com/Areak777/jiuyan-crawler
- 市场：A股 + 美股（韭研公社文章）
- 功能：自动抓取韭研公社文章，生成每日舆情日报；可 GitHub Actions 定时运行
- 部署：GitHub Actions 或本地 Python
- Star 参考：数百级　难度：★★☆☆☆　推荐：★★★☆☆

### 5. stock-news-scraper — 美股新闻抓取管道
- 仓库：https://github.com/AlexBoyev/stock-news-scraper
- 市场：美股
- 功能：Docker 化 Python 新闻抓取管道，实时财经头条存入 PostgreSQL 便于后续分析
- 部署：Docker Compose
- Star 参考：数百级　难度：★★☆☆☆　推荐：★★★☆☆

### 6. RSSHub — 用 RSS 订阅财经快讯
- 仓库：https://github.com/DIYgod/RSSHub
- 市场：A股 + 美股（财联社、东财 7×24、华尔街见闻等路由）
- 功能：把任意网页/快讯源转成 RSS，配合任意 RSS 客户端或推送工具
- 部署：Docker 或公开实例
- Star 参考：约 30k+　难度：★★☆☆☆　推荐：★★★★☆

### 7. daily_stock_analysis / stock9300 — LLM 驱动的智能分析器（新闻 + 行情 + 推送）
- 仓库：https://github.com/hasfhy/stock9300 （另见 `dansonc/daily_stock_analysis_github` 等同源版本，推荐以 `hasfhy/stock9300` 为主，覆盖 A/H/美股）
- 市场：A股 + 港股 + 美股
- 功能：多数据源行情 + 实时新闻 + 技术面/筹码/舆情 + Gemini 决策仪表盘 + 企业微信/飞书/Telegram/邮件多渠道推送，可零成本定时运行
- 部署：Python + 定时任务
- Star 参考：数百级　难度：★★★☆☆　推荐：★★★★☆

### 8. ashare-news-fetcher — A股新闻/政策/情绪统一抓取
- 仓库：见「ashare-news-fetcher」技能类仓库（华尔街见闻、金十、新浪 7×24、东财快讯、证监会/央行/上交所/财政部公告、东方财富股吧）
- 市场：A股
- 功能：抓取新闻、政策、情绪，输出结构化 JSON 或 Markdown
- 部署：Python
- Star 参考：数百级　难度：★★☆☆☆　推荐：★★★☆☆

---

## 分类② 行情与数据源

| 项目 | 链接 | 市场 | 定位 | Star 参考 | 难度 |
|---|---|---|---|---|---|
| AKShare | https://github.com/akfamily/akshare | A股/港股/美股/期货 | 免费金融数据接口，含行情/资金流/龙虎榜/新闻，免注册 | 约 19k | ★★☆☆☆ |
| Tushare | https://github.com/waditu/tushare | A股 | 金融数据 Python 工具包，接口稳定需积分 | 约 15k | ★★☆☆☆ |
| yfinance | https://github.com/ranaroussi/yfinance | 美股 | Yahoo Finance 免费数据 | 约 22k | ★☆☆☆☆ |
| OpenBB | https://github.com/OpenBB-finance/OpenBB | 全球 | 金融数据平台 + AI，一体化研究终端 | 约 64k | ★★★☆☆ |
| mootdx | https://github.com/mootdx/mootdx | A股 | 通达信行情数据接口 | 数千级 | ★★☆☆☆ |

---

## 分类③ AI 智能投研

| 项目 | 链接 | 市场 | 定位 | Star 参考 |
|---|---|---|---|---|
| TradingAgents | https://github.com/TauricResearch/TradingAgents | 美股为主 | 多智能体 AI 交易团队（多空辩论 + 风控） | 约 71k |
| TradingAgents-astock | https://github.com/simonlin1212/TradingAgents-astock | A股 | TradingAgents 的 A股深度特化 fork，中文报告 | 数千级 |
| Qlib | https://github.com/microsoft/qlib | A股/美股 | 微软 AI 量化研究平台（因子挖掘/回测/组合） | 约 39k |

---

## 分类④ 量化交易与回测

| 项目 | 链接 | 市场 | 定位 | Star 参考 |
|---|---|---|---|---|
| vnpy / VeighNa | https://github.com/vnpy/vnpy | A股/美股/期货 | 国内量化交易事实标准：回测 + 模拟盘 + 实盘 | 约 41k |
| backtrader | https://github.com/mementum/backtrader | 美股/全球 | 经典回测框架，实盘需第三方网关 | 约 20k |
| Backtesting.py | https://github.com/kernc/backtesting.py | 全球 | 轻量单文件回测框架 | 约 8k |
| easytrader | https://github.com/shidenggui/easytrader | A股 | 券商客户端自动下单（同花顺/佣金宝等） | 约 9k |
| zvt | https://github.com/zvtvz/zvt | A股 | 统一行情/财务/数据 + 选股框架 | 约 4k |

---

## 分类⑤ 资源索引与技能

| 项目 | 链接 | 定位 |
|---|---|---|
| awesome-quant | https://github.com/thuquant/awesome-quant | 中国 Quant 资源大全（数据/框架/论文） |
| A-Stock-Skills | https://github.com/ZICXR/A-Stock-Skills | 29 个 A股分析 Skills（akshare+tushare+东财） |
| a-stock-data | https://github.com/simonlin1212/a-stock-data | A股数据/新闻采集 Skill |

---

## 选型建议
- 只想**收资讯/提醒**：TrendRadar 或 QuickFinews（门槛最低）。
- 想**做研究分析**：AKShare 拉数据 + TradingAgents-astock 出报告。
- 想**跑量化策略/回测/模拟盘**：vnpy（本项目已落地，见《量化策略说明.md》）。
- 数据底座统一用 **AKShare**（免费、A股美股都覆盖、自带新闻接口）。
