import pytest
from app.core.source_ranking import source_display_name, source_tier


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


@pytest.mark.parametrize(
    ("url", "name"),
    [
        ("https://reuters.com/story", "Reuters"),
        ("https://WWW.REUTERS.COM.:443/story", "Reuters"),
        ("https://www.britannica.com/story", "Encyclopaedia Britannica"),
        ("https://reuters.com.example.com/story", None),
        ("https://reuters.com@example.com/story", None),
        ("https://[bad-url", None),
    ],
)
def test_source_display_name_matches_trusted_domain(url, name):
    assert source_display_name(url) == name
