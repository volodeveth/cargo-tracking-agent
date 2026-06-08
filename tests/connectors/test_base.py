from tracking_agent.connectors.base import ConnectorResult, ConnectorStatus


def test_connector_result_ok():
    r = ConnectorResult(status=ConnectorStatus.OK, raw_html="<html></html>", url="u", source="fixture")
    assert r.status == ConnectorStatus.OK
    assert r.error_code is None
