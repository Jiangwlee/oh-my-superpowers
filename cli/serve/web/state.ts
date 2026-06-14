// App state — ported 1:1 from main.py APP_HTML `state` object.

export interface AppState {
  workspace: string;
  sessionId: string;
  selectedPath: string;
  original: string;
  content: string;
  mode: string;
  genUiHtml: string;
  genUiTitle: string;
  dirty: boolean;
  sending: boolean;
  assistantEl: HTMLElement | null;
  assistantTextEl: HTMLElement | null;
  assistantRaw: string;
  toolListEl: HTMLElement | null;
  toolSteps: Map<string, HTMLElement>;
  sideTab: string;
  chatAbort: AbortController | null;
  terminal: any;
  terminalFit: any;
  terminalSocket: WebSocket | null;
  terminalStarted: boolean;
  terminalResizeObserver: ResizeObserver | null;
  genUiPending?: boolean;
  // True only when the current genUiHtml is the definitive, fully-assembled
  // document (the `gen_ui` event), so the shell's load handler knows whether to
  // run scripts. A mode switch caused by a streamed `gen_ui_delta` leaves this
  // false so partial HTML never runs scripts prematurely.
  genUiFinal?: boolean;
}

export const state: AppState = {
  workspace: "",
  sessionId: "",
  selectedPath: "",
  original: "",
  content: "",
  mode: "preview",
  genUiHtml: "",
  genUiTitle: "",
  dirty: false,
  sending: false,
  assistantEl: null,
  assistantTextEl: null,
  assistantRaw: "",
  toolListEl: null,
  toolSteps: new Map<string, HTMLElement>(),
  sideTab: "chat",
  chatAbort: null,
  terminal: null,
  terminalFit: null,
  terminalSocket: null,
  terminalStarted: false,
  terminalResizeObserver: null,
};

export const $ = (id: string): HTMLElement => document.getElementById(id)!;

export const esc = (value: unknown): string =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (ch) =>
      (({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }) as Record<string, string>)[ch],
  );

export function newSessionId(): string {
  if (crypto?.randomUUID) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export function ext(path: string): string {
  const idx = path.lastIndexOf(".");
  return idx === -1 ? "" : path.slice(idx + 1).toLowerCase();
}

export function isMarkdown(path: string): boolean {
  return ["md", "mdx", "markdown"].includes(ext(path));
}

export function isHtml(path: string): boolean {
  return ["html", "htm"].includes(ext(path));
}
