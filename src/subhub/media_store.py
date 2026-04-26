from __future__ import annotations

from pathlib import Path

import aiofiles
import aioboto3

from subhub import r2_protocol
from subhub.config import R2Config


class R2MediaStore:
    def __init__(self, config: R2Config, root: Path):
        self._config = config
        self._root = Path(root)

    async def download(self, r2_uri: str, kind: str) -> Path | None:
        parsed = r2_protocol.parse_r2_uri(r2_uri)
        if parsed is None:
            return None
        bucket, object_key = parsed
        relative = r2_protocol.local_cache_relative_path(object_key)
        filename = Path(relative).name
        directory = {
            "image": "imgs",
            "video": "videos",
            "audio": "audios",
            "file": "files",
        }.get(kind, "files")
        local_path = self._root / directory / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)
        session = aioboto3.Session(
            aws_access_key_id=self._config.access_key,
            aws_secret_access_key=self._config.secret_key,
        )
        async with session.client(
            "s3",
            endpoint_url=self._config.endpoint,
        ) as client:
            response = await client.get_object(Bucket=bucket, Key=object_key)
            payload = await response["Body"].read()
        async with aiofiles.open(local_path, "wb") as f:
            await f.write(payload)
        return local_path
