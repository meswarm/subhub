from pathlib import Path

import pytest

from subhub.config import R2Config
from subhub.media_store import R2MediaStore


class FakeBody:
    def __init__(self, payload: bytes):
        self._payload = payload

    async def read(self) -> bytes:
        return self._payload


class FakeS3Client:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get_object(self, Bucket: str, Key: str):
        self.calls.append((Bucket, Key))
        return {"Body": FakeBody(self.payload)}


class FakeSession:
    def __init__(self, client):
        self._client = client

    def client(self, *_args, **_kwargs):
        return self._client


@pytest.mark.asyncio
async def test_r2_media_store_downloads_object(monkeypatch, tmp_path):
    client = FakeS3Client(b"image-bytes")
    monkeypatch.setattr(
        "subhub.media_store.aioboto3.Session",
        lambda **_kwargs: FakeSession(client),
    )
    store = R2MediaStore(
        R2Config(
            endpoint="https://r2.example.com",
            access_key="ak",
            secret_key="sk",
            bucket="linux-storage",
            public_url="",
        ),
        tmp_path / "downloads",
    )

    local_path = await store.download(
        "r2://linux-storage/subhub/imgs/1777188865565-1000013399.jpg",
        "image",
    )

    assert local_path == tmp_path / "downloads" / "imgs" / "1777188865565-1000013399.jpg"
    assert local_path.read_bytes() == b"image-bytes"
    assert client.calls == [("linux-storage", "subhub/imgs/1777188865565-1000013399.jpg")]
