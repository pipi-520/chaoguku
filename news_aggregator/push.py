"""企业微信群机器人推送。"""

import json
import os


def send_wecom_markdown(webhook: str, content: str) -> bool:
    """向企业微信群机器人发送 markdown 消息；webhook 为空时仅打印（干跑）。"""
    if not webhook:
        print("[push] WECOM_WEBHOOK 未配置，干跑打印以下内容：")
        print("-----BEGIN-----")
        print(content)
        print("-----END-----")
        return False

    import requests
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    try:
        r = requests.post(webhook, json=payload, timeout=10)
        ok = (r.status_code == 200)
        data = r.json() if r.text else {}
        print(f"[push] 发送结果 {r.status_code} {json.dumps(data, ensure_ascii=False)}")
        return ok and data.get("errcode") == 0
    except Exception as e:  # noqa: BLE001
        print(f"[push] 发送失败: {e}")
        return False


def get_webhook() -> str:
    return os.environ.get("WECOM_WEBHOOK", "")
