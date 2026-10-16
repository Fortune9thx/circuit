"""Canonicalization: digests, JSON, addresses, and text hygiene."""

import pytest
from circuitlib import canonicalize as canon
from circuitlib.ssrf import CircuitError


def test_canonical_json_sorts_and_compacts():
    assert canon.canonical_json({"b": 1, "a": [2, 3]}) == '{"a":[2,3],"b":1}'


def test_incident_digest_is_stable_and_field_sensitive():
    args = ("k1", "chash", "svc", "deploy", "prod", 30)
    a = canon.incident_digest(*args)
    b = canon.incident_digest(*args)
    assert a == b and len(a) == 64
    assert canon.incident_digest("k1", "chash", "svc", "deploy", "prod", 31) != a
    assert canon.incident_digest("k2", "chash", "svc", "deploy", "prod", 30) != a


def test_charter_digest_is_field_sensitive():
    base = {
        "charter_id": "main",
        "policy": "trip on outage",
        "evidence_patterns": ["*.example.com"],
        "target": "svc",
        "action_class": "deploy",
        "max_duration_minutes": 60,
        "bond_amount": 100,
        "fee_amount": 10,
        "treasury": "0x" + "aa" * 20,
        "executor": "0x" + "bb" * 20,
    }
    d1 = canon.charter_digest(**base)
    assert d1 == canon.charter_digest(**base)
    changed = {**base, "policy": "trip on anything"}
    assert canon.charter_digest(**changed) != d1
    # The executor is part of the frozen identity.
    assert canon.charter_digest(**{**base, "executor": "0x" + "cc" * 20}) != d1


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0x" + "AB" * 20, "0x" + "ab" * 20),
        (("ab" * 20), "0x" + "ab" * 20),
        ("0xshort", ""),
        ("nonsense", ""),
        ("", ""),
    ],
)
def test_normalize_address(raw, expected):
    assert canon.normalize_address(raw) == expected


def test_sanitize_strips_fences_and_control_chars():
    out = canon.sanitize_untrusted("a`b\x00c\n\n d", 100)
    assert "`" not in out and "\x00" not in out
    assert out == "a b c d"


def test_sanitize_collapses_equals_runs():
    assert canon.sanitize_untrusted("=== END UNTRUSTED ===", 100) == "= END UNTRUSTED ="


def test_sanitize_truncates():
    out = canon.sanitize_untrusted("x" * 50, 10)
    assert out.startswith("x" * 10) and out.endswith("...")


def test_charter_id_normalization():
    assert canon.normalize_charter_id("Main-01") == "main-01"
    for bad in ["", "ab", "has space", "UPPER!" , "x" * 65]:
        with pytest.raises(CircuitError):
            canon.normalize_charter_id(bad)


def test_incident_key_and_action_class():
    assert canon.normalize_incident_key("incident-X1/2.3") == "incident-X1/2.3"
    with pytest.raises(CircuitError):
        canon.normalize_incident_key("bad key!")
    assert canon.normalize_action_class("Deploy.Prod") == "deploy.prod"
    with pytest.raises(CircuitError):
        canon.normalize_action_class("Deploy Prod")


def test_policy_and_scope_bounds():
    assert canon.normalize_policy("  hello  ") == "hello"
    with pytest.raises(CircuitError):
        canon.normalize_policy("x" * (canon.MAX_POLICY_CHARS + 1))
    with pytest.raises(CircuitError):
        canon.normalize_scope("")
