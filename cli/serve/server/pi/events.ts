// Maps pi JSONL events to the SSE events the frontend consumes.
// Ported 1:1 from main.py (_extract_text_delta, _render_ui_partial_html,
// _tool_detail, _truncate, and the do_POST/_stream_pi dispatch).

export type SseEvent =
  | { type: "assistant_delta"; delta: string }
  | { type: "gen_ui_delta"; html: string }
  | { type: "gen_ui"; html: string; title: string }
  | { type: "tool_start"; id: string; name: string; detail: string }
  | { type: "tool_end"; id: string; name: string; detail: string }
  | { type: "error"; message: string }
  | { type: "done"; returncode: number };

interface PiEvent {
  type?: string;
  toolName?: unknown;
  toolCallId?: unknown;
  args?: unknown;
  message?: unknown;
  assistantMessageEvent?: {
    type?: string;
    delta?: unknown;
    toolCallId?: unknown;
    partial?: { content?: unknown };
  };
}

// Best-effort pull of the `html` value out of a (possibly incomplete) JSON
// object string. Tolerates a truncated tail (the value still streaming).
function extractHtmlFromPartialJson(buf: string): string {
  // Locate the "html" key, then read its JSON-string value, decoding escapes
  // and stopping at the first unescaped closing quote (or end of buffer).
  const keyMatch = /"html"\s*:\s*"/.exec(buf);
  if (!keyMatch) return "";
  let i = keyMatch.index + keyMatch[0].length;
  let out = "";
  while (i < buf.length) {
    const ch = buf[i];
    if (ch === "\\") {
      const next = buf[i + 1];
      if (next === undefined) break; // escape sequence still streaming
      switch (next) {
        case "n": out += "\n"; break;
        case "t": out += "\t"; break;
        case "r": out += "\r"; break;
        case "b": out += "\b"; break;
        case "f": out += "\f"; break;
        case "/": out += "/"; break;
        case '"': out += '"'; break;
        case "\\": out += "\\"; break;
        case "u": {
          const hex = buf.slice(i + 2, i + 6);
          if (hex.length < 4) return out; // unicode escape still streaming
          out += String.fromCharCode(parseInt(hex, 16));
          i += 4;
          break;
        }
        default: out += next;
      }
      i += 2;
      continue;
    }
    if (ch === '"') break; // end of html string value
    out += ch;
    i += 1;
  }
  return out;
}

function truncate(value: string, limit = 160): string {
  const compact = value.trim().split(/\s+/).join(" ");
  if (compact.length <= limit) return compact;
  return `${compact.slice(0, limit - 3)}...`;
}

function extractTextDelta(event: PiEvent): string {
  const update = event.assistantMessageEvent || {};
  if (update.type === "text_delta") return String(update.delta ?? "");
  return "";
}

// Pull the partially-streamed `html` arg out of a toolcall_delta event.
// Tool-call argument streams may arrive as raw JSON/string fragments before a
// full `arguments` object exists; we accumulate fragments by toolCallId and
// emit the html as soon as it can be recovered from the buffer.
function renderUiPartialHtml(event: PiEvent, renderArgBuffers: Map<string, string>): string {
  const update = event.assistantMessageEvent || {};
  if (update.type !== "toolcall_delta") return "";
  const key = String(update.toolCallId ?? event.toolCallId ?? "");
  const partial = update.partial || {};
  const content = Array.isArray(partial.content) ? partial.content : [];
  let html = "";
  for (const block of content) {
    if (!block || typeof block !== "object") continue;
    const args = (block as Record<string, unknown>).arguments;
    if (args && typeof args === "object" && typeof (args as Record<string, unknown>).html === "string") {
      // Already-materialized arguments object: html is directly available.
      html = (args as Record<string, unknown>).html as string;
    } else if (typeof args === "string" && args) {
      // Raw partial argument text. Streams come in two shapes: incremental tail
      // fragments, or cumulative snapshots (each delta = full text so far). A
      // cumulative snapshot already contains the JSON opening, so reset the
      // buffer to it; otherwise append it as the next fragment.
      const prev = renderArgBuffers.get(key) || "";
      const isCumulative = /^\s*[{[]/.test(args);
      const buf = isCumulative ? args : prev + args;
      renderArgBuffers.set(key, buf);
      const recovered = extractHtmlFromPartialJson(buf);
      if (recovered) html = recovered;
    }
  }
  return html;
}

function toolDetail(toolName: string, args: unknown): string {
  if (!args || typeof args !== "object" || Array.isArray(args)) return "";
  const a = args as Record<string, unknown>;
  const lowered = toolName.toLowerCase();
  const pathKeys = ["file_path", "path", "absolute_path", "filename"];
  const cmdKeys = ["command", "cmd", "script"];
  const pick = (keys: string[]): string => {
    for (const key of keys) {
      const value = a[key];
      if (typeof value === "string" && value) return truncate(value);
    }
    return "";
  };
  if (lowered === "read" || lowered === "file_read") {
    const v = pick(pathKeys);
    if (v) return v;
  }
  if (lowered === "bash" || lowered === "shell" || lowered === "exec" || lowered === "exec_command") {
    const v = pick(cmdKeys);
    if (v) return v;
  }
  if (lowered === "edit" || lowered === "write" || lowered === "replace") {
    const v = pick(pathKeys);
    if (v) return v;
  }
  const parts: string[] = [];
  for (const [key, value] of Object.entries(a)) {
    const rendered = typeof value === "string" ? value : JSON.stringify(value);
    parts.push(`${key}=${truncate(rendered, 80)}`);
    if (parts.length >= 3) break;
  }
  return truncate(parts.join(" "));
}

// Parse one pi JSONL line into zero or more SSE events. Returns `done: true`
// when an agent_end was seen so the caller can stop the stream.
// A pi-event mapper bound to a single chat stream. The render_ui arg buffers
// live inside the mapper instance so concurrent /api/chat streams never share
// partial tool-call state.
export interface PiLineMapper {
  mapPiLine(raw: string): { events: SseEvent[]; done: boolean };
}

export function createPiLineMapper(): PiLineMapper {
  // Accumulates streamed render_ui tool-call `arguments` fragments keyed by
  // toolCallId, scoped to this stream. Argument deltas can arrive as partial
  // JSON/string fragments long before a complete `arguments` object
  // materializes, so we buffer the raw text and best-effort extract the `html`
  // field as it grows.
  const renderArgBuffers = new Map<string, string>();
  // Latest complete render_ui html seen during streaming. The materialized-
  // arguments delta shape never touches renderArgBuffers, and message_update /
  // tool_execution_end can carry different toolCallId keys, so a single
  // stream-scoped holder (one render_ui per turn is the norm) reliably lets
  // tool_execution_end recover the final html and emit the run=true gen_ui.
  const renderState = { lastHtml: "", lastTitle: "" };
  return { mapPiLine: (raw) => mapPiLine(raw, renderArgBuffers, renderState) };
}

function mapPiLine(
  raw: string,
  renderArgBuffers: Map<string, string>,
  renderState: { lastHtml: string; lastTitle: string },
): { events: SseEvent[]; done: boolean } {
  const line = raw.trim();
  if (!line) return { events: [], done: false };
  let event: PiEvent;
  try {
    event = JSON.parse(line) as PiEvent;
  } catch {
    return { events: [], done: false };
  }
  const out: SseEvent[] = [];
  const t = event.type;

  if (t === "message_update") {
    const partialHtml = renderUiPartialHtml(event, renderArgBuffers);
    if (partialHtml) {
      renderState.lastHtml = partialHtml;
      out.push({ type: "gen_ui_delta", html: partialHtml });
    }
    const delta = extractTextDelta(event);
    if (delta) out.push({ type: "assistant_delta", delta });
  } else if (t === "tool_execution_start") {
    const name = String(event.toolName ?? "tool");
    // The definitive (run=true) gen_ui is emitted exactly once on
    // tool_execution_end (emitting here too would re-run scripts twice). But pi
    // carries the full html on START, not END, so capture it here as the
    // fallback the end uses — this also covers fast streams with no toolcall_delta.
    if (name === "render_ui") {
      const a = event.args;
      if (a && typeof a === "object" && !Array.isArray(a)) {
        const rec = a as Record<string, unknown>;
        if (typeof rec.html === "string") renderState.lastHtml = rec.html;
        if (typeof rec.title === "string") renderState.lastTitle = rec.title;
      }
    }
    out.push({
      type: "tool_start",
      id: String(event.toolCallId ?? name),
      name,
      detail: toolDetail(name, event.args),
    });
  } else if (t === "tool_execution_end") {
    const name = String(event.toolName ?? "tool");
    // For render_ui whose args streamed in only via toolcall_delta, the
    // gen_ui_delta frames painted with run=false but no final script-running
    // render was ever emitted. Emit the definitive gen_ui here from the
    // materialized args, or as a fallback from the accumulated arg buffer, so
    // the frontend runs embedded scripts and re-dispatches DOMContentLoaded.
    if (name === "render_ui") {
      const key = String(event.toolCallId ?? name);
      const args = event.args;
      let html = "";
      let title = "";
      if (args && typeof args === "object" && !Array.isArray(args)) {
        const a = args as Record<string, unknown>;
        if (typeof a.html === "string") html = a.html;
        if (typeof a.title === "string") title = a.title;
      }
      if (!html) {
        const buf = renderArgBuffers.get(key);
        if (buf) {
          try {
            const parsed = JSON.parse(buf) as Record<string, unknown>;
            if (typeof parsed.html === "string") html = parsed.html;
            if (!title && typeof parsed.title === "string") title = parsed.title;
          } catch {
            // Buffer not yet complete JSON: best-effort recover the html value.
            html = extractHtmlFromPartialJson(buf);
          }
        }
      }
      // Materialized-arguments streams never fill the buffer; fall back to the
      // last complete html seen during the gen_ui_delta phase so the definitive
      // run=true paint (which runs scripts/attaches listeners) is always emitted.
      if (!html) html = renderState.lastHtml;
      if (!title) title = renderState.lastTitle;
      if (html) out.push({ type: "gen_ui", html, title });
      renderArgBuffers.delete(key);
      renderState.lastHtml = "";
      renderState.lastTitle = "";
    }
    out.push({
      type: "tool_end",
      id: String(event.toolCallId ?? name),
      name,
      detail: toolDetail(name, event.args),
    });
  } else if (t === "error") {
    out.push({ type: "error", message: String(event.message ?? "pi error") });
  } else if (t === "agent_end") {
    renderArgBuffers.clear(); // drop per-turn render_ui arg accumulators
    renderState.lastHtml = "";
    renderState.lastTitle = "";
    out.push({ type: "done", returncode: 0 });
    return { events: out, done: true };
  }
  return { events: out, done: false };
}

export { truncate };
