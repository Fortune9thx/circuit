"""circuitlib — the dependency-free logic behind the CIRCUIT contract.

Nothing in this package imports `genlayer`. Every rule that decides whether a
capability is issued — SSRF policy, canonicalization and digests, bond
settlement, and the normalization of a model's answer — lives here so it can be
unit-tested under CPython and audited without the VM. `contracts/build_bundle.py`
inlines these modules into the single deployable file.
"""
