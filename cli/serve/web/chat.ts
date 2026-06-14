// Chat: /api/chat SSE consumer + turns/timeline/steps. Ported 1:1 from APP_HTML.
import { state, $, esc } from "./state.js";
import { renderMarkdown } from "./markdown.js";
import { setMode } from "./editor.js";
import { postGenUi, scheduleGenUiFrame, resetGenUiSeal } from "./genui.js";

export function addTurn(role: string, text: string): HTMLElement {
  const article = document.createElement("article");
  article.className = `turn ${role === "User" ? "user" : "assistant"}`;
  const body =
    role === "Assistant"
      ? `<div class="assistant-md">${renderMarkdown(text || "")}</div>`
      : `<p>${esc(text)}</p>`;
  article.innerHTML = `<div class="turn-head"><span>${role}</span><span>${role === "User" ? "prompt" : "working"}</span></div><div class="turn-body">${body}</div>`;
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
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, sessionId: state.sessionId }),
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
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";
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
          input.focus();
        }
      }
    }
  } catch (err: any) {
    appendAssistant(`\n\n${err.message || err}`);
  } finally {
    state.sending = false;
    ($("send-btn") as HTMLButtonElement).disabled = false;
    $("chat-status").textContent = "idle";
    input.focus();
  }
}
