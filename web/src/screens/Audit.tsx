import { useEffect, useState } from "preact/hooks";
import { api, type AuditRow, type Verify } from "../api";

export function Audit() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [verify, setVerify] = useState<Verify | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.audit().then(setRows).catch(() => setRows([])); }, []);

  async function check() {
    setBusy(true);
    try { setVerify(await api.verify()); setRows(await api.audit()); } finally { setBusy(false); }
  }

  return (
    <div class="stack">
      <div class="row spread">
        <h1>Audit chain</h1>
        <button class="btn btn-primary" onClick={check} data-state={busy ? "loading" : verify ? (verify.ok ? "success" : "error") : undefined} disabled={busy}>
          Verify chain
        </button>
      </div>
      <p class="muted">Every draft, edit and confirmation is a new row. Each row's hash covers its content and the previous row's hash, so changing any row breaks every hash after it.</p>
      {verify && (
        <p class="banner" role="status" data-tone={verify.ok ? "ok" : "bad"}>
          {verify.ok ? `✓ Chain intact — ${verify.checked} rows verified.` : `▲ Chain broken at seq ${verify.first_bad_seq}: ${verify.reason}. ${verify.checked} rows before it verified.`}
        </p>
      )}
      <div class="scroll-x">
        <table class="ledger">
          <thead><tr><th>Seq</th><th>Time</th><th>Event</th><th>Incident</th><th>Entry hash</th><th>Previous hash</th></tr></thead>
          <tbody>
            {[...rows].reverse().map((r) => (
              <tr key={r.seq} data-bad={verify && !verify.ok && verify.first_bad_seq === r.seq ? "true" : undefined}>
                <td class="mono">{r.seq}</td>
                <td class="mono">{new Date(r.ts).toLocaleTimeString()}</td>
                <td>{r.event_type}</td>
                <td class="mono">{r.incident_id.slice(0, 8)}</td>
                <td class="mono">{r.entry_hash.slice(0, 16)}…</td>
                <td class="mono">{r.prev_hash.slice(0, 16)}…</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
