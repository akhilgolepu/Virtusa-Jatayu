import type { Entry } from "../api";

type Mark = { start: number; end: number; n: number; high: boolean };

function spansOf(entries: Entry[]): Mark[] {
  const out: Mark[] = [];
  entries.forEach((e, i) => {
    const high = e.flags.some((f) => f.severity === "high");
    const fields = e.kind === "medication" ? [e.drug, e.dose_value, e.dose_unit, e.route, e.time] : [e.procedure, e.time, e.detail];
    for (const f of fields) if (f && f.span) out.push({ start: f.span[0], end: f.span[1], n: i + 1, high });
  });
  return out.sort((a, b) => a.start - b.start);
}

// Offsets are Unicode code points (Python str indices), so slice with Array.from, never String.slice.
export function Transcript({ text, entries }: { text: string; entries: Entry[] }) {
  const chars = Array.from(text);
  const parts = [];
  let at = 0;
  for (const m of spansOf(entries)) {
    if (m.start < at) continue;
    if (m.start > at) parts.push(chars.slice(at, m.start).join(""));
    parts.push(
      <mark key={m.start} data-flag={m.high ? "high" : undefined} title={`entry ${m.n}`}>
        {chars.slice(m.start, m.end).join("")}<sup>{m.n}</sup>
      </mark>,
    );
    at = m.end;
  }
  if (at < chars.length) parts.push(chars.slice(at).join(""));
  return <p class="transcript">{parts}</p>;
}
