from tracking_agent.config import get_settings


def test_defaults():
    s = get_settings()
    assert s.max_concurrency >= 1
    assert s.llm_enabled is False
    assert "openrouter" in s.llm_base_url
