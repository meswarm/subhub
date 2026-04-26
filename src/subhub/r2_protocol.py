"""R2 与移动端对齐的协议工具。"""

from __future__ import annotations

import mimetypes
import re
import time
from typing import Iterator, Literal
from urllib.parse import urlparse

R2_PREFIX_EVENT_TYPE = "com.talk.r2_prefix"
R2_PREFIX_STATE_KEY = ""

AttachmentDir = Literal["imgs", "videos", "audios", "files"]
MediaKind = Literal["image", "video", "audio", "file"]


class InvalidR2PrefixError(ValueError):
    """房间 R2 prefix 未配置或校验失败。"""


def validate_r2_prefix(raw: str | None) -> str:
    if raw is None:
        raise InvalidR2PrefixError("房间未配置 com.talk.r2_prefix")
    if not isinstance(raw, str):
        raise InvalidR2PrefixError("房间 R2 prefix 必须为字符串")
    s = raw.strip()
    if not s:
        raise InvalidR2PrefixError("房间 R2 prefix 为空（请在房间信息中配置）")
    if "\\" in s:
        raise InvalidR2PrefixError("房间 R2 prefix 不能包含反斜杠")
    if s.startswith("/") or s.endswith("/"):
        raise InvalidR2PrefixError("房间 R2 prefix 不能以 / 开头或结尾")
    if "//" in s:
        raise InvalidR2PrefixError("房间 R2 prefix 不能包含空路径段")
    for seg in s.split("/"):
        if seg in (".", ".."):
            raise InvalidR2PrefixError("房间 R2 prefix 路径段不能为 . 或 ..")
    return s


def attachment_dir_from_mime(mime: str) -> AttachmentDir:
    m = (mime or "").strip().lower()
    if m.startswith("image/"):
        return "imgs"
    if m.startswith("video/"):
        return "videos"
    if m.startswith("audio/"):
        return "audios"
    return "files"


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_ .\-()+]")


def sanitize_filename(name: str) -> str:
    s = (name or "").strip().replace("/", "_").replace("\\", "_")
    s = _SAFE_NAME_RE.sub("_", s)
    if not s:
        s = "file"
    if len(s) > 120:
        s = s[:120]
    return s


def build_object_key(
    room_prefix: str,
    mime: str,
    original_filename: str,
    timestamp_ms: int | None = None,
) -> str:
    prefix = validate_r2_prefix(room_prefix)
    d = attachment_dir_from_mime(mime)
    ts = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
    safe = sanitize_filename(original_filename)
    return f"{prefix}/{d}/{ts}-{safe}"


def parse_r2_uri(r2_uri: str) -> tuple[str, str] | None:
    u = (r2_uri or "").strip()
    if not u.startswith("r2://"):
        return None
    parsed = urlparse(u)
    if parsed.scheme != "r2":
        return None
    netloc = parsed.netloc
    if not netloc:
        return None
    path = parsed.path or ""
    if path.startswith("/"):
        path = path[1:]
    if not path:
        return None
    return netloc, path


def strip_r2_query(r2_uri: str) -> str:
    p = urlparse(r2_uri)
    return f"r2://{p.netloc}{p.path}"


def local_cache_relative_path(object_key: str) -> str:
    key = (object_key or "").replace("\\", "/").lstrip("/")
    parts = [p for p in key.split("/") if p]
    for i, p in enumerate(parts):
        if p in ("imgs", "videos", "audios", "files"):
            return "/".join(parts[i:])
    return "/".join(parts)


def infer_media_kind_from_object_key(object_key: str) -> MediaKind:
    key = object_key.replace("\\", "/")
    parts = [p for p in key.split("/") if p]
    for p in parts:
        if p == "imgs":
            return "image"
        if p == "videos":
            return "video"
        if p == "audios":
            return "audio"
        if p == "files":
            return "file"
    ext = ""
    if "." in key:
        ext = key.rsplit(".", 1)[-1].lower()
    image_ext = {"jpg", "jpeg", "png", "gif", "webp", "heic"}
    video_ext = {"mp4", "mov", "webm", "m4v"}
    audio_ext = {"mp3", "m4a", "aac", "wav", "ogg", "opus", "flac", "weba"}
    if ext in image_ext:
        return "image"
    if ext in video_ext:
        return "video"
    if ext in audio_ext:
        return "audio"
    return "file"


def guess_mime_from_object_key(object_key: str) -> str:
    kind = infer_media_kind_from_object_key(object_key)
    name = object_key.rsplit("/", 1)[-1] if "/" in object_key else object_key
    guessed, _ = mimetypes.guess_type(name)
    if guessed:
        return guessed
    if kind == "image":
        return "image/jpeg"
    if kind == "video":
        return "video/mp4"
    if kind == "audio":
        return "audio/mpeg"
    return "application/octet-stream"


def media_kind_from_mime(mime: str) -> MediaKind:
    m = (mime or "").strip().lower()
    if m.startswith("image/"):
        return "image"
    if m.startswith("video/"):
        return "video"
    if m.startswith("audio/"):
        return "audio"
    return "file"


def outbound_markdown_for_r2(kind: MediaKind, alt: str, r2_uri: str) -> str:
    alt = (alt or "").strip() or "attachment"
    if kind == "image":
        return f"![{alt}]({r2_uri})"
    if kind == "video":
        base = alt.removesuffix("（视频）").strip() or alt
        return f"![{base}（视频）]({r2_uri})"
    if kind == "audio":
        base = alt.removesuffix("（音频）").strip() or alt
        return f"![{base}（音频）]({r2_uri})"
    return f"[{alt}]({r2_uri})"


_MARKDOWN_LINK_OPEN_RE = re.compile(r"!?\[([^\]]*)\]\(")


class R2MarkdownLinkMatch:
    """兼容 `re.Match` 的 `.group('alt'|'uri'|0)`。"""

    __slots__ = ("_full", "_alt", "_uri")

    def __init__(self, full: str, alt: str, uri: str) -> None:
        self._full = full
        self._alt = alt
        self._uri = uri

    def group(self, name: str | int = 0) -> str:
        if name == 0:
            return self._full
        if name == "alt":
            return self._alt
        if name == "uri":
            return self._uri
        raise IndexError(f"no such group: {name!r}")


def _url_inside_outer_paren(body: str, uri_start: int) -> tuple[str, int] | None:
    depth = 1
    k = uri_start
    while k < len(body):
        c = body[k]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return body[uri_start:k], k + 1
        k += 1
    return None


def iter_r2_markdown_links(body: str) -> Iterator[R2MarkdownLinkMatch]:
    pos = 0
    while pos < len(body):
        m = _MARKDOWN_LINK_OPEN_RE.search(body, pos)
        if not m:
            break
        alt = m.group(1)
        after_open = m.end()
        tail = body[after_open:]
        stripped = tail.lstrip()
        if not stripped.startswith("r2://"):
            pos = after_open
            continue
        uri_start = after_open + (len(tail) - len(stripped))
        got = _url_inside_outer_paren(body, uri_start)
        if got is None:
            break
        uri, end_excl = got
        full = body[m.start() : end_excl]
        yield R2MarkdownLinkMatch(full, alt, uri)
        pos = end_excl
