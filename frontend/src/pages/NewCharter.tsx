import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useHealth } from "../components/Chrome";
import { TxStatus, useTx } from "../components/TxPanel";
import { Eyebrow, Section } from "../components/ui";
import { clampInt, toWei } from "../lib/format";

function splitPatterns(raw: string): string[] {
  return raw
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function NewCharter() {
  const nav = useNavigate();
  const { health } = useHealth();
  const tx = useTx();

  const [charterId, setCharterId] = useState("");
  const [policy, setPolicy] = useState("");
  const [patterns, setPatterns] = useState("*.example.com");
  const [target, setTarget] = useState("");
  const [actionClass, setActionClass] = useState("");
  const [maxDuration, setMaxDuration] = useState("60");
  const [bond, setBond] = useState("0.01");
  const [fee, setFee] = useState("0.001");
  const [executor, setExecutor] = useState("");

  const live = health.state === "live";
  const patternList = splitPatterns(patterns);
  const canSubmit =
    live && !tx.busy && charterId.trim() && policy.trim() && patternList.length > 0 && target.trim() && actionClass.trim();

  const submit = async () => {
    const outcome = await tx.run("register_charter", [
      charterId.trim(),
      policy.trim(),
      patternList,
      target.trim(),
      actionClass.trim().toLowerCase(),
      clampInt(maxDuration, 5, 120, 60),
      toWei(bond),
      toWei(fee),
      executor.trim(),
    ]);
    if (outcome?.ok) nav(`/app/charters/${charterId.trim().toLowerCase()}`);
  };

  return (
    <Section className="py-12">
      <Eyebrow>New charter</Eyebrow>
      <h1 className="h-display mt-3 text-[34px]">Write the tripwire</h1>
      <p className="mt-2 max-w-2xl text-sm text-mute">
        A charter is immutable once registered. The evidence hosts you allow are enforced before an
        incident is ever opened, so a proof can only be judged against pages you named in advance.
      </p>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="card space-y-5 p-7">
          <div className="grid gap-5 sm:grid-cols-2">
            <label>
              <span className="label">Charter id</span>
              <input
                className="field"
                placeholder="payments-tripwire"
                value={charterId}
                onChange={(e) => setCharterId(e.target.value)}
              />
            </label>
            <label>
              <span className="label">Target</span>
              <input
                className="field"
                placeholder="payments-service"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              />
            </label>
          </div>

          <label className="block">
            <span className="label">Policy — what must be true to trip</span>
            <textarea
              className="field min-h-[130px]"
              placeholder="Trip when an independent status page reports the payments API as fully down for the stated window."
              value={policy}
              onChange={(e) => setPolicy(e.target.value)}
            />
          </label>

          <div className="grid gap-5 sm:grid-cols-2">
            <label>
              <span className="label">Action class</span>
              <input
                className="field"
                placeholder="deploy"
                value={actionClass}
                onChange={(e) => setActionClass(e.target.value)}
              />
            </label>
            <label>
              <span className="label">Max duration (minutes, 5–120)</span>
              <input
                className="field"
                inputMode="numeric"
                value={maxDuration}
                onChange={(e) => setMaxDuration(e.target.value.replace(/[^0-9]/g, ""))}
              />
            </label>
          </div>

          <label className="block">
            <span className="label">Allowed evidence hosts (one per line, or comma-separated)</span>
            <textarea
              className="field min-h-[84px]"
              placeholder="*.statuspage.io&#10;api.example.com"
              value={patterns}
              onChange={(e) => setPatterns(e.target.value)}
            />
          </label>

          <div className="grid gap-5 sm:grid-cols-2">
            <label>
              <span className="label">Bond (GEN)</span>
              <input
                className="field"
                inputMode="decimal"
                value={bond}
                onChange={(e) => setBond(e.target.value)}
              />
            </label>
            <label>
              <span className="label">Fee to treasury on confirm (GEN)</span>
              <input
                className="field"
                inputMode="decimal"
                value={fee}
                onChange={(e) => setFee(e.target.value)}
              />
            </label>
          </div>

          <label className="block">
            <span className="label">Authorized executor (optional)</span>
            <input
              className="field font-mono"
              placeholder="0x… — leave empty to name your own wallet"
              value={executor}
              onChange={(e) => setExecutor(e.target.value)}
            />
            <span className="mt-1 block text-[12px] text-mute">
              The only address that may consume a capability this charter issues. Defaults to the
              author. Frozen into the charter hash — it cannot change later.
            </span>
          </label>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <button className="btn-primary" onClick={submit} disabled={!canSubmit}>
              {tx.busy ? "Submitting…" : "Register charter"}
            </button>
            {!live && <span className="text-[12px] text-mute">Contract is not live.</span>}
          </div>
          <TxStatus hash={tx.hash} outcome={tx.outcome} error={tx.error} />
        </div>

        <aside className="space-y-4">
          <div className="glass p-6">
            <p className="eyebrow">What the fields mean</p>
            <ul className="mt-3 space-y-2 text-sm text-mute">
              <li>The <strong className="text-ink">policy</strong> is the only text validators judge against.</li>
              <li>The <strong className="text-ink">host allow-list</strong> is enforced by SSRF rules — https, default port, public domains only.</li>
              <li>The <strong className="text-ink">bond</strong> is returned in full on every non-confirming verdict.</li>
              <li>A <strong className="text-ink">fee</strong> moves to the recorded treasury only on a confirmed trigger.</li>
              <li>The <strong className="text-ink">executor</strong> is the only address that can consume an issued capability; anyone else is rejected.</li>
            </ul>
          </div>
          <div className="glass p-6">
            <p className="eyebrow">Allowed hosts</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {patternList.length ? (
                patternList.map((p) => (
                  <code
                    key={p}
                    className="rounded-lg bg-white/60 px-2 py-1 text-[12px] ring-1 ring-inset ring-white/70"
                  >
                    {p}
                  </code>
                ))
              ) : (
                <span className="text-sm text-mute">none yet</span>
              )}
            </div>
          </div>
        </aside>
      </div>
    </Section>
  );
}
