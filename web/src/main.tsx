import { render } from "preact";
import "@fontsource/archivo/500.css";
import "@fontsource/uncut-sans/400.css";
import "@fontsource/uncut-sans/500.css";
import "@fontsource/jetbrains-mono/400.css";
import "./tokens.css";
import "./app.css";
import { App } from "./App";

render(<App />, document.getElementById("app")!);
