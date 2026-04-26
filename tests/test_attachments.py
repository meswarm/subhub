from pathlib import Path

import pytest

from subhub.attachments import AttachmentResolver
from subhub.config import DownloadConfig


class FakeStore:
    def __init__(self, paths):
        self.paths = paths
        self.downloaded = []

    async def download(self, r2_uri: str, kind: str) -> Path | None:
        self.downloaded.append((r2_uri, kind))
        return self.paths.get(r2_uri)


@pytest.mark.asyncio
async def test_downloads_image_when_enabled(tmp_path):
    local = tmp_path / "downloads" / "imgs" / "a.png"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"png")
    store = FakeStore({"r2://bucket/room/imgs/a.png": local})
    resolver = AttachmentResolver(
        download=DownloadConfig(
            root=tmp_path / "downloads",
            images=True,
            videos=False,
            audios=False,
            files=False,
        ),
        media_store=store,
        vision_enabled=True,
    )

    resolved = await resolver.resolve("看图 ![a](r2://bucket/room/imgs/a.png)")

    assert "[image:" in resolved.content
    assert resolved.image_paths == [local]
    assert store.downloaded == [("r2://bucket/room/imgs/a.png", "image")]


@pytest.mark.asyncio
async def test_does_not_download_video_by_default(tmp_path):
    store = FakeStore({})
    resolver = AttachmentResolver(
        download=DownloadConfig(
            root=tmp_path / "downloads",
            images=True,
            videos=False,
            audios=False,
            files=False,
        ),
        media_store=store,
        vision_enabled=True,
    )

    resolved = await resolver.resolve("视频 ![v](r2://bucket/room/videos/a.mp4)")

    assert "用户附件:video" in resolved.content
    assert store.downloaded == []
