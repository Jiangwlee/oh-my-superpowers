// App state — ported 1:1 from main.py APP_HTML `state` object.

export interface ProjectInfo {
  id: string;
  name: string;
  path: string;
}

export interface EditorSnapshot {
  selectedPath: string;
  treeSelectedPath: string;
  treeSelectedType: "file" | "directory" | "";
  original: string;
  content: string;
  fileKind: "text" | "image" | "meta";
  fileSize: number;
  fileDataUrl: string;
  mode: string;
  dirty: boolean;
}

export interface AppState {
  workspace: string;
  projects: ProjectInfo[];
  currentProjectId: string;
  sessionId: string;
  // projectId -> last sessionId, so switching back to a project resumes its pi
  // session (Agent context continuity). In-memory only (NOT persisted): keeps
  // the page-local session invariant — a reload or another tab starts fresh and
  // never runs two pi processes against the same session jsonl.
  projectSessions: Record<string, string>;
  projectEditors: Record<string, EditorSnapshot>;
  selectedPath: string;
  treeSelectedPath: string;
  treeSelectedType: "file" | "directory" | "";
  chatAttachments: string[];
  original: string;
  content: string;
  fileKind: "text" | "image" | "meta";
  fileSize: number;
  fileDataUrl: string;
  mode: string;
  genUiHtml: string;
  genUiTitle: string;
  dirty: boolean;
  sending: boolean;
  // sessionId of the in-flight chat run (or "" when idle), so "New session" only
  // aborts a run that belongs to the project being reset — a background run from
  // another project keeps going.
  chatRunSession: string;
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
  projects: [],
  currentProjectId: "",
  sessionId: "",
  projectSessions: {},
  projectEditors: {},
  selectedPath: "",
  treeSelectedPath: "",
  treeSelectedType: "",
  chatAttachments: [],
  original: "",
  content: "",
  fileKind: "text",
  fileSize: 0,
  fileDataUrl: "",
  mode: "preview",
  genUiHtml: "",
  genUiTitle: "",
  dirty: false,
  sending: false,
  chatRunSession: "",
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
