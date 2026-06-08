from tracking_agent.pipeline.router import build_chain
from tracking_agent.models.enums import NumberType


def test_air_chain_prefers_track_trace_then_fixture(monkeypatch):
    chain = build_chain(NumberType.AIR_AWB, use_fixtures=True)
    names = [c.name for c in chain]
    assert names[0].startswith("track-trace")
    assert "fixtures" in names


def test_air_chain_without_fixtures_excludes_fixture():
    chain = build_chain(NumberType.AIR_AWB, use_fixtures=False)
    names = [c.name for c in chain]
    assert "fixtures" not in names
    assert names[0].startswith("track-trace")


def test_container_chain_uses_container_connector():
    chain = build_chain(NumberType.SEA_CONTAINER, use_fixtures=True)
    names = [c.name for c in chain]
    assert names[0] == "track-trace.com/container"
    assert "fixtures" in names


def test_container_chain_without_fixtures():
    chain = build_chain(NumberType.SEA_CONTAINER, use_fixtures=False)
    names = [c.name for c in chain]
    assert "fixtures" not in names


def test_air_chain_includes_cargoai():
    chain = build_chain(NumberType.AIR_AWB, use_fixtures=False)
    names = [c.name for c in chain]
    assert "cargoai" in names
