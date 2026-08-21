"""新闻一句话摘要：LLM 优先，失败回退规则模板。

- summarize(text, theme, impact, sentiment, lang, cfg_summary, cfg_sentiment) -> str
- summarize_many(texts, cfg_summary, cfg_sentiment, sentiments=None) -> list[str]
- summarize_overview(texts, cfg_summary, cfg_sentiment) -> str

LLM 复用 OpenAI 兼容接口；密钥按 summary.llm_* -> sentiment.llm_* -> 环境变量 回退。
仅当 impact >= llm_min_impact 且配置了 key 才调 LLM，否则直接用规则模板。
规则回退：中文=原文截断+主题标签；英文=原文截断+情绪方向词（不翻译）。
"""

import json
import os
import re


def _is_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _direction_word(sentiment) -> str:
    s = float(sentiment or 0.0)
    if s >= 0.3:
        return "利好"
    if s <= -0.3:
        return "利空"
    return "中性"


def _rule_summary(text: str, theme: str = "", sentiment=0.0) -> str:
    t = re.sub(r"\s+", " ", str(text or "").strip())
    head = t[:80] + ("…" if len(t) > 80 else "")
    if not head:
        return "(无内容)"
    prefix = f"【{theme}】" if theme else ""
    if _is_cjk(head):
        return prefix + head
    return prefix + head + f"（{_direction_word(sentiment)}）"


def _llm_config(cfg_summary, cfg_sentiment):
    cfg_summary = cfg_summary or {}
    cfg_sentiment = cfg_sentiment or {}
    base = (cfg_summary.get("llm_api_base") or cfg_sentiment.get("llm_api_base")
            or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    key = (cfg_summary.get("llm_api_key") or cfg_sentiment.get("llm_api_key")
           or os.environ.get("OPENAI_API_KEY", "")).strip()
    model = (cfg_summary.get("llm_model") or cfg_sentiment.get("llm_model")
             or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")).strip()
    return base, key, model


def _chat(base: str, key: str, model: str, prompt: str, timeout: int) -> str:
    import requests
    r = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "temperature": 0,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=timeout,
    )
    data = r.json()
    return data["choices"][0]["message"]["content"]


def _parse_json(content: str):
    m = re.search(r"\{.*\}", content, re.S)
    if m:
        return json.loads(m.group(0))
    m = re.search(r"\[.*\]", content, re.S)
    if m:
        return json.loads(m.group(0))
    return None


def summarize(text, theme="", impact=0.0, sentiment=0.0, lang="zh",
              cfg_summary=None, cfg_sentiment=None) -> str:
    cfg_summary = cfg_summary or {}
    cfg_sentiment = cfg_sentiment or {}
    llm_min = float(cfg_summary.get("llm_min_impact", 0.4))
    timeout = int(cfg_summary.get("timeout", 20))
    base, key, model = _llm_config(cfg_summary, cfg_sentiment)

    if key and float(impact or 0.0) >= llm_min:
        prompt = (
            "你是财经新闻摘要助手。把下面的新闻浓缩成一句中文，"
            "点出事件本身及对市场的影响方向。只返回 JSON：{\"summary\":\"一句话中文\"}\n\n"
            f"新闻：{text}"
        )
        try:
            obj = _parse_json(_chat(base, key, model, prompt, timeout))
            s = str((obj or {}).get("summary") or "").strip()
            if s:
                return s
        except Exception:
            pass
    return _rule_summary(text, theme, sentiment)


def summarize_many(texts, cfg_summary=None, cfg_sentiment=None, sentiments=None) -> list:
    texts = [re.sub(r"\s+", " ", str(t or "")).strip() for t in (texts or [])]
    if not texts:
        return []
    sentiments = list(sentiments or []) if sentiments is not None else [0.0] * len(texts)
    cfg_summary = cfg_summary or {}
    cfg_sentiment = cfg_sentiment or {}
    timeout = int(cfg_summary.get("timeout", 20))
    base, key, model = _llm_config(cfg_summary, cfg_sentiment)

    if key:
        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
        prompt = (
            "把下面每条财经新闻各浓缩成一句中文摘要，按顺序返回 JSON 数组："
            "[\"摘要1\",\"摘要2\",...]\n\n" + numbered
        )
        try:
            obj = _parse_json(_chat(base, key, model, prompt, timeout))
            if isinstance(obj, list):
                out = [str(x).strip() for x in obj[:len(texts)]]
                if len(out) == len(texts):
                    return out
        except Exception:
            pass
    return [_rule_summary(t, "", sentiments[i] if i < len(sentiments) else 0.0)
            for i, t in enumerate(texts)]


def summarize_overview(texts, cfg_summary=None, cfg_sentiment=None) -> str:
    texts = [re.sub(r"\s+", " ", str(t or "")).strip() for t in (texts or []) if str(t or "").strip()]
    if not texts:
        return "（今日无显著事件）"
    cfg_summary = cfg_summary or {}
    cfg_sentiment = cfg_sentiment or {}
    timeout = int(cfg_summary.get("timeout", 20))
    base, key, model = _llm_config(cfg_summary, cfg_sentiment)

    if key:
        joined = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts[:15]))
        prompt = (
            "下面是今日影响最强的财经新闻标题。用 2~3 句中文写一段今日市场综述，"
            "概括主线与风险偏好。只返回 JSON：{\"overview\":\"...\"}\n\n" + joined
        )
        try:
            obj = _parse_json(_chat(base, key, model, prompt, timeout))
            s = str((obj or {}).get("overview") or "").strip()
            if s:
                return s
        except Exception:
            pass
    top = "；".join((t[:40] + "…" if len(t) > 40 else t) for t in texts[:3])
    return f"今日影响最强：{top}"

