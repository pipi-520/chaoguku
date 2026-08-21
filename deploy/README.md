# 云端部署指南

> 本地（Windows）跑的 `monitor.py` / `run.py` 会在电脑关机后停止。
> 本项目的「日报」已由 GitHub Actions 免费托管；真正需要 24/7 常驻的是「秒级监测器 monitor.py」。

## 一、谁跑在哪里（结论）

| 任务 | 频率 | 免费云端？ | 说明 |
|---|---|---|---|
| `run.py` 聚合 + 日报 + 推送 | 每工作日 18:30 | ✅ GitHub Actions | 已配好，不需要自己电脑 |
| `monitor.py` 实时事件监测 | 15 秒轮询、24/7 | ❌ 需常驻进程 | 需要一台云服务器（或一直开机的设备） |

## 二、方案对比

| 方案 | 成本 | 适合 | 注意 |
|---|---|---|---|
| GitHub Actions（已有） | 免费 | 日报 | 最快 5 分钟一次，做不到 15 秒级 |
| 云服务器 + systemd（已有脚本） | 约 ¥50+/月 | 实时监测，最稳 | 推荐 |
| Docker（已有） | 同上 | 环境隔离 | 与 systemd 二选一 |
| Oracle Cloud 永久免费 VPS | 免费 | 海外源 | 注册有门槛，海外线路 |

## 三、地域选择（重要：英文源会被墙）

- **大陆服务器**（腾讯云/阿里云轻量）：中文源（财联社/东财/新浪/金十/华尔街见闻）秒级且稳定，Server酱/企业微信直连快；但 **Google News RSS、白宫、Truth Social、SEC EDGAR、FRED、联邦储备官网会被墙**，英文一手源基本抓不到（静默失败返回空）。
- **香港/海外服务器**（腾讯云香港、阿里云香港、Vultr/DO）：英文源可用；中文源一般也能用，但个别 akshare 接口可能变慢或被限流。
- **推荐**：单机先上 **香港轻量**（兼顾中英）；若对中文源实时性要求极高，再拆成「大陆跑中文 + 香港跑英文」两台。

## 四、方案B：云服务器 + systemd（推荐）

1. 购买一台轻量应用服务器，选 **Ubuntu 22.04**（地域按上面选香港）。
2. 登录服务器，把代码放上去：
   ```bash
   sudo mkdir -p /opt/chaogu
   cd /opt
   # 方式一：git clone（本仓库已 push 到 GitHub 后）
   sudo git clone https://github.com/<你的仓库> /opt/chaogu
   # 方式二：本机 scp 上传
   # scp -r . user@服务器IP:/opt/chaogu
   ```
3. 配置密钥（编辑 `/opt/chaogu/.env`）：
   ```bash
   SERVERCHAN_SENDKEY=你的Server酱key
   # WECOM_WEBHOOK=你的企业微信群机器人
   # FRED_API_KEY=xxx        # 可选
   # QUIVER_TOKEN=xxx        # 可选
   ```
   或在 `config.yaml` 的 `primary:` 段填，二选一即可。
4. 一键安装为系统服务（自动建 venv、装依赖、设为开机自启 + 崩溃重启）：
   ```bash
   sudo bash /opt/chaogu/scripts/install_service.sh /opt/chaogu
   ```
5. 查看状态 / 日志：
   ```bash
   systemctl status chaogu-monitor
   journalctl -u chaogu-monitor -f
   ```
   `Restart=always` + `RestartSec=5` 已配好：进程崩溃 5 秒后自动拉起；服务器重启后也会自启。

## 五、方案C：Docker

```bash
cd /opt/chaogu
docker compose up -d --build
docker compose logs -f
```
环境变量在 `docker-compose.yml` 里映射，或用根目录 `.env`。

## 六、常见运维

```bash
# 重启
sudo systemctl restart chaogu-monitor
# 手动跑一轮测试（不推送）
/opt/chaogu/.venv/bin/python news_aggregator/monitor.py --once --dry-run --no-boards
# 只跑一轮（测试推送）
/opt/chaogu/.venv/bin/python news_aggregator/monitor.py --once
# 看日志
journalctl -u chaogu-monitor -n 100
```

## 七、可选：把日报也放到服务器（不依赖 GitHub Actions）

若想不用 GitHub Actions，在服务器加一条 cron 每天 18:30 跑：
```bash
crontab -e
# 加入一行：
30 18 * * 1-5 /opt/chaogu/.venv/bin/python /opt/chaogu/news_aggregator/run.py --push >> /var/log/chaogu-daily.log 2>&1
```
