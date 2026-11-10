import pytest
from app.core.source_ranking import source_tier


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://reuters.com/story", "tier1"),
        ("https://WWW.REUTERS.COM.:443/story", "tier1"),
        ("https://www.britannica.com/story", "tier2"),
        ("https://fakereuters.com/story", "default"),
        ("https://reuters.com.example.com/story", "default"),
        ("https://reuters.com@example.com/story", "default"),
        ("https://[bad-url", "default"),
    ],
)
def test_source_tier_checks_hostname_boundary(url, expected):
    assert source_tier(url) == expected
