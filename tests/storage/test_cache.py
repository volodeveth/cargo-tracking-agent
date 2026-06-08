from tracking_agent.storage.cache import Cache


def test_cache_set_get_roundtrip(tmp_path):
    c = Cache(str(tmp_path / "t.db"), ttl_minutes=60)
    c.set("080-38652331", {"x": 1})
    assert c.get("080-38652331") == {"x": 1}


def test_cache_expiry(tmp_path):
    c = Cache(str(tmp_path / "t.db"), ttl_minutes=0)
    c.set("n", {"x": 1})
    assert c.get("n") is None
