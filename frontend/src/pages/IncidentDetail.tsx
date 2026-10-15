import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useHealth } from "../components/Chrome";
import { TxStatus, useTx } from "../components/TxPanel";
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
  StatusPill,
} from "../components/ui";
import { getCapability, getClaimable, getIncident } from "../lib/chain";
import { fromNow, gen, shortHash, until } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export default function IncidentDetail() {
  const { id = "" } = useParams();
  const { health, account } = useHealth();
  const live = health.state === "live";
  const tx = useTx();
  const claimTx = useTx();

  const inc = useAsync(() => (live ? getIncident(id) : Promise.resolve(null)), [live, id]);
  const capId = inc.data?.capability_id ?? "";
  const cap = useAsync(
    () => (live && capId ? getCapability(capId) : Promise.resolve(null)),
    [live, capId],
  );
  const owed = useAsync(
    () => (live && account ? getClaimable(account) : Promise.resolve("0")),
    [live, account, tx.outcome, claimTx.outcome],
  );

  const [form, setForm] = useState<Record<string, string> | null>(null);

  const reload = () => {
    inc.reload();
    cap.reload();
    owed.reload();
  };

  const assess = async () => {
    const outcome = await tx.run("assess", [id]);
    if (outcome?.settled) reload();
  };

  const consume = async () => {
    if (!inc.data) return;
    const f = form ?? {
      incident_key: inc.data.incident_key,
      charter_hash: inc.data.charter_hash,
      target: inc.data.target,
      action_class: inc.data.action_class,
      scope: inc.data.scope,
      duration_minutes: String(inc.data.duration_minutes),
    };
    const outcome = await tx.run("consume_capability", [
      inc.data.capability_id,
      f.incident_key,
      f.charter_hash,
      f.target,
      f.action_class,
      f.scope,
      Number(f.duration_minutes),
    ]);
    if (outcome?.settled) reload();
  };

  const expireCap = async () => {
    const outcome = await tx.run("expire_capability", [capId]);
    if (outcome?.settled) reload();
  };

  const expireStuck = async () => {
    const outcome = await tx.run("expire_stuck", [id]);
    if (outcome?.settled) reload();
  };

  const claim = async () => {
    const outcome = await claimTx.run("claim", []);
    if (outcome?.settled) reload();
  };

  return (
    <Section className="py-12">
      <Link
        to="/app/board"
        className="text-[12px] font-semibold uppercase tracking-[0.12em] text-mute hover:text-ink"
      >
        ← Board
      </Link>

      <div className="mt-5">
        {!live ? (
          <Empty title="No contract live" hint="Incidents cannot be read until a deployment is confirmed." />
        ) : inc.error ? (
          <ErrorNote error={inc.error} />
        ) : inc.loading ? (
          <Spinner label="Reading the incident…" />
        ) : !inc.data ? (
          <Empty title="Incident not found" hint={`No incident is recorded as "${id}".`} />
        ) : (
          (() => {
            const e = inc.data!;
            const now = Math.floor(Date.now() / 1000);
            const permissionlessAt = e.created_at + 1800;
            const stuckAt = e.created_at + 86400;
            return (
              <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
                <div className="card space-y-6 p-7">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <Eyebrow>Incident</Eyebrow>
                      <h1 className="h-display mt-2 text-[28px]">
                        {e.target} · <span className="text-mute">{e.action_class}</span>
                      </h1>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusPill status={e.status} />
                      <DecisionPill decision={e.decision} />
                    </div>
                  </div>

                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Incident key">{e.incident_key}</Field>
                    <Field label="Charter">
                      <Link to={`/app/charters/${e.charter_id}`} className="font-medium text-brand-deep">
                        {e.charter_id}
                      </Link>
                    </Field>
                    <Field label="Scope">{e.scope}</Field>
                    <Field label="Duration">{e.duration_minutes} minutes</Field>
                    <Field label="Assessor">
                      <AddressLink value={e.assessor} />
                    </Field>
                    <Field label="Bond / fee">
                      {gen(e.bond)} · {gen(e.fee)}
                    </Field>
                  </div>

                  <Field label="Evidence URLs">
                    <div className="space-y-1">
                      {e.evidence_urls.map((u) => (
                        <a
                          key={u}
                          href={u}
                          target="_blank"
                          rel="noreferrer"
                          className="block break-all font-medium text-brand-deep underline decoration-brand/30 underline-offset-2"
                        >
                          {u}
                        </a>
                      ))}
                    </div>
                  </Field>

                  {(e.decision || e.code) && (
                    <div className="rounded-chip border border-white/70 bg-white/50 p-5">
                      <p className="eyebrow">Finding</p>
                      <div className="mt-3 grid gap-4 sm:grid-cols-2">
                        <Field label="Code">
                          <Mono>{e.code || "—"}</Mono>
                        </Field>
                        <Field label="Supporting sources">
                          {e.supporting_sources.length ? e.supporting_sources.join(", ") : "none"}
                        </Field>
                        <Field label="Clause ids">
                          {e.clause_ids.length ? e.clause_ids.join(", ") : "none"}
                        </Field>
                        <Field label="Findings hash">{shortHash(e.findings_hash, 8)}</Field>
                      </div>
                    </div>
                  )}

                  {e.status === "OPEN" && (
                    <div className="flex flex-wrap items-center gap-3 border-t border-white/50 pt-5">
                      <button className="btn-primary" onClick={assess} disabled={tx.busy}>
                        {tx.busy ? "Assessing…" : "Assess now"}
                      </button>
                      <span className="text-[12px] text-mute">
                        Anyone may assess{" "}
                        {now >= permissionlessAt
                          ? "now."
                          : `in ${until(permissionlessAt, now)}.`}
                      </span>
                    </div>
                  )}
                  {e.status === "OPEN" && now >= stuckAt && (
                    <button className="btn-ghost" onClick={expireStuck} disabled={tx.busy}>
                      Refund as stuck
                    </button>
                  )}
                  <TxStatus hash={tx.hash} outcome={tx.outcome} error={tx.error} />
                </div>

                <aside className="space-y-4">
                  <div className="glass p-6">
                    <Field label="Canonical digest">{shortHash(e.digest, 10)}</Field>
                    <div className="mt-3">
                      <Field label="Opened">{fromNow(e.created_at)}</Field>
                    </div>
                    {e.assessed_at > 0 && (
                      <div className="mt-3">
                        <Field label="Assessed">{fromNow(e.assessed_at)}</Field>
                      </div>
                    )}
                  </div>

                  {account && (
                    <div className="glass p-6">
                      <p className="eyebrow">Your wallet</p>
                      <p className="mt-2 text-sm text-mute">
                        Claimable: <span className="font-semibold text-ink">{gen(owed.data ?? "0")}</span>
                      </p>
                      <button
                        className="btn-ghost mt-4 w-full"
                        onClick={claim}
                        disabled={claimTx.busy || BigInt(owed.data ?? "0") <= 0n}
                      >
                        {claimTx.busy ? "Claiming…" : "Claim"}
                      </button>
                      <div className="mt-3">
                        <TxStatus
                          hash={claimTx.hash}
                          outcome={claimTx.outcome}
                          error={claimTx.error}
                        />
                      </div>
                    </div>
                  )}

                  {e.capability_id && cap.data && (
                    <div className="card space-y-4 p-6">
                      <div className="flex items-center justify-between gap-3">
                        <p className="eyebrow">Capability</p>
                        <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-mute">
                          {cap.data.consumed ? "consumed" : cap.data.expired ? "expired" : "live"}
                        </span>
                      </div>
                      <Field label="Id">{cap.data.capability_id}</Field>
                      <Field label="Expires">
                        {cap.data.consumed
                          ? `consumed ${fromNow(cap.data.consumed_at)}`
                          : until(cap.data.expires_at)}
                      </Field>

                      {!cap.data.consumed && !cap.data.expired && inc.data.decision === "TRIGGER_CONFIRMED" && (
                        <div className="space-y-3 border-t border-white/50 pt-4">
                          <p className="text-[12px] text-mute">
                            Consuming re-derives the digest from these fields. Any mismatch is
                            rejected.
                          </p>
                          {(
                            [
                              "incident_key",
                              "charter_hash",
                              "target",
                              "action_class",
                              "scope",
                              "duration_minutes",
                            ] as const
                          ).map((k) => (
                            <label key={k} className="block">
                              <span className="label">{k.replace(/_/g, " ")}</span>
                              <input
                                className="field"
                                value={
                                  (form ?? {
                                    incident_key: inc.data!.incident_key,
                                    charter_hash: inc.data!.charter_hash,
                                    target: inc.data!.target,
                                    action_class: inc.data!.action_class,
                                    scope: inc.data!.scope,
                                    duration_minutes: String(inc.data!.duration_minutes),
                                  })[k]
                                }
                                onChange={(ev) =>
                                  setForm({
                                    ...(form ?? {
                                      incident_key: inc.data!.incident_key,
                                      charter_hash: inc.data!.charter_hash,
                                      target: inc.data!.target,
                                      action_class: inc.data!.action_class,
                                      scope: inc.data!.scope,
                                      duration_minutes: String(inc.data!.duration_minutes),
                                    }),
                                    [k]: ev.target.value,
                                  })
                                }
                              />
                            </label>
                          ))}
                          <button className="btn-primary w-full" onClick={consume} disabled={tx.busy}>
                            {tx.busy ? "Consuming…" : "Consume capability"}
                          </button>
                        </div>
                      )}
                      {!cap.data.consumed && !cap.data.expired && cap.data.expires_at < now && (
                        <button className="btn-ghost w-full" onClick={expireCap} disabled={tx.busy}>
                          Mark expired
                        </button>
                      )}
                    </div>
                  )}

                  {e.status === "ASSESSED" && e.decision && e.decision !== "TRIGGER_CONFIRMED" && (
                    <div className="glass p-6 text-sm text-mute">
                      No capability was issued. The bond was refunded in full — a non-confirming
                      verdict is never charged for.
                    </div>
                  )}
                </aside>
              </div>
            );
          })()
        )}
      </div>
    </Section>
  );
}
