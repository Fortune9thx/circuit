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
| Deployed to Studio Dev             | done     | `0x9D1F3a9e0CF3679dc631fd00D39F10e158Bbf923` |
| Live schema verified on chain      | done     | `gen_getContractSchema` → 14 methods; `get_config` returns the expected constants |
| Deployed frontend URL              | **not yet** | pending deployment |
| Pushed to GitHub                   | **not yet** | pending |

## Deployment

- **Contract:** `0x9D1F3a9e0CF3679dc631fd00D39F10e158Bbf923` on GenLayer Studio
  Dev, chain `61997`.
- **Deploy tx:** `0x20652d91afe17e9c55e438d7661cbf6bceaef1c59abc7e5b5a9b1966ffb36bdc`,
  status `ACCEPTED`, validators `AGREE`.
- **Live read:** `get_config` returns
  `assess_delay_seconds=1800`, `stuck_timeout_seconds=86400`,
  `min_duration_minutes=5`, `max_duration_minutes=120`, `max_evidence_urls=5`,
  owner/treasury at the deployer address.
- **Interface:** _pending_.

## Not yet done

1. Deploy the frontend, then link it from this file.
2. Create the repository and push.

Studio Dev is a preview network whose state resets. If the schema stops
resolving, treat CIRCUIT as undeployed until it is redeployed — the interface
does this on its own.
