import asyncio
from tracking_agent.connectors.fixture import FixtureConnector
from tracking_agent.connectors.base import ConnectorStatus
from tracking_agent.models.enums import NumberType


def test_fixture_returns_html():
    c = FixtureConnector()
    r = asyncio.run(c.fetch("080-38652331", NumberType.AIR_AWB))
    assert r.status == ConnectorStatus.OK and "DEP" in r.raw_html


def test_fixture_not_found():
    c = FixtureConnector()
    r = asyncio.run(c.fetch("501-20285134", NumberType.AIR_AWB))
    assert r.status == ConnectorStatus.NOT_FOUND
