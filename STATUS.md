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
| Live payable flow verified          | **not yet** | needs a genlayer-js signer; see below |
| Deployed frontend URL               | done     | https://circuit-rose-eta.vercel.app |
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
- **Interface:** https://circuit-rose-eta.vercel.app — built with the contract
  address embedded and verified present in the deployed bundle; deep links
  resolve.
- **Repository:** https://github.com/Fortune9thx/circuit.
- **CI:** the contract job (ruff, pytest, bundle reproducibility, `genvm-lint
  lint`) and the frontend job (typecheck, build) both pass on `main`.

## Live-proven vs test-only

- **Observed on chain:** deploy, `gen_getContractSchema`, `get_config`,
  `register_charter` (a non-payable write that exercises `_now`), `get_charter`,
  `get_charter_ids`.
- **Not yet observed on chain:** the payable path (`open_incident` with
  `msg.value`), the nondet `assess` under real consensus, capability
  issue/consume/expire, and `claim`. The `genlayer` CLI exposes no flag to attach
  `msg.value`, so the payable flow needs a genlayer-js signer. Until that runs,
  those behaviours are covered by the test suite only and are not claimed as
  live.

Studio Dev is a preview network whose state resets. If the schema stops
resolving, treat CIRCUIT as undeployed until it is redeployed — the interface
does this on its own.
