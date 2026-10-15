import { Link } from "react-router-dom";

import { useHealth } from "../components/Chrome";
import { DecisionPill, Empty, ErrorNote, Eyebrow, Section, Spinner, StatusPill } from "../components/ui";
import { getBoard } from "../lib/chain";
import { fromNow } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export default function Board() {
  const { health } = useHealth();
  const live = health.state === "live";
  const q = useAsync(() => (live ? getBoard(60) : Promise.resolve([])), [live]);

  return (
    <Section className="py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Eyebrow>The board</Eyebrow>
          <h1 className="h-display mt-3 text-[34px]">Incidents</h1>
          <p className="mt-2 max-w-xl text-sm text-mute">
            Every incident is a bonded assessment. A capability appears below only when a trigger
            was confirmed.
          </p>
        </div>
        <Link to="/app/incidents/new" className="btn-primary shrink-0">
          Open an incident
        </Link>
      </div>

      <div className="mt-8">
        {!live ? (
          <Empty
            title="The board is offline until the contract is live"
            hint="Nothing is fabricated here. Configure a confirmed deployment and this fills in."
          />
        ) : q.error ? (
          <ErrorNote error={q.error} />
        ) : q.loading ? (
          <Spinner label="Reading the board…" />
        ) : q.data && q.data.length ? (
          <div className="card divide-y divide-white/50 overflow-hidden">
            {q.data.map((e) => (
              <Link
                key={e.incident_id}
                to={`/app/incidents/${e.incident_id}`}
                className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 transition hover:bg-white/50"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink">
                    {e.target} · <span className="text-mute">{e.action_class}</span>
                  </p>
                  <p className="text-[12px] text-mute">
                    {e.incident_id} · charter {e.charter_id} · {fromNow(e.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusPill status={e.status} />
                  <DecisionPill decision={e.decision} />
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <Empty title="No incidents yet" hint="Open one against a charter to see it here." />
        )}
      </div>
    </Section>
  );
}
