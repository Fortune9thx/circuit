# Status

What is true right now, and what is not yet true. Nothing here is aspirational.

## Scorecard

| Claim                               | State    | Evidence |
| ----------------------------------- | -------- | -------- |
| One contract, one nondet path       | done     | `contracts/Circuit.py`; `_judge` holds the only `gl.eq_principle` call |
| Six-verdict taxonomy, fail closed   | done     | `circuitlib/judgment.py`; short-circuit to `INSUFFICIENT` |
| Decision bound to full evidence     | done     | `normalize_evidence` digests the whole document, not the bounded excerpt; `findings_hash` folds the fingerprints into the compared record |
| Capabilities single-use, expiring, executor-bound | done | `consume_capability` rejects any caller but the charter's frozen executor; `test_unrelated_address_cannot_consume` |
| Escrow conserved, pull-only payouts | done     | `circuitlib/accounting.py`; `claim()` |
| Evidence confined (SSRF + allow-list)| done    | `circuitlib/ssrf.py`; re-checked at fetch |
| Money exact beyond 2**53            | done     | bond/fee serialized as strings |
| Test suite green                    | done     | `113 passed` |
| Lint clean                          | done     | `ruff check .` → All checks passed |
| Schema validates                    | done     | `genvm-lint check` → ok, 14 methods (7 view / 7 write) |
| Bundle reproducible                 | done     | `build_bundle.py`; CI diff gate |
| Interface builds                    | done     | `npm run typecheck`, `npm run build` |
| Deployed to Studio Dev              | done     | `0x7689bE9D97533cA981EC5c2782dE01326b37A8D1` |
| Live schema verified on chain       | done     | `gen_getContractSchema` → 14 methods (`register_charter` now takes `executor`); `get_config` returns the expected constants |
| Live non-payable write verified     | done     | `register_charter` accepted; `_now()` read on chain |
| Live payable + nondet flow verified  | done     | `open_incident` (value), `assess` → `TRIGGER_CONFIRMED`/`NOT_CONFIRMED`, `consume_capability`, `claim` all on chain |
| Live executor authorization verified | done     | an unrelated caller's `consume_capability` reverted; the executor's succeeded |
| Deployed frontend URL               | done     | https://circuit-rose-eta.vercel.app |
| Frontend write path verified        | done     | live bundle carries the built-in dev chain + fee preset; see below |
| Pushed to GitHub                    | done     | https://github.com/Fortune9thx/circuit; CI green |

## Deployment

- **Contract:** `0x7689bE9D97533cA981EC5c2782dE01326b37A8D1` on GenLayer Studio
  Dev, chain `61997`.
- **Deploy tx:** `0x47976bbdfbf2ab7dc55dc046f88c61ba6e309f1aed43d07726ec72cd03700a39`,
  result `ACCEPTED`.
- **Live read:** `get_config` returns `assess_delay_seconds=1800`,
  `stuck_timeout_seconds=86400`, `min_duration_minutes=5`,
  `max_duration_minutes=120`, `max_evidence_urls=5`, owner/treasury at the
  deployer address. `gen_getContractSchema` lists `register_charter` with its
  `executor` parameter.
- **Live executor authorization (throwaway signer):** `register_charter` with
  `executor=0x1034…` tx
  `0xb1eeedbe9cfbb678bd85543e7a74ef8b991c7f6cfd1c4c1562d633deacf9be83`;
  `open_incident` tx
  `0x12b5ed6fef22fbaf54b755bc7fbd058e8c557276b399e27f206711a1eff8312a`;
  `assess` → `TRIGGER_CONFIRMED`, capability `c1` bound to that executor. An
  unrelated account (`0xc6e6…`, via the CLI) calling `consume_capability` was
  rejected (`FINISHED_WITH_ERROR`) and left the capability unconsumed; the
  executor's `consume_capability` tx
  `0x8a17db431eb99391992d72e2b395e5b03cfbc74c8c294e5071b8667bb1d695c7`
  succeeded (`consumed: true`, `consumed_by` = executor).
- **Interface:** https://circuit-rose-eta.vercel.app — contract address embedded
  and verified in the deployed bundle; the bundle also carries the built-in dev
  chain definition and the write fee preset (see "Frontend write path").
- **Repository:** https://github.com/Fortune9thx/circuit.
- **CI:** the contract job (ruff, pytest, bundle reproducibility, `genvm-lint
  lint`) and the frontend job (typecheck, build) both pass on `main`.

## Live-proven vs test-only

- **Observed on chain:** deploy, `gen_getContractSchema`, `get_config`,
  `register_charter` (with and without `executor`), `open_incident` with
  `msg.value`, `assess` under real consensus (both a `NOT_CONFIRMED` refund and a
  `TRIGGER_CONFIRMED` that minted a capability), `consume_capability`, and
  `claim`. Capability authorization is proven on chain both ways: an unrelated
  caller's consumption reverts, and the frozen executor's succeeds.
- **Not yet observed on chain:** `expire_capability`, `expire_stuck`,
  `set_owner`/`set_treasury`, and the `INSUFFICIENT`/`CONFLICTING`/`STALE`/
  `TAMPERED` verdicts. These are covered by the test suite only and are not
  claimed as live.
- **`expire_stuck` / `expire_capability` windows** are 24h by design, so they
  cannot be exercised against a fresh incident without waiting.

## Frontend write path

Two defects in the interface's write path were found by driving the deployed
bundle, and both are fixed and redeployed:

- The chain object was hand-rolled and lacked `defaultNumberOfInitialValidators`,
  so `writeContract` threw `Cannot convert undefined to a BigInt` before sending.
  The clients now spread the library's own `studioDevnet` chain and only override
  the RPC endpoint.
- Writes carried no fee preset and were rejected with `FeeValueMustBeNonZero(1)`.
  The client now attaches the same fee distribution and non-zero deposit that a
  successful deploy on this network uses.

## Studio Dev determinism note

Studio Dev's nondeterministic model intermittently answers with malformed JSON,
which makes `exec_prompt(..., response_format="json")` raise; the round then ends
`MAJORITY_DISAGREE` / `FINISHED_WITH_ERROR` and the `assess` transaction changes
no state, leaving the incident `OPEN`. This is a property of the preview network,
not of the contract. The remedy is to call `assess` again; a confirming
assessment can take several attempts on this network, and only a round that
reaches consensus changes state. The interface surfaces the settled decision once
a round finalizes.

Studio Dev is a preview network whose state resets. If the schema stops
resolving, treat CIRCUIT as undeployed until it is redeployed — the interface
does this on its own.
