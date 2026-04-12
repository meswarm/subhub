"""webhook 模块测试。"""

from unittest.mock import patch

from subhub.webhook import WebhookConfig, send_text


class _MockResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@patch("subhub.webhook.urlopen")
def test_send_text_success(mock_urlopen):
    mock_urlopen.return_value = _MockResponse(status=200)
    resp = send_text(WebhookConfig(url="http://localhost:9001/alert", enabled=True), "hello")
    assert resp.ok is True
    assert resp.status_code == 200


@patch("subhub.webhook.urlopen", side_effect=Exception("boom"))
def test_send_text_unexpected_error_returns_failure(mock_urlopen):
    resp = send_text(WebhookConfig(url="http://localhost:9001/alert", enabled=True), "hello")
    assert resp.ok is False
