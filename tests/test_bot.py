from subhub.bot import _preview_text


def test_preview_text_compacts_whitespace_and_truncates():
    text = "第一行\n第二行\t第三行 " + ("x" * 200)

    preview = _preview_text(text, limit=32)

    assert "\n" not in preview
    assert "\t" not in preview
    assert preview.endswith("...")
