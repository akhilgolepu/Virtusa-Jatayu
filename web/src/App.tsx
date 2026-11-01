import { useEffect, useState } from "preact/hooks";
import { api, DISCLAIMER } from "./api";
import { link, usePath } from "./router";
import { Capture } from "./screens/Capture";
import { Incidents } from "./screens/Incidents";
import { Audit } from "./screens/Audit";
import { Record } from "./screens/Record";

type Theme = "dark" | "light";

function readTheme(): Theme {
  try {
    const saved = localStorage.getItem("jatayu-theme");
    if (saved === "dark" || saved === "light") return saved;
  } catch { /* storage may be blocked */ }
  return matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

const NAV: [string, string][] = [["/", "Capture"], ["/incidents", "Incidents"], ["/audit", "Audit"], ["/record", "Record"]];

export function App() {
  const path = usePath();
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [device, setDevice] = useState<string>("…");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("jatayu-theme", theme); } catch { /* ignore */ }
  }, [theme]);
  useEffect(() => { api.health().then((h) => setDevice(h.asr_device)).catch(() => setDevice("offline?")); }, []);

  const section = path === "/" ? "/" : "/" + path.split("/")[1];
  let screen;
  if (section === "/incidents") screen = <Incidents id={path.split("/")[2]} />;
  else if (section === "/audit") screen = <Audit />;
  else if (section === "/record") screen = <Record />;
  else screen = <Capture />;

  return (
    <>
      <header class="topbar">
        <div class="shell">
          <a class="wordmark" {...link("/")}>Jatayu</a>
          <nav class="nav" aria-label="Main">
            {NAV.map(([href, label]) => (
              <a key={href} {...link(href)} aria-current={section === href ? "page" : undefined}>{label}</a>
            ))}
          </nav>
          <span class="status-chip">offline · asr {device}</span>
          <button class="btn btn-ghost" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                  aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>
      <main class="shell">{screen}</main>
      <footer class="shell">{DISCLAIMER}</footer>
    </>
  );
}
