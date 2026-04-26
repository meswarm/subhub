from subhub import r2_protocol


def test_validate_prefix():
    assert r2_protocol.validate_r2_prefix("  team-a/A-room  ") == "team-a/A-room"


def test_validate_prefix_rejects_invalid_values():
    for value in (None, "/bad", "a//b"):
        try:
            r2_protocol.validate_r2_prefix(value)  # type: ignore[arg-type]
        except r2_protocol.InvalidR2PrefixError:
            continue
        raise AssertionError(f"expected InvalidR2PrefixError for {value!r}")


def test_attachment_dir_and_object_key():
    assert r2_protocol.attachment_dir_from_mime("image/png") == "imgs"
    assert r2_protocol.attachment_dir_from_mime("video/mp4") == "videos"
    assert r2_protocol.attachment_dir_from_mime("audio/mpeg") == "audios"
    assert r2_protocol.attachment_dir_from_mime("application/pdf") == "files"
    assert (
        r2_protocol.build_object_key(
            "subhub",
            "image/png",
            "photo.png",
            timestamp_ms=1776581000000,
        )
        == "subhub/imgs/1776581000000-photo.png"
    )


def test_parse_r2_uri_and_local_cache_path():
    bucket, key = r2_protocol.parse_r2_uri("r2://linux-storage/subhub/imgs/a.png")
    assert bucket == "linux-storage"
    assert key == "subhub/imgs/a.png"
    assert r2_protocol.parse_r2_uri("https://x") is None
    assert r2_protocol.local_cache_relative_path("subhub/imgs/1776581000000-photo.png") == "imgs/1776581000000-photo.png"
    assert r2_protocol.local_cache_relative_path("odd/layout/no-media-dir.bin") == "odd/layout/no-media-dir.bin"


def test_kind_and_mime_helpers():
    assert r2_protocol.infer_media_kind_from_object_key("subhub/videos/x.mp4") == "video"
    assert r2_protocol.infer_media_kind_from_object_key("subhub/imgs/x.png") == "image"
    assert r2_protocol.guess_mime_from_object_key("subhub/imgs/x.png") == "image/png"
    assert r2_protocol.media_kind_from_mime("audio/mpeg") == "audio"


def test_outbound_markdown_and_iter_links():
    u = "r2://b/k"
    assert r2_protocol.outbound_markdown_for_r2("image", "a", u).startswith("![a](")
    assert "（视频）" in r2_protocol.outbound_markdown_for_r2("video", "a", u)
    assert "（音频）" in r2_protocol.outbound_markdown_for_r2("audio", "a", u)
    assert r2_protocol.outbound_markdown_for_r2("file", "a", u).startswith("[a](")

    body = f"a ![u1]({u}) b ![u2](r2://b/p/a_(b).mp3) c"
    matches = list(r2_protocol.iter_r2_markdown_links(body))
    assert [m.group("uri") for m in matches] == [u, "r2://b/p/a_(b).mp3"]
