// Chat: /api/chat SSE consumer + turns/timeline/steps. Ported 1:1 from APP_HTML.
import { state, $, esc } from "./state.js";
import { renderMarkdown } from "./markdown.js";
import { setMode } from "./editor.js";
import { postGenUi, scheduleGenUiFrame, resetGenUiSeal } from "./genui.js";
import { refreshTree } from "./tree.js";
import { api, withProject } from "./api.js";

export function addTurn(role: string, text: string): HTMLElement {
  const article = document.createElement("article");
  article.className = `turn ${role === "User" ? "user" : "assistant"}`;
  const body =
    role === "Assistant"
      ? `<div class="assistant-md">${renderMarkdown(text || "")}</div>`
      : `<p>${esc(text)}</p>`;
  const status =
    role === "User"
      ? "prompt"
      : `<span class="working"><i></i><i></i><i></i></span>`;
  article.innerHTML = `<div class="turn-head"><span>${role}</span><span class="turn-status">${status}</span></div><div class="turn-body">${body}</div>`;
  $("chat-log").appendChild(article);
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
  return article;
}

export function startAssistantTurn(): void {
  const article = addTurn("Assistant", "");
  state.assistantEl = article;
  state.assistantTextEl = article.querySelector(".assistant-md");
  state.assistantRaw = "";
  const timeline = document.createElement("div");
  timeline.className = "timeline";
  article.querySelector(".turn-body")!.insertBefore(timeline, state.assistantTextEl);
  state.toolListEl = timeline;
}

export function appendAssistant(delta: string): void {
  if (!state.assistantTextEl) startAssistantTurn();
  state.assistantRaw += delta;
  state.assistantTextEl!.innerHTML = renderMarkdown(state.assistantRaw);
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
}

export function addStep(text: string, done = false): HTMLElement {
  if (!state.toolListEl) startAssistantTurn();
  const step = document.createElement("div");
  step.className = `step ${done ? "done" : "patch"}`;
  step.textContent = text;
  state.toolListEl!.appendChild(step);
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
  return step;
}

// Clear the chat transcript and per-turn assistant/tool state. Used when
// starting a new session so the old conversation's turns do not linger.
export function clearChat(): void {
  $("chat-log").innerHTML = "";
  state.assistantEl = null;
  state.assistantTextEl = null;
  state.assistantRaw = "";
  state.toolListEl = null;
  state.toolSteps.clear();
}

// Repaint a resumed session's past turns into the chat panel. pi keeps the
// real context via --session; this only restores what the user can see. Each
// turn is static (assistant turns show "done", not the animated working state).
export function renderHistoryTurns(turns: { role: string; text: string }[]): void {
  clearChat();
  for (const turn of turns) {
    const role = turn.role === "user" ? "User" : "Assistant";
    const article = addTurn(role, turn.text);
    if (role === "Assistant") {
      const status = article.querySelector(".turn-status");
      if (status) status.textContent = "done";
    }
  }
}

// Fetch a session's past turns and repaint them. Best-effort: a missing or
// unreadable session leaves a clean panel. Shared by project-switch resume and
// by background-run completion.
export async function loadSessionHistory(sessionId: string): Promise<void> {
  try {
    const data = await (await api(`/api/session?sessionId=${encodeURIComponent(sessionId)}`)).json();
    if (Array.isArray(data.turns)) renderHistoryTurns(data.turns);
  } catch {
    /* leave the cleared panel as-is */
  }
}

export async function sendMessage(): Promise<void> {
  const input = $("chat-input") as HTMLTextAreaElement;
  const message = input.value.trim();
  if (!message || state.sending) return;
  state.sending = true;
  resetGenUiSeal(); // new turn: allow a fresh Gen UI render to paint partials again
  ($("send-btn") as HTMLButtonElement).disabled = true;
  $("chat-status").textContent = "running";
  addTurn("User", message);
  startAssistantTurn();
  input.value = "";
  // Fence this turn to the session it started in: if New session rotates the id
  // (or aborts), stale events from this stream are ignored and the fetch stops.
  const turnSession = state.sessionId;
  const abort = new AbortController();
  state.chatAbort = abort;
  state.chatRunSession = turnSession;
  try {
    const res = await fetch(withProject("/api/chat"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, sessionId: turnSession }),
      signal: abort.signal,
    });
    if (!res.ok) {
      throw new Error((await res.text()) || `HTTP ${res.status}`);
    }
    if (!res.body) {
      throw new Error("Streaming response body is unavailable.");
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    // Once the user switches away from this turn's session, stop rendering but
    // keep draining the stream so pi runs to completion and persists to its
    // jsonl — the background run is never killed. We do not re-attach a
    // mid-stream turn; the transcript is reloaded from disk on return instead.
    let detached = false;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";
      if (!detached && state.sessionId !== turnSession) detached = true;
      if (detached) continue; // drain silently, render nothing
      for (const chunk of chunks) {
        const line = chunk.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        const event = JSON.parse(line.slice(6));
        if (event.type === "assistant_delta") appendAssistant(event.delta || "");
        if (event.type === "tool_start") {
          const label = [event.name || "tool", event.detail].filter(Boolean).join(": ");
          state.toolSteps.set(event.id || label, addStep(label));
        }
        if (event.type === "tool_end") {
          const id = event.id || event.name || "tool";
          const step = state.toolSteps.get(id);
          if (step) {
            step.classList.remove("patch");
            step.classList.add("done");
          } else {
            const label = [event.name || "tool done", event.detail].filter(Boolean).join(": ");
            addStep(label, true);
          }
        }
        if (event.type === "gen_ui_delta") {
          state.genUiHtml = event.html || "";
          state.genUiFinal = false; // partial stream — shell must not run scripts yet
          if (state.mode !== "genui") setMode("genui"); // build shell once, paint partial (run=false)
          else scheduleGenUiFrame();
        }
        if (event.type === "gen_ui") {
          // Definitive, fully-assembled HTML — final paint that also runs scripts.
          state.genUiHtml = event.html || "";
          state.genUiTitle = event.title || "";
          state.genUiFinal = true; // shell's load handler may now run scripts
          addStep(`render_ui${event.title ? ": " + event.title : ""}`, true);
          if (state.mode !== "genui") setMode("genui"); // builds shell; load handler runs scripts
          else postGenUi(true); // already live: run scripts in place
        }
        if (event.type === "error") appendAssistant(`\n\n${event.message}`);
        if (event.type === "done") {
          state.sending = false;
          ($("send-btn") as HTMLButtonElement).disabled = false;
          $("chat-status").textContent = "idle";
          // Turn finished: replace the animated working dots with a static label.
          const status = state.assistantEl?.querySelector(".turn-status");
          if (status) status.textContent = "done";
          input.focus();
          // The turn may have created/edited/deleted files: refresh the tree,
          // restoring expanded dirs so the view does not collapse each turn.
          refreshTree().catch(() => {});
        }
      }
    }
    // The run finished. If it completed while detached and the user is back on
    // this session, repaint the now-complete transcript from disk.
    if (detached && state.sessionId === turnSession) {
      await loadSessionHistory(turnSession);
      refreshTree().catch(() => {});
    }
  } catch (err: any) {
    // An abort (New session) or a session rotation is not an error to surface.
    if (err?.name !== "AbortError" && state.sessionId === turnSession) {
      appendAssistant(`\n\n${err.message || err}`);
    }
  } finally {
    if (state.chatAbort === abort) state.chatAbort = null;
    if (state.chatRunSession === turnSession) state.chatRunSession = "";
    // Only reset shared UI if this turn still owns the session; otherwise a newer
    // turn (after New session) is in control and must not be disturbed.
    if (state.sessionId === turnSession) {
      state.sending = false;
      ($("send-btn") as HTMLButtonElement).disabled = false;
      $("chat-status").textContent = "idle";
      input.focus();
    }
  }
}
