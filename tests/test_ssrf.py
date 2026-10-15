"""SSRF policy: the accept/reject matrix and the pattern allow-list."""

import pytest
from circuitlib import ssrf
from circuitlib.ssrf import CircuitError, ssrf_reason


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/path",
        "https://api.example.com/report?id=3",
        "https://news.bbc.co.uk/article",
        "https://sub.domain.example.org",
    ],
)
def test_accepts_public_https(url):
    assert ssrf_reason(url) is None


@pytest.mark.parametrize(
    "url,reason",
    [
        ("ftp://example.com/x", "scheme must be https"),
        ("http://example.com/x", "scheme must be https"),
        ("https://localhost/x", "host is internal or loopback"),
        ("https://api.localhost/x", "host is internal or loopback"),
        ("https://box.local/x", "host is internal or loopback"),
        ("https://example.home.arpa/x", "host is internal or loopback"),
        ("https://127.0.0.1/x", "host is an ip literal"),
        ("https://10.0.0.1/x", "host is an ip literal"),
        ("https://169.254.169.254/latest/meta-data/", "host is an ip literal"),
        ("https://100.64.0.1/x", "host is an ip literal"),
        ("https://198.51.100.7/x", "host is an ip literal"),
        ("https://[::1]/x", "host is an ip literal"),
        ("https://0x7f000001/x", "host is an ip literal"),
        ("https://2130706433/x", "host is an ip literal"),
        ("https://user:pass@example.com/x", "url must not embed credentials"),
        ("https://example.com:8443/x", "port must be the default https port"),
        ("https://example.com:443/x", "port must be the default https port"),
        ("https://foo/x", "host must be a public domain"),
        ("https://example.123/x", "host must end in an alphabetic tld"),
        ("https:///x", "url has no host"),
        ("https://", "url has no host"),
        ("", "url is empty"),
        ("   ", "url is empty"),
    ],
)
def test_rejects_with_reason(url, reason):
    assert ssrf_reason(url) == reason


def test_rejects_overlong_url():
    assert ssrf_reason("https://example.com/" + "a" * 600) == "url too long"


def test_rejects_non_string():
    assert ssrf_reason(None) == "url must be a string"


def test_validate_url_raises():
    with pytest.raises(CircuitError):
        ssrf.validate_url("http://example.com")


def test_pattern_wildcard_matches_subdomains_and_apex():
    assert ssrf.pattern_matches_host("*.example.com", "a.example.com")
    assert ssrf.pattern_matches_host("*.example.com", "deep.a.example.com")
    assert ssrf.pattern_matches_host("*.example.com", "example.com")
    assert not ssrf.pattern_matches_host("*.example.com", "example.com.evil.net")
    assert not ssrf.pattern_matches_host("*.example.com", "notexample.com")


def test_pattern_exact_matches_only_exact():
    assert ssrf.pattern_matches_host("example.com", "example.com")
    assert not ssrf.pattern_matches_host("example.com", "a.example.com")


@pytest.mark.parametrize("bad", ["", "example", "*.123", "exa mple.com", "-bad.com"])
def test_bad_patterns_rejected(bad):
    with pytest.raises(CircuitError):
        ssrf.normalize_pattern(bad)


def test_normalize_patterns_dedupes():
    assert ssrf.normalize_patterns(["*.Example.com", "*.example.com."]) == ["*.example.com"]


def test_normalize_evidence_urls_enforces_patterns():
    urls = ["https://a.example.com/1", "https://b.example.com/2"]
    assert ssrf.normalize_evidence_urls(urls, ["*.example.com"]) == urls
    with pytest.raises(CircuitError):
        ssrf.normalize_evidence_urls(["https://evil.net/1"], ["*.example.com"])


def test_normalize_evidence_urls_bounds_and_dedupes():
    with pytest.raises(CircuitError):
        ssrf.normalize_evidence_urls([], None)
    with pytest.raises(CircuitError):
        ssrf.normalize_evidence_urls([f"https://a.com/{i}" for i in range(6)], None)
    assert ssrf.normalize_evidence_urls(
        ["https://a.com/x", "https://a.com/x", "https://a.com/y"], None
    ) == ["https://a.com/x", "https://a.com/y"]
