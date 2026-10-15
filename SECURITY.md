# Security

## Reporting

Report suspected vulnerabilities privately to `fortuneemx@gmail.com`. Do not
open a public issue for a live exploit. Please include the contract method, the
inputs, and the observed vs. expected result.

## Threat model

CIRCUIT is a single GenLayer Intelligent Contract that turns a written charter
into a one-shot, expiring capability — but only when validators independently
confirm a tripwire. The assets it protects are (a) the assessor bonds it holds
and (b) the false-authority risk of issuing a capability that a downstream
system will act on.

The design assumes every off-chain input is hostile:

- **Evidence pages.** Fetched URLs, their bytes, and any text inside them are
  treated as attacker-controlled data, never as instructions. Content is
  HTML-stripped, fence markers are removed, and prompt-injection attempts are
  declared in the prompt as evidence of bad faith.
- **The model.** The LLM runs inside `gl.eq_principle.strict_eq`; its raw prose
  is never trusted. Only a canonical, comparable record — decision class,
  sorted supporting-source indices, sorted clause ids, and a findings hash over
  the normalized evidence — is compared across validators.
- **The caller.** Nothing about a judgment comes from the caller's claims about
  themselves. `consume_capability` re-derives the canonical digest from its
  arguments and rejects any mismatch.

### Fail-closed invariants

1. Only `TRIGGER_CONFIRMED` issues a capability. `NOT_CONFIRMED`,
   `INSUFFICIENT`, `CONFLICTING`, `STALE`, and `TAMPERED` refund the bond in
   full and issue nothing.
2. A failed or partial evidence fetch can only ever produce `INSUFFICIENT`. The
   model is not consulted at all when evidence cannot be read.
3. No consensus, a model error, or an unparseable agreed value all resolve to
   `INSUFFICIENT` — never to a capability.
4. `claim()` is the only function that moves value out, it zeroes the balance
   before transferring, and it can only ever send an address its own
   already-credited amount. There is no admin path that seizes or force-issues.

### SSRF and resource bounds

Evidence URLs are validated before they are ever frozen and re-checked at fetch
time. Only `https` on the default port, no credentials, no IP literals, no
loopback/metadata/private/link-local/`home.arpa` hosts, alphabetic TLDs only,
bounded URL count and length, and a bounded number of characters per fetched
page. See `contracts/circuitlib/ssrf.py` for the exact rules and
`docs/audit.md` for their rationale.

## Out of scope

- The GenLayer runtime, the SDK, and the LLM backend.
- The correctness of the *charter text*: CIRCUIT decides whether evidence
  matches the tripwire as written, not whether the charter's author meant it.
- Downstream systems that consume a capability. CIRCUIT issues the artifact; it
  does not control what a verifier does with it.
