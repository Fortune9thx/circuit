# Status

What is true right now, and what is not yet true. Nothing here is aspirational.

## Scorecard

| Claim                               | State    | Evidence |
| ----------------------------------- | -------- | -------- |
| One contract, one nondet path       | done     | `contracts/Circuit.py`; `_judge` holds the only `gl.eq_principle` call |
| Six-verdict taxonomy, fail closed   | done     | `circuitlib/judgment.py`; short-circuit to `INSUFFICIENT` |
| Decision bound to full evidence     | done     | `normalize_evidence` digests the whole document, not the bounded excerpt; `findings_hash` folds the fingerprints into the compared record |
| Capabilities single-use + expiring  | done     | `consume_capability`, `expire_capability` |
| Escrow conserved, pull-only payouts | done     | `circuitlib/accounting.py`; `claim()` |
| Evidence confined (SSRF + allow-list)| done    | `circuitlib/ssrf.py`; re-checked at fetch |
| Money exact beyond 2**53            | done     | bond/fee serialized as strings |
| Test suite green                    | done     | `109 passed` |
| Lint clean                          | done     | `ruff check .` → All checks passed |
| Schema validates                    | done     | `genvm-lint check` → ok, 14 methods (7 view / 7 write) |
| Bundle reproducible                 | done     | `build_bundle.py`; CI diff gate |
| Interface builds                    | done     | `npm run typecheck`, `npm run build` |
| Deployed to Studio Dev              | done     | `0xBb48Fa9a0aAe40C03A6F792b209aA761054F1250` |
| Live schema verified on chain       | done     | `gen_getContractSchema` → 14 methods; `get_config` returns the expected constants |
| Live non-payable write verified     | done     | `register_charter` accepted; `_now()` read on chain |
| Live payable + nondet flow verified  | done     | `open_incident` (value), `assess` → `TRIGGER_CONFIRMED`/`NOT_CONFIRMED`, `consume_capability`, `claim` all on chain |
| Deployed frontend URL               | done     | https://circuit-rose-eta.vercel.app |
| Frontend write path verified        | done     | live bundle carries the built-in dev chain + fee preset; see below |
| Pushed to GitHub                    | done     | https://github.com/Fortune9thx/circuit; CI green |

## Deployment

- **Contract:** `0xBb48Fa9a0aAe40C03A6F792b209aA761054F1250` on GenLayer Studio
  Dev, chain `61997`.
- **Deploy tx:** `0xb6ec433233ad0eb6ac94ac57b2f2f9bc05933d85d3a2f2f254bd82a732dc8989ed`,
  result `MAJORITY_AGREE`, leader `execution_result: SUCCESS`.
- **Live read:** `get_config` returns `assess_delay_seconds=1800`,
  `stuck_timeout_seconds=86400`, `min_duration_minutes=5`,
  `max_duration_minutes=120`, `max_evidence_urls=5`, owner/treasury at the
  deployer address.
- **Live write:** `register_charter` tx
  `0xcb6bb0a6e21f43fdb72c759add10b2ce38f1c143938aaffe63c87e6542c53731`, accepted;
  `get_charter circuit-smoke` reads back the stored charter including
  `created_at`, so `gl.message.raw["datetime"]` is probed on this pinned hash.
- **Live full loop (throwaway signer):** `open_incident` tx
  `0x29cf47f7f985a5983913e0c444ef92c72421e1938b8727dd5f514b120ba37abd` (paid
  `bond + fee`), `assess` settled `i1`/`i2` as `NOT_CONFIRMED` and `i3` as
  `TRIGGER_CONFIRMED` (capability `c1`), `consume_capability` tx
  `0xbd6cb30f8ded44ed50f0569d377d4b2278afaedb3357ae59253c15a3d93b5bd8`, and
  `claim` paid the refund/payout.
- **Interface:** https://circuit-rose-eta.vercel.app — contract address embedded
  and verified in the deployed bundle; the bundle also carries the built-in dev
  chain definition and the write fee preset (see "Frontend write path").
- **Repository:** https://github.com/Fortune9thx/circuit.
- **CI:** the contract job (ruff, pytest, bundle reproducibility, `genvm-lint
  lint`) and the frontend job (typecheck, build) both pass on `main`.

## Live-proven vs test-only

- **Observed on chain:** deploy, `gen_getContractSchema`, `get_config`,
  `register_charter`, `open_incident` with `msg.value`, `assess` under real
  consensus (both a `NOT_CONFIRMED` refund and a `TRIGGER_CONFIRMED` that minted
  a capability), `consume_capability`, `get_capability`, and `claim`.
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
not of the contract. The remedy is to call `assess` again; the second attempt
settled normally. The interface surfaces the settled decision once a round
finalizes.

Studio Dev is a preview network whose state resets. If the schema stops
resolving, treat CIRCUIT as undeployed until it is redeployed — the interface
does this on its own.
