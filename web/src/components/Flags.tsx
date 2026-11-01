import type { Flag } from "../api";

const ICON = { high: "▲", medium: "△", low: "○" } as const;
const WORD = { high: "Check", medium: "Note", low: "Info" } as const;

// Severity is carried by icon + word + border, never by colour alone.
export function Flags({ flags }: { flags: Flag[] }) {
  if (!flags.length) return null;
  return (
    <ul class="flags" role="list" style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {flags.map((f) => (
        <li class="flag" data-severity={f.severity} key={f.code + f.field}>
          <span class="icon" aria-hidden="true">{ICON[f.severity]}</span>
          <span><span class="sr-only">{WORD[f.severity]}: </span><code>{f.code.replaceAll("_", " ")}</code> — {f.message}</span>
        </li>
      ))}
    </ul>
  );
}
