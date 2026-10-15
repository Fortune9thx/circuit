# Status

What is true right now, and what is not yet true. Nothing here is aspirational.

## Scorecard

| Claim                              | State    | Evidence |
| ---------------------------------- | -------- | -------- |
| One contract, one nondet path      | done     | `contracts/Circuit.py`; `_judge` holds the only `gl.eq_principle` call |
| Six-verdict taxonomy, fail closed  | done     | `circuitlib/judgment.py`; short-circuit to `INSUFFICIENT` |
| Capabilities single-use + expiring | done     | `consume_capability`, `expire_capability` |
| Escrow conserved, pull-only payouts| done     | `circuitlib/accounting.py`; `claim()` |
| Evidence confined (SSRF + allow-list)| done   | `circuitlib/ssrf.py`; re-checked at fetch |
| Money exact beyond 2**53           | done     | bond/fee serialized as strings |
| Test suite green                   | done     | `107 passed` |
| Lint clean                         | done     | `ruff check .` → All checks passed |
| Schema validates                   | done     | `genvm-lint check` → ok, 14 methods (7 view / 7 write) |
| Bundle reproducible                | done     | `build_bundle.py`; CI diff gate |
| Interface builds                   | done     | `npm run typecheck`, `npm run build` |
| Deployed to Studio Dev             | **not yet** | pending |
| Live schema verified on chain      | **not yet** | pending deployment |
| Deployed frontend URL              | **not yet** | pending deployment |
| Pushed to GitHub                   | **not yet** | pending |

## Not yet done

1. Deploy `contracts/build/Circuit.bundled.py` to Studio Dev and record the
   address.
2. Confirm the live schema and wire `VITE_CONTRACT_ADDRESS`.
3. Deploy the frontend, then link it from this file.
4. Create the repository and push.

Until items 1–4 are done, treat CIRCUIT as audited source, not as a live
deployment.
