# 贡献指南 / Contributing

感谢你对 FlashQuant 的关注！欢迎通过以下方式参与：

## 如何贡献

1. **提 Issue**：报告 bug、提需求、讨论想法。
2. **提 PR**：
   - Fork 本仓库，新建分支（如 `feat/xxx`、`fix/xxx`）。
   - 保持改动聚焦，一个 PR 只做一件事。
   - 新功能请补充必要的中文注释与文档。
3. **完善主题库**：在 `news_aggregator/themes.yaml` 里增删主题/关键词，是最简单的贡献方式。

## 开发约定

- 脚本统一用 UTF-8 编码，Python 3.12。
- 数据抓取单源失败不中断（沿用 `fetchers.py` 的容错风格）。
- 推送密钥一律走环境变量或 `config.yaml` 的 `monitor` / `primary` 段，**不要提交真实密钥**（`.env` 已被 gitignore）。

## 运行自检

```bash
python -m py_compile news_aggregator/*.py scripts/*.py
python news_aggregator/monitor.py --once --dry-run --no-boards
```

> 本项目仅用于学习研究，不构成投资建议。

---

## How to contribute (English)

1. **Issues**: bug reports, feature requests, discussions.
2. **Pull Requests**: fork, create a focused branch, keep one PR per change.
3. **Themes**: editing `news_aggregator/themes.yaml` is the easiest way to contribute.

Conventions: UTF-8, Python 3.12, per-source fault tolerance, never commit real secrets.