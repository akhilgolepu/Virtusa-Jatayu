import { useEffect, useState } from "preact/hooks";

// Minimal history router: the server returns the app for every non-API path.
export function navigate(path: string) {
  if (path !== location.pathname) history.pushState(null, "", path);
  dispatchEvent(new PopStateEvent("popstate"));
}

export function usePath(): string {
  const [path, setPath] = useState(location.pathname);
  useEffect(() => {
    const on = () => setPath(location.pathname);
    addEventListener("popstate", on);
    return () => removeEventListener("popstate", on);
  }, []);
  return path;
}

export function link(path: string) {
  return {
    href: path,
    onClick: (e: MouseEvent) => {
      if (e.metaKey || e.ctrlKey || e.button !== 0) return;
      e.preventDefault();
      navigate(path);
    },
  };
}
