// Session lifecycle. Rotating the pi session is shared by the "New" button and
// by switching projects (a project switch must not reuse the old project's
// workspace-bound session).
import { state, $, newSessionId } from "./state.js";
import { clearChat } from "./chat.js";
import { resetGenUiSeal } from "./genui.js";
import { resetTerminal } from "./terminal.js";

// Start a fresh pi session without reloading the page: rotate the sessionId,
// clear the chat transcript and reset the terminal (both are session-bound).
// File tree, editor, open file and theme are page state and are kept intact.
export function newSession(): void {
  state.chatAbort?.abort(); // stop any in-flight chat stream bound to the old session
  state.sessionId = newSessionId();
  $("session-label").textContent = `session: ${state.sessionId.slice(0, 8)}`;
  state.sending = false;
  ($("send-btn") as HTMLButtonElement).disabled = false;
  clearChat();
  resetGenUiSeal();
  resetTerminal();
  if (state.sideTab !== "terminal") $("chat-status").textContent = "idle";
}
