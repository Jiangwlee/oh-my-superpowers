// Fetch wrappers — ported 1:1 from main.py APP_HTML.

export async function api(path: string, options?: RequestInit): Promise<Response> {
  const res = await fetch(path, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res;
}

export async function loadDirectory(path: string): Promise<any> {
  const data = await (await api(`/api/tree?path=${encodeURIComponent(path || "")}`)).json();
  return data;
}

export function websocketUrl(path: string): string {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${window.location.host}${path}`;
}
