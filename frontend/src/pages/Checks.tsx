import { useHealth } from "../components/Chrome";
import {
  AddressLink,
  DecisionPill,
  Empty,
  ErrorNote,
  Eyebrow,
  Field,
  Mono,
  Section,
  Spinner,
} from "../components/ui";
import { getConfig } from "../lib/chain";
import type { Decision } from "../lib/types";
import { useAsync } from "../lib/useAsync";

const DECISIONS: Decision[] = [
  "TRIGGER_CONFIRMED",
  "NOT_CONFIRMED",
  "INSUFFICIENT",
  "CONFLICTING",
  "STALE",
  "TAMPERED",
];

const INVARIANTS: { title: string; body: string }[] = [
  {
    title: "One non-deterministic call per assessment",
    body: "A judgment runs inside a single strict_eq block. Every validator fetches the evidence itself and re-derives the verdict through the same pure canonicalizer, so agreement is decided on the verdict class and the sorted source/clause sets — never on prose.",
  },
  {
    title: "Unreadable evidence can never trigger",
    body: "If any evidence URL fails to fetch or parse the verdict is INSUFFICIENT and the model is not consulted at all. A network failure is structurally incapable of producing a capability.",
  },
  {
    title: "Capabilities are single-use, expiring, and digest-bound",
    body: "The digest binds incident key, charter hash, target, action class, scope and duration. It is recomputed at freeze, at issuance, and at consumption; any mismatch rejects the call.",
  },
  {
    title: "No verdict but a confirmed trigger charges anything",
    body: "Every other verdict — and every technical failure — refunds the bond in full. The treasury fee moves only on TRIGGER_CONFIRMED.",
  },
  {
    title: "Balances are pull-only",
    body: "Nothing is pushed to a wallet. claim() zeroes the balance before transferring, so funds cannot be double-spent and a non-receiving address cannot lock the protocol.",
  },
  {
    title: "Evidence is confined to an allow-list",
    body: "URLs are https, default port, public domains only, and must match a host pattern frozen in the charter. The rule is applied when the incident opens and again at fetch time.",
  },
];

export default function Checks() {
  const { health, refresh } = useHealth();
  const live = health.state === "live";
  const cfg = useAsync(() => (live ? getConfig() : Promise.resolve(null)), [live]);

  return (
    <Section className="py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Eyebrow>Checks</Eyebrow>
          <h1 className="h-display mt-3 text-[34px]">What CIRCUIT guarantees</h1>
          <p className="mt-2 max-w-2xl text-sm text-mute">
            The properties below hold in the contract itself, not in this page. They are listed here
            so they can be checked against the deployed source.
          </p>
        </div>
        <button className="btn-ghost shrink-0" onClick={refresh}>
          Re-check connection
        </button>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="card p-7">
          <p className="eyebrow">Deployment</p>
          {!live ? (
            <div className="mt-3">
              <Empty
                title="Not live"
                hint="The banner above states exactly why. This page will not show a config until a deployment is confirmed by the chain."
              />
            </div>
          ) : cfg.error ? (
            <div className="mt-3">
              <ErrorNote error={cfg.error} />
            </div>
          ) : cfg.loading ? (
            <div className="mt-3">
              <Spinner label="Reading config…" />
            </div>
          ) : cfg.data ? (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Field label="Contract">{health.address}</Field>
              <Field label="Owner">
                <AddressLink value={cfg.data.owner} />
              </Field>
              <Field label="Treasury">
                <AddressLink value={cfg.data.treasury} />
              </Field>
              <Field label="Assess delay">{cfg.data.assess_delay_seconds}s</Field>
              <Field label="Stuck timeout">{cfg.data.stuck_timeout_seconds}s</Field>
              <Field label="Duration range">
                {cfg.data.min_duration_minutes}–{cfg.data.max_duration_minutes} min
              </Field>
              <Field label="Max evidence URLs">{cfg.data.max_evidence_urls}</Field>
              <Field label="Charters registered">{cfg.data.next_charter - 1}</Field>
              <Field label="Incidents opened">{cfg.data.next_incident - 1}</Field>
              <Field label="Capabilities minted">{cfg.data.next_capability - 1}</Field>
            </div>
          ) : null}
        </div>

        <div className="card p-7">
          <p className="eyebrow">The six verdicts</p>
          <p className="mt-2 text-sm text-mute">
            Exactly one is chosen per assessment. Only the first issues a capability.
          </p>
          <div className="mt-4 space-y-2">
            {DECISIONS.map((d) => (
              <div key={d} className="flex items-center justify-between gap-3">
                <DecisionPill decision={d} />
                <Mono>{d === "TRIGGER_CONFIRMED" ? "capability issued" : "full refund"}</Mono>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-5 md:grid-cols-2">
        {INVARIANTS.map((inv) => (
          <div key={inv.title} className="glass p-6">
            <h3 className="text-[15px] font-bold tracking-[-0.01em] text-ink">{inv.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-mute">{inv.body}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}
