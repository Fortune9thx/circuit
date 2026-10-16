# CIRCUIT

A temporary circuit-breaker protocol on GenLayer.

A **charter** is a written tripwire: a policy, the evidence hosts it may be
judged against, a target, an action class, and a bond/fee schedule. An assessor
posts a bond to open an **incident** and freezes the evidence URLs and a
canonical digest. Validators then independently fetch that evidence and decide,
under the Equivalence Principle, exactly one of six discrete verdicts.

Only `TRIGGER_CONFIRMED` issues a **capability** — a single-use, expiring
artifact whose digest is recomputed at freeze, at issuance, and at consumption;
any mismatch rejects. A capability can be consumed only by its **executor**, the
address frozen into the charter at registration. Every other verdict, including
every technical failure, refunds the bond in full and issues nothing.

The whole protocol is one contract. Deployable on GenLayer Studio Dev
(chain `61997`) and Studio Next only.

## Deployed

- **Contract:** [`0x7689bE9D97533cA981EC5c2782dE01326b37A8D1`](https://explorer-studio-dev.genlayer.com/address/0x7689bE9D97533cA981EC5c2782dE01326b37A8D1) on Studio Dev, chain `61997`
- **Interface:** [circuit-rose-eta.vercel.app](https://circuit-rose-eta.vercel.app)

Studio Dev state resets periodically; see [STATUS.md](STATUS.md) for the current
state rather than assuming this address still resolves.

## The six verdicts

| Verdict             | Meaning                                             | Effect                          |
| ------------------- | --------------------------------------------------- | ------------------------------- |
| `TRIGGER_CONFIRMED` | The evidence meets the tripwire.                    | Capability issued; fee to treasury |
| `NOT_CONFIRMED`     | The evidence shows the condition is not met.        | Full refund                     |
| `INSUFFICIENT`      | Absent, unreadable or too thin.                     | Full refund (the fail-closed default) |
| `CONFLICTING`       | Sources disagree and cannot be resolved.            | Full refund                     |
| `STALE`             | The evidence is outdated or off-window.             | Full refund                     |
| `TAMPERED`          | The evidence shows signs of alteration or forgery.  | Full refund                     |

A capability is issued only for `TRIGGER_CONFIRMED`; it binds the incident key,
charter hash, target, action class, scope and duration into a digest that must be
reproduced exactly when the capability is consumed.

## Why the design holds

- **One non-deterministic call per assessment.** A judgment runs inside a single
  `strict_eq` block. Each validator fetches the evidence itself and re-derives
  the verdict through the same pure canonicalizer, so agreement is decided on
  the verdict class and the sorted source/clause sets — never on prose.
- **Unreadable evidence can never trigger.** If any evidence URL fails to fetch
  or parse, the verdict is `INSUFFICIENT` and the model is never consulted.
- **A capability is bound to one executor.** Consumption is rejected for every
  caller except the address named in the charter at registration (the author by
  default), so an unrelated account cannot spend or invalidate it.
- **Money is exact.** Bonds and fees are stored as decimal strings; `0.01 GEN`
  is `1e16` wei, above JavaScript's `2**53` exact-integer range.
- **Escape hatches on every GEN-holding status.** A bonded incident can always be
  refunded: on assessment (unless confirmed), on the stuck timeout, and via
  `claim()`, which is pull-only and zeroes the balance before transferring.
- **Evidence is confined.** URLs are https, default port, public domains only,
  and must match a host pattern frozen in the charter — enforced at open time and
  again at fetch time.

## Repository layout

```
contracts/
  Circuit.py                 the contract; one nondet path
  circuitlib/                pure logic: ssrf, canonicalize, judgment, accounting
  build_bundle.py            inlines circuitlib into the deployable
  build/Circuit.bundled.py   what actually deploys (generated; do not edit)
tests/                       the contract driven through a fake GenVM
frontend/                    Vite + React + TypeScript interface
docs/                        architecture, audit, deploy, steward notes
```

## Develop

```sh
# contract
pip install -r requirements-dev.txt
ruff check .
pytest
python contracts/build_bundle.py        # regenerate the deployable
genvm-lint check contracts/build/Circuit.bundled.py

# frontend
cd frontend
npm install
npm run typecheck
npm run build
```

The committed bundle must always match the source it claims to come from; CI
rebuilds it and fails on any diff.

## Deploy

See [docs/DEPLOY.md](docs/DEPLOY.md). The deployable is
`contracts/build/Circuit.bundled.py`; its first byte is the pinned GenVM
`Depends` directive.

## Security

See [SECURITY.md](SECURITY.md) and [docs/audit.md](docs/audit.md).

## License

MIT — see [LICENSE](LICENSE).
