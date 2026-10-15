import { Link } from "react-router-dom";

import { useHealth } from "../components/Chrome";
import { Empty, ErrorNote, Eyebrow, Section, Spinner } from "../components/ui";
import { listCharters } from "../lib/chain";
import { fromNow, gen } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export default function Charters() {
  const { health } = useHealth();
  const live = health.state === "live";
  const q = useAsync(() => (live ? listCharters(60) : Promise.resolve([])), [live]);

  return (
    <Section className="py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Eyebrow>Charters</Eyebrow>
          <h1 className="h-display mt-3 text-[34px]">Registered tripwires</h1>
          <p className="mt-2 max-w-xl text-sm text-mute">
            Each charter freezes a policy, an evidence allow-list, and a bond/fee schedule.
          </p>
        </div>
        <Link to="/app/charters/new" className="btn-primary shrink-0">
          New charter
        </Link>
      </div>

      <div className="mt-8">
        {!live ? (
          <Empty title="No contract live" hint="Charters appear once a deployment is confirmed." />
        ) : q.error ? (
          <ErrorNote error={q.error} />
        ) : q.loading ? (
          <Spinner label="Reading charters…" />
        ) : q.data && q.data.length ? (
          <div className="grid gap-5 md:grid-cols-2">
            {q.data.map((c) => (
              <Link key={c.charter_id} to={`/app/charters/${c.charter_id}`} className="card p-6 transition hover:shadow-lift">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-[17px] font-bold tracking-[-0.01em] text-ink">{c.charter_id}</h3>
                  <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-mute">
                    {fromNow(c.created_at)}
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-mute">{c.policy}</p>
                <p className="mt-3 text-[12px] text-mute">
                  {c.target} · {c.action_class} · bond {gen(c.bond_amount)} · fee {gen(c.fee_amount)}
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <Empty title="No charters yet" hint="Register the first tripwire to begin." />
        )}
      </div>
    </Section>
  );
}
