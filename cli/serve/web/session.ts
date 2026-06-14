// Session lifecycle. Rotating the pi session is shared by the "New" button and
// by switching projects (a project switch must not reuse the old project's
// workspace-bound session).
import { state, $, newSessionId } from "./state.js";
import { clearChat } from "./chat.js";
import { resetGenUiSeal } from "./genui.js";
import { resetTerminal } from "./terminal.js";

// Bind the page to a given pi session id and reset the session-bound surfaces
// (chat transcript, Gen UI seal, terminal). The on-screen transcript is always
// cleared — resuming a session restores Agent context via pi --session, not the
// rendered history. File tree, editor, open file and theme are page state and
// are kept intact.
export function bindSession(sessionId: string): void {
  // NOTE: does NOT abort an in-flight chat. Switching projects must let a
  // running agent finish in the background and persist to its session jsonl;
  // killing it here would lose the response (only the user turn survives).
  state.sessionId = sessionId;
  $("session-label").textContent = `session: ${sessionId.slice(0, 8)}`;
  state.sending = false;
  ($("send-btn") as HTMLButtonElement).disabled = false;
  clearChat();
  resetGenUiSeal();
  resetTerminal();
  if (state.sideTab !== "terminal") $("chat-status").textContent = "idle";
}

// Start a fresh pi session for the current project (the "New" button). The fresh
// id replaces the project's remembered session so switching away and back
// resumes this new one, not the discarded one.
export function newSession(): void {
  // Explicit stop: abort the run only if it belongs to the current project, so a
  // background run from another project is not killed.
  if (state.chatAbort && state.chatRunSession === state.sessionId) state.chatAbort.abort();
  const sessionId = newSessionId();
  if (state.currentProjectId) state.projectSessions[state.currentProjectId] = sessionId;
  bindSession(sessionId);
}
