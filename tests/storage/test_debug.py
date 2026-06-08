from pathlib import Path

from tracking_agent.storage.debug import save_debug_html


def test_save_debug_html_writes_file(tmp_path):
    p = save_debug_html(str(tmp_path), "080-38652331__fixtures", "<html>hi</html>")
    assert Path(p).exists()
    assert Path(p).read_text(encoding="utf-8") == "<html>hi</html>"


def test_save_debug_html_sanitizes_name(tmp_path):
    p = save_debug_html(str(tmp_path), "a/b:c*?", "<x/>")
    assert Path(p).exists()
    assert "/" not in Path(p).name and ":" not in Path(p).name
