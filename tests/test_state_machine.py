"""The contract's state machine, driven through the fake GenVM.

Every test exercises a real branch: consensus agreement and disagreement, the
fail-closed paths, the bond arithmetic, the one-shot capability, the escape
hatches, and the pull-only payout.
"""

import datetime
import json

import Circuit as circuit_module
import pytest
from circuitlib.canonicalize import incident_digest
from fake_genlayer import UserError

Address = circuit_module.Address

OWNER = "0x" + "aa" * 20
ASSESSOR = "0x" + "bb" * 20
TREASURY = "0x" + "cc" * 20
OTHER = "0x" + "dd" * 20
EXECUTOR = "0x" + "ee" * 20

T0 = 1_700_000_000
EVIDENCE_URL = "https://a.example.com/report"
BOND = 1000
FEE = 100
SCOPE = "prod-west"


def set_time(gl, ts):
    dt = datetime.datetime.fromtimestamp(ts, datetime.UTC)
    gl.message.raw = {"datetime": dt.isoformat()}


def set_sender(gl, addr):
    gl.message.sender_address = Address(addr)


@pytest.fixture
def app(gl):
    set_time(gl, T0)
    set_sender(gl, OWNER)
    gl.message.value = 0
    return circuit_module.Circuit(TREASURY)


def register(app, gl, author=OWNER, **over):
    set_sender(gl, author)
    kwargs = {
        "charter_id": "main",
        "policy": "trip when the service reports an outage",
        "evidence_patterns": ["*.example.com"],
        "target": "payments",
        "action_class": "deploy",
        "max_duration_minutes": 60,
        "bond_amount": BOND,
        "fee_amount": FEE,
    }
    kwargs.update(over)
    return app.register_charter(**kwargs)


def open_incident(app, gl, key="inc-1", assessor=ASSESSOR, value=BOND + FEE, **over):
    set_sender(gl, assessor)
    gl.message.value = value
    return app.open_incident(
        key, "main", over.get("scope", SCOPE), 30, over.get("urls", [EVIDENCE_URL])
    )


def agree(nondet, decision, sources=(0,)):
    answer = {"decision": decision, "supporting_sources": list(sources)}
    nondet.leader_answers = [json.dumps(answer)]


# --- charters --------------------------------------------------------------


def test_register_charter_and_view(app, gl):
    assert register(app, gl) == "main"
    charter = json.loads(app.get_charter("main"))
    assert charter["charter_id"] == "main"
    assert charter["author"] == OWNER
    # With no executor supplied, the author is the executor.
    assert charter["executor"] == OWNER
    assert charter["evidence_patterns"] == ["*.example.com"]
    assert len(charter["charter_hash"]) == 64


def test_register_binds_explicit_executor(app, gl):
    register(app, gl, executor=EXECUTOR)
    assert json.loads(app.get_charter("main"))["executor"] == EXECUTOR


def test_register_rejects_bad_executor(app, gl):
    with pytest.raises(UserError):
        register(app, gl, executor="not-an-address")


def test_register_rejects_duplicate(app, gl):
    register(app, gl)
    with pytest.raises(UserError):
        register(app, gl)


def test_register_rejects_bad_pattern(app, gl):
    with pytest.raises(UserError):
        register(app, gl, evidence_patterns=["not a host"])


def test_register_rejects_bad_duration(app, gl):
    with pytest.raises(UserError):
        register(app, gl, max_duration_minutes=1)


# --- opening incidents -----------------------------------------------------


def test_open_incident_freezes_digest(app, gl):
    register(app, gl)
    iid = open_incident(app, gl)
    inc = json.loads(app.get_incident(iid))
    assert inc["status"] == "OPEN"
    assert inc["target"] == "payments"
    chash = json.loads(app.get_charter("main"))["charter_hash"]
    assert inc["digest"] == incident_digest("inc-1", chash, "payments", "deploy", SCOPE, 30)


def test_open_rejects_underpayment(app, gl):
    register(app, gl)
    with pytest.raises(UserError):
        open_incident(app, gl, value=BOND + FEE - 1)


def test_open_rejects_disallowed_host(app, gl):
    register(app, gl)
    with pytest.raises(UserError):
        open_incident(app, gl, urls=["https://evil.net/x"])


def test_open_rejects_duplicate_key(app, gl):
    register(app, gl)
    open_incident(app, gl)
    with pytest.raises(UserError):
        open_incident(app, gl)


def test_open_rejects_duration_over_charter_max(app, gl):
    register(app, gl, max_duration_minutes=20)
    set_sender(gl, ASSESSOR)
    gl.message.value = BOND + FEE
    with pytest.raises(UserError):
        app.open_incident("inc-1", "main", SCOPE, 30, [EVIDENCE_URL])


# --- assess: the confirming path -------------------------------------------


def test_assess_confirmed_issues_capability_and_settles(app, gl, nondet):
    register(app, gl)
    iid = open_incident(app, gl)
    nondet.web[EVIDENCE_URL] = (200, "service status: outage")
    agree(nondet, "TRIGGER_CONFIRMED")
    set_sender(gl, ASSESSOR)

    assert app.assess(iid) == "TRIGGER_CONFIRMED"

    inc = json.loads(app.get_incident(iid))
    assert inc["status"] == "ASSESSED"
    assert inc["capability_id"]
    assert int(app.get_claimable(ASSESSOR)) == BOND
    assert int(app.get_claimable(TREASURY)) == FEE

    cap = json.loads(app.get_capability(inc["capability_id"]))
    assert cap["digest"] == inc["digest"]
    assert cap["consumed"] is False


# --- assess: the fail-closed paths -----------------------------------------


def test_assess_not_confirmed_refunds_in_full(app, gl, nondet):
    register(app, gl)
    iid = open_incident(app, gl)
    nondet.web[EVIDENCE_URL] = (200, "service status: healthy")
    agree(nondet, "NOT_CONFIRMED", sources=())
    set_sender(gl, ASSESSOR)

    assert app.assess(iid) == "NOT_CONFIRMED"
    inc = json.loads(app.get_incident(iid))
    assert inc["capability_id"] == ""
    assert int(app.get_claimable(ASSESSOR)) == BOND + FEE
    assert int(app.get_claimable(TREASURY)) == 0


def test_assess_divergent_evidence_fails_closed(app, gl, nondet):
    register(app, gl)
    iid = open_incident(app, gl)
    # Leader and validator fetch different bytes for the same URL.
    nondet.web[EVIDENCE_URL] = [(200, "outage"), (200, "healthy")]
    agree(nondet, "TRIGGER_CONFIRMED")
    set_sender(gl, ASSESSOR)

    assert app.assess(iid) == "INSUFFICIENT"
    assert json.loads(app.get_incident(iid))["capability_id"] == ""
    assert int(app.get_claimable(ASSESSOR)) == BOND + FEE


def test_assess_fetch_failure_is_insufficient(app, gl, nondet):
    register(app, gl)
    iid = open_incident(app, gl)
    # No web entry: render raises inside both passes.
    agree(nondet, "TRIGGER_CONFIRMED")
    set_sender(gl, ASSESSOR)

    assert app.assess(iid) == "INSUFFICIENT"
    assert int(app.get_claimable(ASSESSOR)) == BOND + FEE
    assert nondet.prompts == []  # the model is never consulted


def test_assess_consensus_exception_fails_closed(app, gl, nondet):
    register(app, gl)
    iid = open_incident(app, gl)
    nondet.web[EVIDENCE_URL] = (200, "outage")
    agree(nondet, "TRIGGER_CONFIRMED")
    nondet.force_exception = True
    set_sender(gl, ASSESSOR)

    assert app.assess(iid) == "INSUFFICIENT"
    assert json.loads(app.get_incident(iid))["capability_id"] == ""


def test_trigger_without_sources_is_downgraded(app, gl, nondet):
    register(app, gl)
    iid = open_incident(app, gl)
    nondet.web[EVIDENCE_URL] = (200, "outage")
    nondet.leader_answers = [json.dumps({"decision": "TRIGGER_CONFIRMED"})]
    set_sender(gl, ASSESSOR)

    assert app.assess(iid) == "INSUFFICIENT"
    assert json.loads(app.get_incident(iid))["capability_id"] == ""


def test_assess_twice_rejected(app, gl, nondet):
    register(app, gl)
    iid = open_incident(app, gl)
    nondet.web[EVIDENCE_URL] = (200, "outage")
    agree(nondet, "NOT_CONFIRMED", sources=())
    set_sender(gl, ASSESSOR)
    app.assess(iid)
    with pytest.raises(UserError):
        app.assess(iid)


# --- authorization ---------------------------------------------------------


def test_stranger_cannot_assess_before_delay(app, gl, nondet):
    register(app, gl)
    iid = open_incident(app, gl)
    nondet.web[EVIDENCE_URL] = (200, "outage")
    agree(nondet, "NOT_CONFIRMED", sources=())
    set_sender(gl, OTHER)
    set_time(gl, T0)
    with pytest.raises(UserError):
        app.assess(iid)


def test_stranger_can_assess_after_delay(app, gl, nondet):
    register(app, gl)
    iid = open_incident(app, gl)
    nondet.web[EVIDENCE_URL] = (200, "outage")
    agree(nondet, "NOT_CONFIRMED", sources=())
    set_sender(gl, OTHER)
    set_time(gl, T0 + 1801)
    assert app.assess(iid) == "NOT_CONFIRMED"


# --- capability lifecycle --------------------------------------------------


def _confirmed(app, gl, nondet):
    register(app, gl, executor=EXECUTOR)
    iid = open_incident(app, gl)
    nondet.web[EVIDENCE_URL] = (200, "outage")
    agree(nondet, "TRIGGER_CONFIRMED")
    set_sender(gl, ASSESSOR)
    app.assess(iid)
    inc = json.loads(app.get_incident(iid))
    chash = json.loads(app.get_charter("main"))["charter_hash"]
    return inc["capability_id"], chash


def test_capability_carries_its_executor(app, gl, nondet):
    cap_id, _ = _confirmed(app, gl, nondet)
    assert json.loads(app.get_capability(cap_id))["executor"] == EXECUTOR


def test_executor_consumes_capability_once(app, gl, nondet):
    cap_id, chash = _confirmed(app, gl, nondet)
    set_sender(gl, EXECUTOR)
    assert app.consume_capability(cap_id, "inc-1", chash, "payments", "deploy", SCOPE, 30) == cap_id
    assert json.loads(app.get_capability(cap_id))["consumed"] is True
    with pytest.raises(UserError):
        app.consume_capability(cap_id, "inc-1", chash, "payments", "deploy", SCOPE, 30)


def test_unrelated_address_cannot_consume(app, gl, nondet):
    cap_id, chash = _confirmed(app, gl, nondet)
    # A stranger with the exact right arguments still cannot spend the
    # capability: consumption is bound to the charter's executor.
    set_sender(gl, OTHER)
    with pytest.raises(UserError):
        app.consume_capability(cap_id, "inc-1", chash, "payments", "deploy", SCOPE, 30)
    cap = json.loads(app.get_capability(cap_id))
    assert cap["consumed"] is False
    assert cap["executor"] == EXECUTOR


def test_consume_capability_digest_mismatch_rejected(app, gl, nondet):
    cap_id, chash = _confirmed(app, gl, nondet)
    set_sender(gl, EXECUTOR)
    with pytest.raises(UserError):
        app.consume_capability(cap_id, "inc-1", chash, "payments", "deploy", "prod-east", 30)


def test_capability_expires(app, gl, nondet):
    cap_id, chash = _confirmed(app, gl, nondet)
    set_sender(gl, EXECUTOR)
    set_time(gl, T0 + 30 * 60 + 10)
    with pytest.raises(UserError):
        app.consume_capability(cap_id, "inc-1", chash, "payments", "deploy", SCOPE, 30)
    app.expire_capability(cap_id)
    assert json.loads(app.get_capability(cap_id))["expired"] is True


# --- escape hatches --------------------------------------------------------


def test_expire_stuck_refunds_after_timeout(app, gl):
    register(app, gl)
    iid = open_incident(app, gl)
    with pytest.raises(UserError):
        app.expire_stuck(iid)
    set_time(gl, T0 + 86401)
    assert app.expire_stuck(iid) == "EXPIRED"
    assert int(app.get_claimable(ASSESSOR)) == BOND + FEE


# --- payouts ---------------------------------------------------------------


def test_claim_is_pull_only_and_once(app, gl, nondet, chain):
    register(app, gl)
    iid = open_incident(app, gl)
    nondet.web[EVIDENCE_URL] = (200, "outage")
    agree(nondet, "TRIGGER_CONFIRMED")
    set_sender(gl, ASSESSOR)
    app.assess(iid)

    assert app.claim() == str(BOND)
    assert chain.sent == [(ASSESSOR, BOND)]
    with pytest.raises(UserError):
        app.claim()


def test_charter_and_board_indexes(app, gl):
    register(app, gl)
    assert json.loads(app.get_charter_ids()) == ["main"]
    iid = open_incident(app, gl)
    board = json.loads(app.get_board(10))
    assert board and board[0]["incident_id"] == iid
    assert board[0]["status"] == "OPEN"


def test_overpayment_is_refundable(app, gl, nondet):
    register(app, gl)
    iid = open_incident(app, gl, value=BOND + FEE + 50)
    nondet.web[EVIDENCE_URL] = (200, "healthy")
    agree(nondet, "NOT_CONFIRMED", sources=())
    set_sender(gl, ASSESSOR)
    app.assess(iid)
    # The whole attached value comes back on a non-confirming verdict.
    assert int(app.get_claimable(ASSESSOR)) == BOND + FEE + 50
