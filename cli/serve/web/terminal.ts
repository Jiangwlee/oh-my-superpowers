// Terminal: xterm + FitAddon + /ws/terminal WS, resize/PTY. Ported 1:1 from APP_HTML.
import { state, $ } from "./state.js";
import { websocketUrl } from "./api.js";

export function setSideTab(tab: string): void {
  state.sideTab = tab;
  document.querySelectorAll("[data-side-tab]").forEach((btn) => {
    btn.classList.toggle("active", (btn as HTMLElement).dataset.sideTab === tab);
  });
  $("chat-log").classList.toggle("active", tab === "chat");
  $("terminal-pane").classList.toggle("active", tab === "terminal");
  document.querySelector(".agent")!.classList.toggle("terminal-active", tab === "terminal");
  $("chat-status").textContent = tab === "terminal" ? terminalStatus() : state.sending ? "running" : "idle";
  if (tab === "terminal") {
    startTerminal();
    setTimeout(fitTerminal, 40);
  }
}

export function terminalStatus(): string {
  if (state.terminalSocket?.readyState === WebSocket.OPEN) return "terminal";
  if (state.terminalSocket?.readyState === WebSocket.CONNECTING) return "connecting";
  if (state.terminalStarted) return "closed";
  return "idle";
}

export function fitTerminal(): void {
  if (!state.terminal || !state.terminalFit) return;
  try {
    state.terminalFit.fit();
    if (state.terminalSocket?.readyState === WebSocket.OPEN) {
      state.terminalSocket.send(
        JSON.stringify({
          type: "resize",
          cols: state.terminal.cols,
          rows: state.terminal.rows,
        }),
      );
    }
  } catch (_) {}
}

// Tear down the terminal so the next connection uses the current sessionId.
// The old PTY-bound socket is closed; if the terminal tab is active we
// immediately reconnect under the new session.
export function resetTerminal(): void {
  try {
    state.terminalSocket?.close();
  } catch (_) {}
  state.terminalSocket = null;
  try {
    state.terminalResizeObserver?.disconnect();
  } catch (_) {}
  state.terminalResizeObserver = null;
  try {
    state.terminal?.dispose();
  } catch (_) {}
  state.terminal = null;
  state.terminalFit = null;
  state.terminalStarted = false;
  $("terminal").innerHTML = "";
  if (state.sideTab === "terminal") {
    startTerminal();
    setTimeout(fitTerminal, 40);
  }
}

export function startTerminal(): void {
  if (state.terminalStarted) return;
  state.terminalStarted = true;
  if (!window.Terminal || !window.FitAddon?.FitAddon) {
    $("terminal").innerHTML = '<div class="empty">xterm.js failed to load.</div>';
    $("chat-status").textContent = "error";
    return;
  }
  state.terminal = new window.Terminal({
    cursorBlink: true,
    convertEol: true,
    fontFamily: '"JetBrains Mono", "SFMono-Regular", Consolas, monospace',
    fontSize: 12,
    lineHeight: 1.25,
    theme: {
      background: "#0b0b09",
      foreground: "#f3ecdd",
      cursor: "#a4d86f",
      selectionBackground: "#38412c",
    },
  });
  state.terminalFit = new window.FitAddon.FitAddon();
  state.terminal.loadAddon(state.terminalFit);
  state.terminal.open($("terminal"));
  state.terminal.focus();
  fitTerminal();
  if (window.ResizeObserver) {
    state.terminalResizeObserver = new ResizeObserver(() => fitTerminal());
    state.terminalResizeObserver.observe($("terminal-pane"));
  }

  const socket = new WebSocket(websocketUrl(`/ws/terminal?sessionId=${encodeURIComponent(state.sessionId)}`));
  state.terminalSocket = socket;
  $("chat-status").textContent = "connecting";

  // Fence handlers to this socket: after resetTerminal() (New session) replaces
  // state.terminalSocket, late events from the old PTY must not write into the
  // new terminal or clobber its status.
  const isCurrent = (): boolean => state.terminalSocket === socket;

  state.terminal.onData((data: string) => {
    if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "input", data }));
  });
  socket.addEventListener("open", () => {
    if (!isCurrent()) return;
    $("chat-status").textContent = "terminal";
    fitTerminal();
  });
  socket.addEventListener("message", (event: MessageEvent) => {
    if (!isCurrent()) return;
    state.terminal.write(event.data);
  });
  socket.addEventListener("close", () => {
    if (!isCurrent()) return;
    $("chat-status").textContent = state.sideTab === "terminal" ? "closed" : "idle";
  });
  socket.addEventListener("error", () => {
    if (!isCurrent()) return;
    $("chat-status").textContent = "error";
  });
}
