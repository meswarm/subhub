"""Link Webhook 推送客户端。"""

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class WebhookConfig:
    url: str = ""
    enabled: bool = False
    timeout_seconds: int = 5


@dataclass
class WebhookResponse:
    ok: bool
    status_code: int | None = None
    error: str | None = None


def send_text(config: WebhookConfig, message: str) -> WebhookResponse:
    if not config.enabled or not config.url:
        return WebhookResponse(ok=False, error="webhook 未启用")

    payload = json.dumps({"message": message}).encode("utf-8")
    request = Request(
        config.url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            return WebhookResponse(ok=True, status_code=getattr(response, "status", 200))
    except HTTPError as exc:
        return WebhookResponse(ok=False, status_code=exc.code, error=str(exc))
    except URLError as exc:
        return WebhookResponse(ok=False, error=str(exc))
    except Exception as exc:
        return WebhookResponse(ok=False, error=str(exc))
