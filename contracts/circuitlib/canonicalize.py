"""Deterministic canonicalization: digests, canonical JSON, and text hygiene.

The capability digest is the contract's spine: it is computed when an incident
is opened, re-derived when a capability is issued, and re-derived again when
the capability is consumed, and any mismatch rejects. That only means anything
if the derivation is byte-for-byte reproducible from the same inputs, so every
piece of it — JSON key order, number encoding, whitespace — is pinned here.

No genlayer imports.
"""

import hashlib
import json
import re

from .ssrf import fail

MAX_TEXT_CHARS = 4000
MAX_POLICY_CHARS = 4000
MAX_SCOPE_CHARS = 500
MAX_TARGET_CHARS = 300
MAX_ACTION_CLASS_CHARS = 64
MAX_INCIDENT_KEY_CHARS = 128
MAX_CHARTER_ID_CHARS = 64

_FENCE_RE = re.compile(r"[`\u0000-\u0008\u000b\u000c\u000e-\u001f]")
_EQ_RUN_RE = re.compile(r"={2,}")
_WS_RE = re.compile(r"\s+")
_ADDR_RE = re.compile(r"^0x[0-9a-f]{40}$")
_CHARTER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
_INCIDENT_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_ACTION_CLASS_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,63}$")


def canonical_json(obj):
    """The one JSON encoding used for every digest and every comparable."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_hex(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def digest_fields(fields):
    return sha256_hex(canonical_json(fields))


def incident_digest(incident_key, charter_hash, target, action_class, scope, duration_minutes):
    """Digest binding one capability to its incident's frozen constants."""
    return digest_fields({
        "incident_key": str(incident_key),
        "charter_hash": str(charter_hash),
        "target": str(target),
        "action_class": str(action_class),
        "scope": str(scope),
        "duration_minutes": int(duration_minutes),
    })


def charter_digest(
    charter_id,
    policy,
    evidence_patterns,
    target,
    action_class,
    max_duration_minutes,
    bond_amount,
    fee_amount,
    treasury,
    executor,
):
    """Digest of a charter's immutable content, frozen at registration.

    `executor` is part of the frozen content: it names the only address allowed
    to consume a capability the charter produces, so it must not be mutable
    without changing the charter's identity.
    """
    return digest_fields({
        "charter_id": str(charter_id),
        "policy": str(policy),
        "evidence_patterns": [str(p) for p in evidence_patterns],
        "target": str(target),
        "action_class": str(action_class),
        "max_duration_minutes": int(max_duration_minutes),
        "bond_amount": int(bond_amount),
        "fee_amount": int(fee_amount),
        "treasury": str(treasury),
        "executor": str(executor),
    })


def _require_str(value, what, limit):
    if not isinstance(value, str):
        fail(what + " must be a string")
    s = value.strip()
    if not s:
        fail(what + " is required")
    if len(s) > limit:
        fail(what + " is too long")
    return s


def normalize_charter_id(value):
    s = _require_str(value, "charter id", MAX_CHARTER_ID_CHARS).lower()
    if not _CHARTER_ID_RE.match(s):
        fail("charter id must be 3-64 chars of a-z, 0-9, dash or underscore")
    return s


def normalize_policy(value):
    return _require_str(value, "policy", MAX_POLICY_CHARS)


def normalize_scope(value):
    return _require_str(value, "scope", MAX_SCOPE_CHARS)


def normalize_target(value):
    return _require_str(value, "target", MAX_TARGET_CHARS)


def normalize_action_class(value):
    s = _require_str(value, "action class", MAX_ACTION_CLASS_CHARS).lower()
    if not _ACTION_CLASS_RE.match(s):
        fail("action class must be a lowercase token")
    return s


def normalize_incident_key(value):
    s = _require_str(value, "incident key", MAX_INCIDENT_KEY_CHARS)
    if not _INCIDENT_KEY_RE.match(s):
        fail("incident key has an invalid character")
    return s


def normalize_address(value):
    """Coerce anything address-shaped into the lowercase 0x-hex form stored here."""
    if isinstance(value, bytes):
        value = value.hex()
    s = str(value).strip().lower()
    if s and not s.startswith("0x"):
        s = "0x" + s
    return s if _ADDR_RE.match(s) else ""


def sanitize_untrusted(raw, limit):
    """Make hostile text safe to embed inside a fenced prompt block.

    Backticks and control characters are removed, then any run of two or more
    `=` is collapsed to one: the fence this text sits inside is a run of `=`,
    so text carrying its own `===` run could otherwise forge a closing marker
    and make whatever follows it read as instruction rather than quoted data.
    Finally the result is bounded, so one oversized page cannot crowd the rules
    out of the prompt.
    """
    if not isinstance(raw, str):
        raw = str(raw)
    t = _FENCE_RE.sub(" ", raw)
    t = _EQ_RUN_RE.sub("=", t)
    t = _WS_RE.sub(" ", t).strip()
    if len(t) > limit:
        t = t[:limit] + " ..."
    return t
