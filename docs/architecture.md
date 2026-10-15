# Architecture

CIRCUIT is one contract, `Circuit`, plus a pure library it inlines
(`circuitlib`). The split exists so that every rule that can be tested without a
chain is, and the contract is left holding only the parts that need storage,
value, or consensus.

## The deployable

`contracts/Circuit.py` is the source of record. `contracts/build_bundle.py`
inlines `circuitlib` between two markers and writes
`contracts/build/Circuit.bundled.py`, which is the only file deployed. The
bundler:

- re-emits the pinned `Depends` directive as the first byte;
- strips docstrings (AST-based) to keep the bundle small;
- refuses to drop imported names, to write a BOM, or to emit code that does not
  compile.

CI rebuilds the bundle and fails if it differs from the committed one, so the
deployed artifact can never drift from the reviewed source.

## circuitlib

Four pure modules, no `genlayer` imports, each independently testable.

| Module           | Responsibility |
| ---------------- | -------------- |
| `ssrf.py`        | Evidence URL and host-pattern validation. https only, default port, no IP literals or credentials, public domains only; a URL must match a charter's frozen pattern. |
| `canonicalize.py`| Field validators, canonical JSON, and the digest functions `charter_digest` / `incident_digest`. |
| `judgment.py`    | Decision coercion, comparable construction, `findings_hash`, evidence normalization (HTML strip, fence-collapse, control-char removal), prompt building. |
| `accounting.py`  | `settle(decision, attached, fee)` and the conservation check. |

## The contract

Storage is JSON documents in `TreeMap`s rather than nested storage dataclasses:
an incident is read and written whole, so a document is the natural unit and a
flat storage surface is easier to audit than a graph of one.

```
charters        charter id  -> charter JSON
charter_ids     "all"       -> JSON list of charter ids
incidents       incident id -> incident JSON
open_incidents  incident key-> open incident id (empty when closed)
capabilities    capability id -> capability JSON
claimable       address     -> wei owed
board           "all"       -> JSON list of recent incident ids
```

### Methods

Writes (7): `register_charter`, `open_incident` (payable), `assess`,
`consume_capability`, `expire_stuck`, `expire_capability`, `claim`.

Views (7): `get_config`, `get_charter`, `get_charter_ids`, `get_incident`,
`get_capability`, `get_board`, `get_claimable`.

### The one nondeterministic path

`assess` calls `_judge`, whose only nondeterministic call is a single
`gl.eq_principle.strict_eq(judge)`. Inside `judge`, evidence is fetched with
`gl.nondet.web.render` and, when every source read cleanly, the model is asked
once. The result is canonicalized by the same pure function in every validator,
so consensus is on the verdict class and sorted index/clause sets. Any exception
— including no consensus — falls back to `INSUFFICIENT` (`_FAIL_CLOSED`).

The fetch loop is inlined into `judge` rather than factored into a helper,
because `genvm-lint` only follows `gl.nondet.*` calls made directly inside the
function handed to the equivalence principle.

### Time

Time is read from `gl.message.raw["datetime"]`, which every validator
re-executing the call sees identically. `gl.block` does not exist and
`gl.vm.get_timestamp()` raises on this runtime.

### Value

Bonds and fees are `u256` wei on chain but are serialized into record JSON as
decimal **strings**, because `0.01 GEN` is `1e16` wei — beyond the exactly
representable range of a JavaScript number. All internal reads wrap them in
`int()`. The only function that moves value out is `claim()`, which zeroes the
balance before transferring through an `@gl.evm.contract_interface` recipient.

## The interface

`frontend/` is a Vite + React + TypeScript app. It reads the chain directly over
JSON-RPC, treats every unconfirmed state as failure (see `src/lib/tx.ts`), and
renders an explicit empty state rather than inventing a record. Liveness is
probed with `gen_getContractSchema`, not `eth_getCode` — a live GenLayer
contract can return `0x` for `eth_getCode`.
