from tracking_agent.config import Settings


def test_defaults():
    # ignore any local .env so this asserts the code defaults, not the dev's config
    s = Settings(_env_file=None)
    assert s.max_concurrency >= 1
    assert s.llm_enabled is False
    assert "openrouter" in s.llm_base_url
