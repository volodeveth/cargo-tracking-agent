from tracking_agent.storage.history import History


def test_history_detects_change(tmp_path):
    h = History(str(tmp_path / "h.db"))
    assert h.record("n", "in_transit") is True
    assert h.record("n", "in_transit") is False
    assert h.record("n", "arrived") is True
    assert h.last_status("n") == "arrived"
