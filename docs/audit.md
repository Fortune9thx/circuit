# Audit

This is a safety argument, not a proof. Each invariant below names where it is
enforced and which test exercises it. Anything a reader can falsify against the
deployed source is a finding.

## Invariants

### 1. Exactly one non-deterministic call per assessment

Enforced: `_judge` holds the single `gl.eq_principle.strict_eq(judge)`; the fetch
loop is inlined into `judge` so `genvm-lint` can see every `gl.nondet.*` call
reachable from the equivalence block. `genvm-lint check` passes.
Tests: `test_state_machine.py` (every assess path); the linter gate in CI.

### 2. Fail closed

Enforced: any exception, no-consensus result, or unparseable agreement returns
`_FAIL_CLOSED` (`INSUFFICIENT`). If any evidence URL fails to fetch or parse the
verdict short-circuits to `INSUFFICIENT` and the model is never consulted.
Tests: `test_assess_fetch_failure_is_insufficient` (also asserts
`nondet.prompts == []`), `test_assess_consensus_exception_fails_closed`,
`test_assess_divergent_evidence_fails_closed`.

### 3. A closed decision taxonomy

Enforced: `canon_decision` strips non-letters and maps to one of six verdicts;
anything unrecognized becomes `INSUFFICIENT`. A trigger with no cited sources is
downgraded.
Tests: `test_judgment_pure.py`, `test_trigger_without_sources_is_downgraded`.

### 4. Capabilities are single-use, expiring, digest-bound, and executor-bound

Enforced: `consume_capability` requires the caller to be the capability's
`executor` — the address frozen into the charter at registration — and rejects
any other caller before it checks anything else. It then re-derives the digest
from the caller's arguments and rejects on any mismatch with either the stored
capability or the incident; it rejects a consumed or expired capability.
Tests: `test_executor_consumes_capability_once`,
`test_unrelated_address_cannot_consume` (a stranger with the exact right
arguments is still rejected and the capability stays unconsumed),
`test_capability_carries_its_executor`,
`test_consume_capability_digest_mismatch_rejected`, `test_capability_expires`.

### 5. Escrow is conserved

Enforced: `settle` splits `attached` into `assessor` + `treasury` with no value
created or destroyed; the contract credits exactly those amounts.
Tests: `test_accounting.py::test_conservation_holds` (across edge cases),
`test_assess_confirmed_issues_capability_and_settles`,
`test_assess_not_confirmed_refunds_in_full`, `test_overpayment_is_refundable`.

### 6. Payouts are pull-only

Enforced: `claim()` zeroes the balance before transferring and is the only
function that moves value out.
Tests: `test_claim_is_pull_only_and_once`.

### 7. Every GEN-holding status has an escape hatch

Enforced: `expire_stuck` refunds an unassessed incident after the stuck timeout;
a non-confirming verdict refunds in full at assessment; `expire_capability`
retires a lapsed capability.
Tests: `test_expire_stuck_refunds_after_timeout`, the refund tests above.

### 8. Evidence is confined

Enforced: `normalize_evidence_urls` requires https, a default port, a public
domain, no credentials, and a match against a host pattern frozen in the charter.
The pattern check is applied at open time and the URL is re-checked at fetch
time.
Tests: `test_ssrf.py`, `test_open_rejects_disallowed_host`.

### 9. Inputs are bounded

Enforced: length caps in `canonicalize.py` (policy ≤ 4000, scope ≤ 500,
target ≤ 300; charter id and incident key patterns), a maximum of five evidence
URLs, at most 32 patterns.
Tests: `test_canonicalize.py`, `test_ssrf.py`.

### 10. Prompt injection is blunted

Enforced: `strip_html` removes script/style and other non-content tags;
fence-like runs of `=` are collapsed so quoted text cannot forge a fence;
backticks and control characters are stripped; the hostile-data note is stated
after the evidence.
Tests: `test_judgment_pure.py`.

### 11. Assessment authorization

Enforced: `assess` allows the assessor and the charter author immediately, and
anyone else only after the assess delay.
Tests: `test_stranger_cannot_assess_before_delay`,
`test_stranger_can_assess_after_delay`.

### 12. Money is exact

Enforced: bond and fee are serialized into record JSON as decimal strings, so a
JS client never round-trips a value above `2**53` through a float.
Tests: `test_bundle` / contract tests carry exact integers; the frontend parses
with `BigInt`.

### 13. The deployable matches the source

Enforced: `build_bundle.py` regenerates deterministically and CI diffs the
result.
Tests: `test_bundle.py`.

## Known limits

- The verdict is only as good as the evidence hosts a charter allows. A charter
  authored to trust a compromised host can be fooled; the protocol bounds this
  to hosts named in advance, not to truth.
- `STALE` and `TAMPERED` are model judgments over the fetched text; they are
  corroborated by validators re-fetching, but they are not a cryptographic proof
  of provenance.
- Studio Dev state can be reset. The interface treats an unconfirmed deployment
  as "not live" rather than assuming persistence.
