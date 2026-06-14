// Reusable modal dialog. One visual language for every popup in the workbench
// (directory picker, delete confirm, future dialogs) so styling never drifts.
// Markup is built here; styling lives in styles.css under `.omp-dialog`.
import { esc } from "./state.js";

export interface DialogAction {
  label: string;
  variant?: "default" | "primary" | "danger";
  // Return false to keep the dialog open; anything else closes it.
  onClick?: () => unknown;
}

export interface DialogOptions {
  title: string;
  // Body may be raw HTML text or a prebuilt element (e.g. the browser list).
  body: string | HTMLElement;
  actions: DialogAction[];
  // Called when the dialog is dismissed via scrim/Escape/close without an action.
  onDismiss?: () => void;
}

export interface DialogHandle {
  close: () => void;
  // The body container, so callers can re-render dynamic content in place.
  bodyEl: HTMLElement;
}

export function openDialog(opts: DialogOptions): DialogHandle {
  const scrim = document.createElement("div");
  scrim.className = "omp-scrim";

  const dialog = document.createElement("div");
  dialog.className = "omp-dialog";

  const head = document.createElement("div");
  head.className = "omp-dialog-head";
  head.innerHTML = `<h3>${esc(opts.title)}</h3>`;
  const closeBtn = document.createElement("button");
  closeBtn.className = "omp-dialog-close";
  closeBtn.title = "Close";
  closeBtn.textContent = "×";
  head.appendChild(closeBtn);

  const bodyEl = document.createElement("div");
  bodyEl.className = "omp-dialog-body";
  if (typeof opts.body === "string") bodyEl.innerHTML = opts.body;
  else bodyEl.appendChild(opts.body);

  const actions = document.createElement("div");
  actions.className = "omp-dialog-actions";

  let closed = false;
  const close = (): void => {
    if (closed) return;
    closed = true;
    document.removeEventListener("keydown", onKey);
    scrim.remove();
  };
  const dismiss = (): void => {
    if (closed) return;
    close();
    opts.onDismiss?.();
  };

  for (const action of opts.actions) {
    const btn = document.createElement("button");
    btn.className = `omp-dialog-btn ${action.variant || "default"}`;
    btn.textContent = action.label;
    btn.addEventListener("click", () => {
      if (action.onClick?.() === false) return; // keep open
      close();
    });
    actions.appendChild(btn);
  }

  dialog.append(head, bodyEl, actions);
  scrim.appendChild(dialog);

  closeBtn.addEventListener("click", dismiss);
  scrim.addEventListener("click", (e) => {
    if (e.target === scrim) dismiss();
  });
  const onKey = (e: KeyboardEvent): void => {
    if (e.key === "Escape") dismiss();
  };
  document.addEventListener("keydown", onKey);

  document.body.appendChild(scrim);
  return { close, bodyEl };
}

// Convenience: a yes/no confirm built on the same dialog. Resolves true only if
// the confirm action is chosen; scrim/Escape/cancel resolve false.
export function confirmDialog(opts: {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
}): Promise<boolean> {
  return new Promise((resolve) => {
    let decided = false;
    const handle = openDialog({
      title: opts.title,
      body: `<p class="omp-dialog-message">${esc(opts.message)}</p>`,
      actions: [
        {
          label: opts.cancelLabel || "Cancel",
          variant: "default",
          onClick: () => {
            decided = true;
            resolve(false);
          },
        },
        {
          label: opts.confirmLabel || "Confirm",
          variant: opts.danger ? "danger" : "primary",
          onClick: () => {
            decided = true;
            resolve(true);
          },
        },
      ],
      onDismiss: () => {
        if (!decided) resolve(false);
      },
    });
    void handle;
  });
}
