import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useHealth } from "../components/Chrome";
import { TxStatus, useTx } from "../components/TxPanel";
import { Empty, ErrorNote, Eyebrow, Mono, Section, Spinner } from "../components/ui";
import { listCharters } from "../lib/chain";
import { gen } from "../lib/format";
import { useAsync } from "../lib/useAsync";

function splitUrls(raw: string): string[] {
  return raw
    .split(/\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function OpenIncident() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const { health } = useHealth();
  const live = health.state === "live";
  const tx = useTx();

  const charters = useAsync(() => (live ? listCharters(60) : Promise.resolve([])), [live]);

  const [charterId, setCharterId] = useState(params.get("charter") ?? "");
  const [key, setKey] = useState("");
  const [scope, setScope] = useState("");
  const [duration, setDuration] = useState("30");
  const [urls, setUrls] = useState("");

  useEffect(() => {
    if (!charterId && charters.data && charters.data.length) setCharterId(charters.data[0].charter_id);
  }, [charters.data, charterId]);

  const charter = useMemo(
    () => charters.data?.find((c) => c.charter_id === charterId) ?? null,
    [charters.data, charterId],
  );

  const urlList = splitUrls(urls);
  const value = charter ? BigInt(charter.bond_amount) + BigInt(charter.fee_amount) : 0n;
  const canSubmit =
    live && !tx.busy && charter && key.trim() && scope.trim() && urlList.length > 0 && urlList.length <= 5;

  const submit = async () => {
    if (!charter) return;
    const outcome = await tx.run(
      "open_incident",
      [key.trim(), charter.charter_id, scope.trim(), Number(duration) || 30, urlList],
      value,
    );
    if (outcome?.ok) nav("/app/board");
  };

  return (
    <Section className="py-12">
      <Eyebrow>New incident</Eyebrow>
      <h1 className="h-display mt-3 text-[34px]">Open a bonded incident</h1>
      <p className="mt-2 max-w-2xl text-sm text-mute">
        The attached value is the charter's bond plus its fee, returned in full unless a trigger is
        confirmed. The evidence URLs are frozen here and re-fetched independently by each validator.
      </p>

      {!live ? (
        <div className="mt-8">
          <Empty title="No contract live" hint="Incidents can only be opened against a live deployment." />
        </div>
      ) : charters.error ? (
        <div className="mt-8">
          <ErrorNote error={charters.error} />
        </div>
      ) : charters.loading ? (
        <div className="mt-8">
          <Spinner label="Reading charters…" />
        </div>
      ) : !charters.data || !charters.data.length ? (
        <div className="mt-8">
          <Empty title="No charters to open against" hint="Register a charter first." />
        </div>
      ) : (
        <div className="mt-8 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <div className="card space-y-5 p-7">
            <label className="block">
              <span className="label">Charter</span>
              <select className="field" value={charterId} onChange={(e) => setCharterId(e.target.value)}>
                {charters.data.map((c) => (
                  <option key={c.charter_id} value={c.charter_id}>
                    {c.charter_id} · {c.target}
                  </option>
                ))}
              </select>
            </label>

            <div className="grid gap-5 sm:grid-cols-2">
              <label>
                <span className="label">Incident key</span>
                <input
                  className="field"
                  placeholder="outage-2026-10-15-west"
                  value={key}
                  onChange={(e) => setKey(e.target.value)}
                />
              </label>
              <label>
                <span className="label">Scope</span>
                <input
                  className="field"
                  placeholder="prod-west"
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                />
              </label>
            </div>

            <label className="block">
              <span className="label">Duration (minutes, 5–{charter?.max_duration_minutes ?? 120})</span>
              <input
                className="field"
                inputMode="numeric"
                value={duration}
                onChange={(e) => setDuration(e.target.value.replace(/[^0-9]/g, ""))}
              />
            </label>

            <label className="block">
              <span className="label">Evidence URLs (one per line, up to 5)</span>
              <textarea
                className="field min-h-[96px]"
                placeholder={"https://status.example.com/incidents/123"}
                value={urls}
                onChange={(e) => setUrls(e.target.value)}
              />
            </label>

            <div className="flex flex-wrap items-center gap-3">
              <button className="btn-primary" onClick={submit} disabled={!canSubmit}>
                {tx.busy ? "Submitting…" : `Open · escrow ${gen(value)}`}
              </button>
              {urlList.length > 5 && (
                <span className="text-[12px] text-rose-600">At most 5 URLs.</span>
              )}
            </div>
            <TxStatus hash={tx.hash} outcome={tx.outcome} error={tx.error} />
          </div>

          <aside className="space-y-4">
            {charter && (
              <div className="glass p-6">
                <p className="eyebrow">{charter.charter_id}</p>
                <p className="mt-2 text-sm text-mute">{charter.policy}</p>
                <p className="mt-3 text-[12px] text-mute">
                  bond {gen(charter.bond_amount)} · fee {gen(charter.fee_amount)}
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {charter.evidence_patterns.map((p) => (
                    <Mono key={p}>{p}</Mono>
                  ))}
                </div>
              </div>
            )}
            <div className="glass p-6 text-sm text-mute">
              A URL outside the charter's allow-list is rejected before any validator sees it.
            </div>
          </aside>
        </div>
      )}
    </Section>
  );
}
