"""确定性量化建议：方向 + 动作 + 参考仓位（纯规则，与 LLM 无关）。"""

DISCLAIMER = "以上由程序自动生成，仅用于学习研究，不构成投资建议。"

DEFAULT = {
    "threshold_long": 0.3,
    "threshold_flat": -0.3,
    "position_high": 0.6,
    "position_mid": 0.4,
    "position_text_high": "3成以上",
    "position_text_mid": "2~3成",
    "position_text_low": "1成以内",
}


def suggest(impact, sentiment, action_cfg=None) -> dict:
    """由影响分与情绪分给出 {direction, action, position}。

    action_cfg 可覆盖阈值与仓位文案（键名见 DEFAULT）。
    """
    cfg = dict(DEFAULT)
    if action_cfg:
        for k, v in action_cfg.items():
            if k in cfg and v not in (None, ""):
                cfg[k] = v

    imp = float(impact or 0.0)
    s = float(sentiment or 0.0)
    tl = float(cfg["threshold_long"])
    tf = float(cfg["threshold_flat"])

    if s >= tl:
        direction, action = "利好", "关注做多"
    elif s <= tf:
        direction, action = "利空", "回避/对冲"
    else:
        direction, action = "中性", "中性观望"

    if imp >= float(cfg["position_high"]):
        position = str(cfg["position_text_high"])
    elif imp >= float(cfg["position_mid"]):
        position = str(cfg["position_text_mid"])
    else:
        position = str(cfg["position_text_low"])

    return {"direction": direction, "action": action, "position": position}
