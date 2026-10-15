# Changelog

All notable changes to CIRCUIT are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-15

### Added

- `Circuit` Intelligent Contract for GenLayer Studio Dev (chain id 61997),
  pinned to `py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng`.
- Charter registry: a written policy, evidence host patterns, a tripwire target
  and action class, a bond/fee schedule, and a frozen `charter_hash`.
- Bonded incident lifecycle: `open_incident` (payable) freezes evidence URLs and
  a canonical digest, `assess` runs the tripwire under validator consensus and
  settles the bond, `expire_stuck` refunds an incident no one assessed.
- One-shot, expiring capability issuance (`5–120` minutes) with a
  content-addressed digest recomputed at freeze, issuance, and consumption.
- Six discrete verdicts (`TRIGGER_CONFIRMED`, `NOT_CONFIRMED`, `INSUFFICIENT`,
  `CONFLICTING`, `STALE`, `TAMPERED`); only `TRIGGER_CONFIRMED` issues.
- `circuitlib`: dependency-free pure-logic package (`ssrf`, `canonicalize`,
  `accounting`, `judgment`) with its own test suite, inlined into the deployable
  by `contracts/build_bundle.py`.
- Vite + React + TypeScript + Tailwind frontend with a fail-closed STATUS
  surface that reads liveness from `gen_getContractSchema`, never `eth_getCode`.
