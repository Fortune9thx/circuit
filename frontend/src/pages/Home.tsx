import { Link } from "react-router-dom";

import { useHealth } from "../components/Chrome";
import { CtaBand, DecisionPill, Empty, Eyebrow, Seal, Section } from "../components/ui";
import { getBoard } from "../lib/chain";
import { fromNow } from "../lib/format";
import type { Decision } from "../lib/types";
import { useAsync } from "../lib/useAsync";

const STEPS = [
  {
    title: "Register a charter",
    body: "Write the tripwire once: a policy, the evidence hosts it may be judged against, a target, an action class, and a bond/fee schedule. It is frozen and hashed.",
  },
  {
    title: "Open a bonded incident",
    body: "An assessor posts the bond and freezes the evidence URLs plus a canonical digest. Nothing about the judgment comes from the caller's claims.",
  },
  {
    title: "Validators decide",
    body: "Each validator independently re-fetches the evidence and re-derives the verdict. Only a confirmed trigger issues a one-shot, expiring capability; everything else refunds in full.",
  },
];

const DECISIONS: { key: Decision; line: string }[] = [
  { key: "TRIGGER_CONFIRMED", line: "The evidence meets the tripwire. A capability is issued." },
  { key: "NOT_CONFIRMED", line: "The evidence shows the condition is not met." },
  { key: "INSUFFICIENT", line: "Absent, unreadable or too thin. The fail-closed default." },
  { key: "CONFLICTING", line: "Sources disagree and cannot be resolved." },
  { key: "STALE", line: "The evidence is outdated or off-window." },
  { key: "TAMPERED", line: "The evidence shows signs of alteration or forgery." },
];

export default function Home() {
  const { health } = useHealth();
  const live = health.state === "live";
  const board = useAsync(() => (live ? getBoard(6) : Promise.resolve([])), [live]);

  return (
    <div className="pb-4">
      <Section className="pt-14 sm:pt-20">
        <div className="grid items-center gap-10 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <Eyebrow>Temporary circuit-breaker protocol</Eyebrow>
            <h1 className="h-display mt-4 text-[44px] sm:text-[58px]">
              A tripwire is only worth as much as the evidence behind it.
            </h1>
            <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-mute">
              CIRCUIT turns a written charter into a single-use, expiring capability — but only
              when independent validators confirm a trigger from evidence they fetched and judged
              themselves. Anything short of that refunds the bond and issues nothing.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/app/board" className="btn-primary">
                Open the board
              </Link>
              <Link to="/app/charters/new" className="btn-white">
                Register a charter
              </Link>
            </div>
          </div>
          <div className="flex justify-center lg:justify-end">
            <Seal />
          </div>
        </div>
      </Section>

      <Section className="mt-16">
        <div className="grid gap-5 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <div key={s.title} className="card p-7">
              <span className="text-[12px] font-extrabold text-brand">{String(i + 1).padStart(2, "0")}</span>
              <h3 className="mt-3 text-[17px] font-bold tracking-[-0.01em] text-ink">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-mute">{s.body}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section className="mt-16">
        <Eyebrow>Six discrete verdicts</Eyebrow>
        <h2 className="h-display mt-3 text-[30px]">One of these, or the bond comes back.</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {DECISIONS.map((d) => (
            <div key={d.key} className="glass p-5">
              <DecisionPill decision={d.key} />
              <p className="mt-3 text-sm text-mute">{d.line}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section className="mt-16">
        <div className="flex items-end justify-between gap-4">
          <div>
            <Eyebrow>Latest on the board</Eyebrow>
            <h2 className="h-display mt-3 text-[30px]">Recent incidents</h2>
          </div>
          <Link to="/app/board" className="btn-ghost shrink-0">
            View all
          </Link>
        </div>
        <div className="mt-6">
          {!live ? (
            <Empty
              title="Nothing is live yet"
              hint="The board reads the contract directly. Until a deployment is confirmed by gen_getContractSchema, this stays empty on purpose."
            />
          ) : board.loading ? (
            <Empty title="Reading the board…" />
          ) : board.data && board.data.length ? (
            <div className="card divide-y divide-white/50 overflow-hidden">
              {board.data.map((e) => (
                <Link
                  key={e.incident_id}
                  to={`/app/incidents/${e.incident_id}`}
                  className="flex items-center justify-between gap-4 px-6 py-4 transition hover:bg-white/50"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-ink">
                      {e.target} · {e.action_class}
                    </p>
                    <p className="text-[12px] text-mute">
                      {e.incident_id} · {fromNow(e.created_at)}
                    </p>
                  </div>
                  <DecisionPill decision={e.decision} />
                </Link>
              ))}
            </div>
          ) : (
            <Empty title="No incidents yet" hint="Open one against a charter to see it here." />
          )}
        </div>
      </Section>

      <Section className="mt-16">
        <CtaBand
          title="Write the tripwire. Let independent validators decide."
          action="Register a charter"
          to="/app/charters/new"
        />
      </Section>
    </div>
  );
}
