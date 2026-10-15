# Steward notes

What to check to trust this deployment without taking the README's word for it.
Each item is falsifiable from the repository and the chain.

## 1. The source is the deployed source

```sh
python contracts/build_bundle.py
git diff --exit-code -- contracts/build/Circuit.bundled.py
```

No diff means the committed bundle is exactly what the bundler emits from
`Circuit.py` and `circuitlib/`.

```sh
genlayer.cmd code 0x<address> | diff - contracts/build/Circuit.bundled.py
```

The chain's source should match the bundle.

## 2. One nondeterministic path

```sh
genvm-lint check contracts/build/Circuit.bundled.py
```

Read `_judge` in the bundle: it should contain the only `gl.eq_principle` call,
and every `gl.nondet.*` call should be directly inside the `judge` closure.

## 3. Fail-closed is real

```sh
pytest -q
```

Then read `test_assess_fetch_failure_is_insufficient` — it asserts the model is
never consulted when evidence does not read cleanly.

## 4. Escrow conserves

Read `circuitlib/accounting.py` and `test_accounting.py`. `settle` must split
`attached` into `assessor` + `treasury` with nothing created. `claim()` in the
contract should zero the balance before transferring, and be the only transfer.

## 5. Evidence is confined

Read `circuitlib/ssrf.py`. Confirm https-only, default-port-only, no IP
literals, no credentials, public domains only, and that a URL must match a host
pattern frozen in the charter. Confirm the same check runs at fetch time inside
`_judge`.

## 6. The interface fails closed

Read `frontend/src/lib/tx.ts`. Success is an allow-list; a missing or
unrecognized field is failure. A write that executed but reached no consensus
must not read as success. Read `frontend/src/lib/chain.ts` to confirm liveness
uses `gen_getContractSchema`, not `eth_getCode`.

## 7. Live schema

```sh
genlayer.cmd schema 0x<address>
```

Expect 14 methods: 7 views and 7 writes, one constructor parameter.

## 8. Try to make it issue a capability it should not

- Open an incident against a charter whose evidence host is a healthy status
  page. It must settle `NOT_CONFIRMED` and refund.
- Point an evidence URL outside the charter's allow-list. It must be rejected
  before any validator sees it.
- Consume a capability with any field changed. It must be rejected.
- Assess the same incident twice. The second call must be rejected.

## 9. Agreement is on content, not just verdicts

Read `normalize_evidence` in `circuitlib/judgment.py`. The `digest` it returns is
taken over the **whole** stripped document, not the `MAX_FETCH_CHARS` excerpt the
model is shown, and `build_comparable` echoes those digests and folds them into
`findings_hash`. So two validators agree only if they fetched the same bytes —
and if they had agreed on the bounded excerpt alone, a divergence past the cutoff
would have been invisible to consensus. `test_digest_covers_content_past_the_excerpt_cap`
pins this: two documents that differ only after the cutoff keep an identical
prompt excerpt but must have different digests.

## 10. Consensus is exercised under a fake runtime

`strict_eq` and the one-nondet-path rule are checked structurally by
`genvm-lint`, and the judgement pipeline is driven end to end in `pytest`
through `tests/fake_genlayer.py`, which models the leader/validator split. There
is no `gltest` fixture in this repository, so the suite does not exercise the
real runner; `genvm-lint check` and a live deploy are what stand in for that.
