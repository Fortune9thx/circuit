# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }
"""CIRCUIT — a temporary circuit-breaker protocol.

A charter is a written tripwire: a policy, the evidence hosts it may be judged
against, a target, an action class, and a bond/fee schedule. An assessor posts
a bond to open an incident and freezes the evidence URLs and a canonical
digest. Validators then independently fetch that evidence and decide, under the
Equivalence Principle, exactly one of six discrete verdicts.

Only `TRIGGER_CONFIRMED` issues a capability. Every other verdict — including
every technical failure — refunds the bond in full and issues nothing. A
capability is a single-use, expiring artifact whose digest is recomputed at
freeze, at issuance, and at consumption; any mismatch rejects.

State is JSON documents in TreeMaps rather than nested storage dataclasses:
incidents are read and written whole, so a single document is the natural
unit, and a flat storage surface is easier to audit than a graph of one.
"""

import datetime
import json

import genlayer as gl

# isort: off
# These two MUST stay above the circuitlib marker below. The bundler replaces
# everything between the markers with inlined circuitlib source, so an SDK
# import that drifts inside the block is silently deleted from the deployable
# while every local test keeps passing against the fake runtime. That happened
# on a sibling project, and the fix is this comment.
from genlayer.storage import TreeMap
from genlayer.types import *
# isort: on

# --- circuitlib (inlined by contracts/build_bundle.py for deployment) -------
from circuitlib.accounting import settle
from circuitlib.canonicalize import (
    charter_digest,
    incident_digest,
    normalize_action_class,
    normalize_charter_id,
    normalize_incident_key,
    normalize_policy,
    normalize_scope,
    normalize_target,
)
from circuitlib.judgment import (
    INSUFFICIENT,
    TRIGGER_CONFIRMED,
    build_comparable,
    build_prompt,
    canon_decision,
    comparable_json,
    normalize_evidence,
)
from circuitlib.ssrf import (
    MAX_EVIDENCE_URLS,
    CircuitError,
    normalize_evidence_urls,
    normalize_patterns,
)

# --- end circuitlib ---------------------------------------------------------

ST_OPEN = "OPEN"
ST_ASSESSED = "ASSESSED"
ST_EXPIRED = "EXPIRED"

MIN_DURATION_MINUTES = 5
MAX_DURATION_MINUTES = 120
ASSESS_DELAY_SECONDS = 1800  # parties first, then permissionless
STUCK_TIMEOUT_SECONDS = 86400  # an incident nobody assessed is refunded
MAX_BOARD = 50


@gl.evm.contract_interface
class _Recipient:
    """Nameless-transfer interface used to pay native GEN out to a wallet."""

    class View:
        pass

    class Write:
        pass


def _err(reason):
    """Raise a stable, lowercase, machine-comparable user error."""
    raise gl.vm.UserError(reason)


def _safe_json(raw):
    """Parse model output without ever letting a parse failure become a decision."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            return {}
        try:
            parsed = json.loads(raw[start:end + 1])
        except Exception:
            return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_agreed(agreed, fallback):
    """Read what the validators agreed on, failing closed on anything else."""
    if not isinstance(agreed, str) or not agreed.strip():
        return dict(fallback)
    try:
        parsed = json.loads(agreed)
    except Exception:
        return dict(fallback)
    return parsed if isinstance(parsed, dict) else dict(fallback)


def _to_account_str(value):
    """Coerce an address-shaped argument into the lowercase hex string stored here.

    Tooling can hand a 40-hex address to a `str`-annotated parameter already
    decoded as an `Address`; accepting both means an address-typed caller is
    never locked out by an encoding detail while local tests pass.
    """
    if isinstance(value, Address):
        return value.as_hex.lower()
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def _to_address(value):
    """Coerce a constructor argument into an Address, or None if unset."""
    if value is None or value == "":
        return None
    if isinstance(value, Address):
        return value
    return Address(value)


def _guard(fn):
    """Run pure-lib code, translating its CircuitError into a GenVM user error."""
    try:
        return fn()
    except CircuitError as e:
        _err(str(e))


_FAIL_CLOSED = build_comparable({"decision": INSUFFICIENT}, [], [])


class Circuit(gl.contract.Contract):
    # --- storage ----------------------------------------------------------
    owner: Address
    treasury: Address
    next_charter: u256
    next_incident: u256
    next_capability: u256

    charters: TreeMap[str, str]       # charter id -> charter JSON
    charter_ids: TreeMap[str, str]    # "all" -> JSON list of charter ids
    incidents: TreeMap[str, str]      # incident id -> incident JSON
    open_incidents: TreeMap[str, str]  # incident key -> open incident id
    capabilities: TreeMap[str, str]   # capability id -> capability JSON
    claimable: TreeMap[str, u256]     # address (lowercase hex) -> wei owed
    board: TreeMap[str, str]          # "all" -> JSON list of incident ids

    def __init__(self, treasury: str = ""):
        self.owner = gl.message.sender_address
        self.treasury = _to_address(treasury) or gl.message.sender_address
        self.next_charter = u256(1)
        self.next_incident = u256(1)
        self.next_capability = u256(1)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _now(self) -> int:
        """Current time in whole seconds.

        Read from the message itself (`gl.message.raw["datetime"]`), which every
        validator re-executing this call sees identically. `gl.block` does not
        exist and `gl.vm.get_timestamp()` raises on this runtime; the message
        field is the one that works and the right source on the merits.
        """
        try:
            raw = gl.message.raw["datetime"]
        except Exception:
            raw = gl.message.datetime
        raw = str(raw).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return int(datetime.datetime.fromisoformat(raw).timestamp())

    def _sender(self) -> str:
        return gl.message.sender_address.as_hex.lower()

    def _load_charter(self, charter_id: str):
        blob = self.charters.get(str(charter_id).strip().lower())
        return json.loads(blob) if blob is not None else None

    def _load_incident(self, incident_id: str):
        blob = self.incidents.get(str(incident_id).strip())
        return json.loads(blob) if blob is not None else None

    def _load_capability(self, capability_id: str):
        blob = self.capabilities.get(str(capability_id).strip())
        return json.loads(blob) if blob is not None else None

    def _store_charter(self, charter: dict) -> None:
        self.charters[charter["charter_id"]] = json.dumps(charter, sort_keys=True)

    def _store_incident(self, incident: dict) -> None:
        self.incidents[incident["incident_id"]] = json.dumps(incident, sort_keys=True)

    def _store_capability(self, capability: dict) -> None:
        self.capabilities[capability["capability_id"]] = json.dumps(capability, sort_keys=True)

    def _credit(self, addr: str, amount: int) -> None:
        """Owe wei to an address. Never pushes funds — claim() pulls."""
        if int(amount) <= 0:
            return
        key = str(addr).lower()
        self.claimable[key] = u256(int(self.claimable.get(key, 0)) + int(amount))

    def _append_charter_id(self, charter_id: str) -> None:
        raw = self.charter_ids.get("all")
        items = json.loads(raw) if raw else []
        if charter_id not in items:
            items.append(charter_id)
        self.charter_ids["all"] = json.dumps(items)

    def _append_board(self, incident_id: str) -> None:
        raw = self.board.get("all")
        items = json.loads(raw) if raw else []
        if incident_id not in items:
            items.append(incident_id)
        if len(items) > MAX_BOARD:
            items = items[-MAX_BOARD:]
        self.board["all"] = json.dumps(items)

    def _fresh_incident_id(self) -> str:
        n = int(self.next_incident)
        self.next_incident = u256(n + 1)
        return f"i{n}"

    def _fresh_capability_id(self) -> str:
        n = int(self.next_capability)
        self.next_capability = u256(n + 1)
        return f"c{n}"

    # ------------------------------------------------------------------
    # writes: charters
    # ------------------------------------------------------------------

    @gl.public.write
    def register_charter(
        self,
        charter_id: str,
        policy: str,
        evidence_patterns: list,
        target: str,
        action_class: str,
        max_duration_minutes: int,
        bond_amount: int,
        fee_amount: int,
    ) -> str:
        """Register an immutable charter. The sender becomes its author."""
        handle = _guard(lambda: normalize_charter_id(charter_id))
        if self.charters.get(handle) is not None:
            _err("charter id already registered")

        pol = _guard(lambda: normalize_policy(policy))
        pats = _guard(lambda: normalize_patterns(evidence_patterns))
        tgt = _guard(lambda: normalize_target(target))
        ac = _guard(lambda: normalize_action_class(action_class))

        md = int(max_duration_minutes)
        if md < MIN_DURATION_MINUTES or md > MAX_DURATION_MINUTES:
            _err("max duration out of range")
        bond = int(bond_amount)
        fee = int(fee_amount)
        if bond < 0 or fee < 0:
            _err("bond and fee must not be negative")
        if fee > bond:
            _err("fee must not exceed the bond")

        treasury_hex = self.treasury.as_hex.lower()
        chash = charter_digest(handle, pol, pats, tgt, ac, md, bond, fee, treasury_hex)
        charter = {
            "charter_id": handle,
            "author": self._sender(),
            "policy": pol,
            "evidence_patterns": pats,
            "target": tgt,
            "action_class": ac,
            "max_duration_minutes": md,
            # Wei is stored as a decimal string: 0.01 GEN is 1e16 wei, above
            # JavaScript's 2**53 exact-integer range, so a JSON number here
            # would silently lose precision on the way to any JS client.
            "bond_amount": str(bond),
            "fee_amount": str(fee),
            "treasury": treasury_hex,
            "charter_hash": chash,
            "created_at": self._now(),
        }
        self._store_charter(charter)
        self._append_charter_id(handle)
        return handle

    # ------------------------------------------------------------------
    # writes: incident lifecycle
    # ------------------------------------------------------------------

    @gl.public.write.payable
    def open_incident(
        self,
        incident_key: str,
        charter_id: str,
        scope: str,
        duration_minutes: int,
        evidence_urls: list,
    ) -> str:
        """Freeze evidence and open a bonded incident against a charter.

        The attached value must cover the charter's bond plus its disclosed
        fee; anything above that is held as refundable bond too, so no value is
        ever stranded by an overpayment.
        """
        charter = self._load_charter(charter_id)
        if charter is None:
            _err("charter not found")

        key = _guard(lambda: normalize_incident_key(incident_key))
        sc = _guard(lambda: normalize_scope(scope))
        dur = int(duration_minutes)
        if dur < MIN_DURATION_MINUTES or dur > MAX_DURATION_MINUTES:
            _err("duration out of range")
        if dur > int(charter["max_duration_minutes"]):
            _err("duration exceeds the charter maximum")
        urls = _guard(lambda: normalize_evidence_urls(evidence_urls, charter["evidence_patterns"]))

        if self.open_incidents.get(key):
            _err("an incident with this key is already open")

        value = int(gl.message.value)
        required = int(charter["bond_amount"]) + int(charter["fee_amount"])
        if value < required:
            _err("attached value is below the bond plus fee")

        fee = int(charter["fee_amount"])
        digest = incident_digest(
            key,
            charter["charter_hash"],
            charter["target"],
            charter["action_class"],
            sc,
            dur,
        )
        iid = self._fresh_incident_id()
        incident = {
            "incident_id": iid,
            "incident_key": key,
            "charter_id": charter["charter_id"],
            "charter_hash": charter["charter_hash"],
            "target": charter["target"],
            "action_class": charter["action_class"],
            "scope": sc,
            "duration_minutes": dur,
            "evidence_urls": urls,
            "digest": digest,
            "assessor": self._sender(),
            "bond": str(value - fee),
            "fee": str(fee),
            "status": ST_OPEN,
            "decision": "",
            "code": "",
            "supporting_sources": [],
            "clause_ids": [],
            "findings_hash": "",
            "capability_id": "",
            "created_at": self._now(),
            "assessed_at": 0,
        }
        self._store_incident(incident)
        self.open_incidents[key] = iid
        self._append_board(iid)
        return iid

    @gl.public.write
    def assess(self, incident_id: str) -> str:
        """Run the tripwire judgment and settle the bond.

        The assessor and the charter's author may assess immediately; anyone
        else may once the assess delay has passed, so an incident cannot be
        left to rot by a party that stops responding.
        """
        incident = self._load_incident(incident_id)
        if incident is None:
            _err("incident not found")
        if incident["status"] != ST_OPEN:
            _err("incident is not open")

        charter = self._load_charter(incident["charter_id"])
        if charter is None:
            _err("charter not found")

        sender = self._sender()
        authorized = (
            sender == incident["assessor"]
            or sender == charter["author"]
            or self._now() >= int(incident["created_at"]) + ASSESS_DELAY_SECONDS
        )
        if not authorized:
            _err("not authorized to assess yet")

        result = self._judge(
            charter["policy"],
            incident["target"],
            incident["action_class"],
            incident["scope"],
            incident["duration_minutes"],
            incident["evidence_urls"],
        )
        decision = canon_decision(result.get("decision"))

        attached = int(incident["bond"]) + int(incident["fee"])
        settlement = settle(decision, attached, int(incident["fee"]))
        self._credit(incident["assessor"], settlement["assessor"])
        if settlement["treasury"] > 0:
            self._credit(self.treasury.as_hex, settlement["treasury"])

        incident["status"] = ST_ASSESSED
        incident["decision"] = decision
        incident["code"] = str(result.get("code", ""))
        incident["supporting_sources"] = list(result.get("supporting_sources", []))
        incident["clause_ids"] = list(result.get("clause_ids", []))
        incident["findings_hash"] = str(result.get("findings_hash", ""))
        incident["assessed_at"] = self._now()

        if decision == TRIGGER_CONFIRMED:
            incident["capability_id"] = self._issue_capability(incident)
        else:
            incident["capability_id"] = ""

        self._store_incident(incident)
        if self.open_incidents.get(incident["incident_key"]) == incident["incident_id"]:
            self.open_incidents[incident["incident_key"]] = ""
        return decision

    def _issue_capability(self, incident: dict) -> str:
        """Mint a one-shot, expiring capability bound to the incident digest."""
        now = self._now()
        expires_at = now + int(incident["duration_minutes"]) * 60
        cid = self._fresh_capability_id()
        capability = {
            "capability_id": cid,
            "incident_id": incident["incident_id"],
            "charter_id": incident["charter_id"],
            "digest": incident["digest"],
            "target": incident["target"],
            "action_class": incident["action_class"],
            "scope": incident["scope"],
            "duration_minutes": int(incident["duration_minutes"]),
            "issued_at": now,
            "expires_at": expires_at,
            "consumed": False,
            "consumed_by": "",
            "consumed_at": 0,
            "expired": False,
        }
        self._store_capability(capability)
        return cid

    @gl.public.write
    def consume_capability(
        self,
        capability_id: str,
        incident_key: str,
        charter_hash: str,
        target: str,
        action_class: str,
        scope: str,
        duration_minutes: int,
    ) -> str:
        """Consume a capability exactly once, re-deriving its digest first.

        The caller's arguments must reproduce the digest frozen at open time.
        A mismatch is a rejection, not a warning: the whole point of the
        capability is that what a downstream system acts on is byte-for-byte
        what the validators confirmed.
        """
        capability = self._load_capability(capability_id)
        if capability is None:
            _err("capability not found")
        if capability["consumed"]:
            _err("capability already consumed")
        if capability["expired"] or self._now() > int(capability["expires_at"]):
            _err("capability expired")

        incident = self._load_incident(capability["incident_id"])
        if incident is None or incident["status"] != ST_ASSESSED:
            _err("capability incident is not settled")
        if incident["decision"] != TRIGGER_CONFIRMED:
            _err("capability incident was not confirmed")

        digest = incident_digest(
            incident_key, charter_hash, target, action_class, scope, int(duration_minutes)
        )
        if digest != capability["digest"] or digest != incident["digest"]:
            _err("capability digest mismatch")

        capability["consumed"] = True
        capability["consumed_by"] = self._sender()
        capability["consumed_at"] = self._now()
        self._store_capability(capability)
        return capability_id

    @gl.public.write
    def expire_stuck(self, incident_id: str) -> str:
        """Refund an incident nobody assessed after the stuck timeout."""
        incident = self._load_incident(incident_id)
        if incident is None:
            _err("incident not found")
        if incident["status"] != ST_OPEN:
            _err("incident is not open")
        if self._now() < int(incident["created_at"]) + STUCK_TIMEOUT_SECONDS:
            _err("incident is not stuck yet")

        incident["status"] = ST_EXPIRED
        incident["assessed_at"] = self._now()
        self._credit(incident["assessor"], int(incident["bond"]) + int(incident["fee"]))
        self._store_incident(incident)
        if self.open_incidents.get(incident["incident_key"]) == incident["incident_id"]:
            self.open_incidents[incident["incident_key"]] = ""
        return ST_EXPIRED

    @gl.public.write
    def expire_capability(self, capability_id: str) -> str:
        """Mark an unconsumed capability expired once its window has passed."""
        capability = self._load_capability(capability_id)
        if capability is None:
            _err("capability not found")
        if capability["consumed"]:
            _err("capability already consumed")
        if capability["expired"]:
            return capability_id
        if self._now() <= int(capability["expires_at"]):
            _err("capability has not expired")
        capability["expired"] = True
        self._store_capability(capability)
        return capability_id

    # ------------------------------------------------------------------
    # writes: payouts
    # ------------------------------------------------------------------

    @gl.public.write
    def claim(self) -> str:
        """Withdraw everything owed to the sender.

        Pull-only, and zeroed before the transfer, so nothing is pushed to an
        address that cannot receive it and no balance is double-spent. This is
        the only function that moves value out.
        """
        key = self._sender()
        amount = int(self.claimable.get(key, 0))
        if amount <= 0:
            _err("nothing to claim")
        self.claimable[key] = u256(0)
        _Recipient(gl.message.sender_address).emit_transfer(value=u256(amount))
        return str(amount)

    # ------------------------------------------------------------------
    # the one non-deterministic path
    # ------------------------------------------------------------------

    def _judge(self, policy, target, action_class, scope, duration_minutes, urls) -> dict:
        """Run the tripwire judgment under validator consensus.

        One `strict_eq` block, and it is the only non-deterministic call an
        assessment makes. Every validator runs `judge` itself, fetching the
        evidence independently, and each canonicalizes its result through the
        same pure function, so agreement is decided on the verdict class and
        the sorted source/clause sets — never on prose.
        """

        def judge() -> str:
            # Inlined rather than factored: genvm-lint only follows
            # gl.nondet.* calls made directly inside the function handed to the
            # equivalence principle, and rejects the contract when they sit one
            # closure hop away.
            evidence = []
            all_ok = True
            for u in urls:
                try:
                    resp = gl.nondet.web.render(u, mode="text")
                    ev = normalize_evidence(u, 200, resp)
                except Exception:
                    ev = normalize_evidence(u, 0, b"")
                if not ev["ok"]:
                    all_ok = False
                evidence.append(ev)

            digests = [e["digest"] for e in evidence]

            # An unreadable or partially-read evidence set can only ever be
            # INSUFFICIENT. The model is not consulted at all in that case, so
            # a fetch failure is structurally incapable of producing a trigger.
            if not all_ok:
                return comparable_json(
                    build_comparable({"decision": INSUFFICIENT}, digests, [])
                )

            prompt = build_prompt(policy, target, action_class, scope, duration_minutes, evidence)
            raw = gl.nondet.exec_prompt(prompt, response_format="json")
            return comparable_json(build_comparable(_safe_json(raw), digests, []))

        try:
            agreed = gl.eq_principle.strict_eq(judge)
            return _parse_agreed(agreed, _FAIL_CLOSED)
        except Exception:
            # No consensus, or the judgment could not run at all. A technical
            # failure, not a finding: fail closed and never issue.
            return dict(_FAIL_CLOSED)

    # ------------------------------------------------------------------
    # views
    # ------------------------------------------------------------------

    @gl.public.view
    def get_config(self) -> str:
        return json.dumps(
            {
                "owner": self.owner.as_hex,
                "treasury": self.treasury.as_hex,
                "min_duration_minutes": MIN_DURATION_MINUTES,
                "max_duration_minutes": MAX_DURATION_MINUTES,
                "assess_delay_seconds": ASSESS_DELAY_SECONDS,
                "stuck_timeout_seconds": STUCK_TIMEOUT_SECONDS,
                "max_evidence_urls": MAX_EVIDENCE_URLS,
                "next_charter": int(self.next_charter),
                "next_incident": int(self.next_incident),
                "next_capability": int(self.next_capability),
            },
            sort_keys=True,
        )

    @gl.public.view
    def get_charter(self, charter_id: str) -> str:
        return self.charters.get(str(charter_id).strip().lower(), "")

    @gl.public.view
    def get_charter_ids(self) -> str:
        return self.charter_ids.get("all", "[]")

    @gl.public.view
    def get_incident(self, incident_id: str) -> str:
        return self.incidents.get(str(incident_id).strip(), "")

    @gl.public.view
    def get_capability(self, capability_id: str) -> str:
        return self.capabilities.get(str(capability_id).strip(), "")

    @gl.public.view
    def get_board(self, limit: int = 20) -> str:
        raw = self.board.get("all")
        items = json.loads(raw) if raw else []
        n = int(limit)
        if n < 0:
            n = 0
        if n > MAX_BOARD:
            n = MAX_BOARD
        items = items[-n:] if n else []
        out = []
        for iid in reversed(items):
            blob = self.incidents.get(iid)
            if blob is None:
                continue
            inc = json.loads(blob)
            out.append(
                {
                    "incident_id": inc["incident_id"],
                    "charter_id": inc["charter_id"],
                    "status": inc["status"],
                    "decision": inc["decision"],
                    "target": inc["target"],
                    "action_class": inc["action_class"],
                    "created_at": inc["created_at"],
                }
            )
        return json.dumps(out, sort_keys=True)

    @gl.public.view
    def get_claimable(self, addr: str) -> str:
        return str(int(self.claimable.get(_to_account_str(addr), 0)))
