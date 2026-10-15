import { Link, useParams } from "react-router-dom";

import { useHealth } from "../components/Chrome";
import { AddressLink, Empty, ErrorNote, Eyebrow, Field, Mono, Section, Spinner } from "../components/ui";
import { getCharter } from "../lib/chain";
import { fromNow, gen, shortHash } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export default function CharterDetail() {
  const { id = "" } = useParams();
  const { health } = useHealth();
  const live = health.state === "live";
  const q = useAsync(() => (live ? getCharter(id) : Promise.resolve(null)), [live, id]);

  return (
    <Section className="py-12">
      <Link to="/app/charters" className="text-[12px] font-semibold uppercase tracking-[0.12em] text-mute hover:text-ink">
        ← Charters
      </Link>

      <div className="mt-5">
        {!live ? (
          <Empty title="No contract live" hint="This charter cannot be read until a deployment is confirmed." />
        ) : q.error ? (
          <ErrorNote error={q.error} />
        ) : q.loading ? (
          <Spinner label="Reading the charter…" />
        ) : !q.data ? (
          <Empty title="Charter not found" hint={`No charter is registered under "${id}".`} />
        ) : (
          (() => {
            const c = q.data!;
            return (
              <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
                <div className="card space-y-6 p-7">
                  <div>
                    <Eyebrow>Charter</Eyebrow>
                    <h1 className="h-display mt-2 text-[30px]">{c.charter_id}</h1>
                  </div>
                  <Field label="Policy — the tripwire">
                    <p className="whitespace-pre-wrap leading-relaxed">{c.policy}</p>
                  </Field>
                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Target">{c.target}</Field>
                    <Field label="Action class">{c.action_class}</Field>
                    <Field label="Max duration">{c.max_duration_minutes} minutes</Field>
                    <Field label="Bond / fee">
                      {gen(c.bond_amount)} · {gen(c.fee_amount)}
                    </Field>
                  </div>
                  <Field label="Allowed evidence hosts">
                    <div className="flex flex-wrap gap-1.5">
                      {c.evidence_patterns.map((p) => (
                        <Mono key={p}>{p}</Mono>
                      ))}
                    </div>
                  </Field>
                </div>

                <aside className="space-y-4">
                  <div className="glass p-6">
                    <Field label="Author">
                      <AddressLink value={c.author} />
                    </Field>
                    <div className="mt-4">
                      <Field label="Registered">{fromNow(c.created_at)}</Field>
                    </div>
                    <div className="mt-4">
                      <Field label="Charter hash">{shortHash(c.charter_hash, 10)}</Field>
                    </div>
                    <div className="mt-4">
                      <Field label="Treasury">
                        <AddressLink value={c.treasury} />
                      </Field>
                    </div>
                  </div>
                  <Link to={`/app/incidents/new?charter=${encodeURIComponent(c.charter_id)}`} className="btn-primary w-full">
                    Open an incident
                  </Link>
                </aside>
              </div>
            );
          })()
        )}
      </div>
    </Section>
  );
}
