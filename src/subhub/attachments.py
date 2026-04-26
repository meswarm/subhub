from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from subhub import r2_protocol
from subhub.config import DownloadConfig


@dataclass
class ResolvedMessage:
    content: str
    image_paths: list[Path] = field(default_factory=list)


class AttachmentResolver:
    def __init__(self, download: DownloadConfig, media_store, vision_enabled: bool):
        self._download = download
        self._media_store = media_store
        self._vision_enabled = vision_enabled

    async def resolve(self, content: str) -> ResolvedMessage:
        result = content
        images: list[Path] = []
        for match in list(r2_protocol.iter_r2_markdown_links(content)):
            original = match.group(0)
            alt = match.group("alt")
            clean_uri = r2_protocol.strip_r2_query(match.group("uri"))
            parsed = r2_protocol.parse_r2_uri(clean_uri)
            if not parsed:
                continue
            _bucket, key = parsed
            kind = r2_protocol.infer_media_kind_from_object_key(key)
            mime = r2_protocol.guess_mime_from_object_key(key)
            should_download = {
                "image": self._download.images,
                "video": self._download.videos,
                "audio": self._download.audios,
                "file": self._download.files,
            }[kind]

            local_path = None
            if should_download and self._media_store is not None:
                local_path = await self._media_store.download(clean_uri, kind)

            if kind == "image" and local_path and self._vision_enabled:
                replacement = f"[image:{local_path}:{mime}] {alt}".strip()
                images.append(local_path)
            elif local_path:
                replacement = (
                    f"[用户附件:{kind} 名称:{alt or key} 本地路径:{local_path} 类型:{mime}]"
                )
            else:
                replacement = f"[用户附件:{kind} 名称:{alt or key} 类型:{mime} 未下载]"

            result = result.replace(original, replacement)
        return ResolvedMessage(content=result, image_paths=images)
