from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiofiles

from subhub import r2_protocol


@dataclass(frozen=True)
class MediaStoreConfig:
    root: Path


class R2MediaStore:
    def __init__(self, config: MediaStoreConfig):
        self._config = config

    async def download(self, r2_uri: str, kind: str) -> Path | None:
        parsed = r2_protocol.parse_r2_uri(r2_uri)
        if parsed is None:
            return None
        _bucket, object_key = parsed
        relative = r2_protocol.local_cache_relative_path(object_key)
        filename = Path(relative).name
        directory = {
            "image": "imgs",
            "video": "videos",
            "audio": "audios",
            "file": "files",
        }.get(kind, "files")
        local_path = self._config.root / directory / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(local_path, "wb") as f:
            await f.write(b"")
        return local_path
