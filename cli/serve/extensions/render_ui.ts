/**
 * render_ui — Generative UI tool for `omp serve`.
 *
 * A pi extension that registers a single `render_ui` tool. The tool is an
 * "envelope" (CopilotKit-style): the LLM puts a COMPLETE HTML document into the
 * tool ARGUMENTS; the handler is a no-op that only confirms. The serve backend
 * intercepts the tool call's streamed args and renders the HTML in a sandboxed
 * <iframe> in the middle "Gen UI" panel.
 *
 * Loaded via `pi --extension <this file>` (jiti loads the .ts directly; typebox
 * and @earendil-works/pi-coding-agent are provided as bundled virtual modules,
 * so this file resolves its imports from any location).
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const RENDER_UI_PARAMS = Type.Object({
  title: Type.Optional(
    Type.String({ description: "Short title for the generated UI panel." }),
  ),
  html: Type.String({
    description:
      "A COMPLETE, self-contained HTML document. Inline <style> and <script> " +
      "are allowed. It is rendered in a sandboxed iframe (no same-origin access), " +
      "so do not use localStorage/cookies/fetch to same-origin; load any libraries " +
      "from a CDN via <script>/<link> tags.",
  }),
});

export default function renderUiExtension(pi: ExtensionAPI) {
  // Register at top level so it works in `-p`/json (print) mode too.
  pi.registerTool({
    name: "render_ui",
    label: "Render UI",
    description:
      "Render a generative UI for the user. Pass a COMPLETE, self-contained HTML " +
      "document (inline CSS/JS allowed). It is shown in a sandboxed iframe in the " +
      "middle 'Gen UI' panel, NOT in chat. Use this whenever the user asks to build, " +
      "show, visualize, prototype, or design any interface, widget, chart, form, " +
      "dashboard, game, or page.",
    promptSnippet:
      "Use render_ui to display any visual/interactive UI as a full HTML document.",
    promptGuidelines: [
      "When the user asks for any UI, widget, visualization, form, or page, call render_ui with a complete HTML document instead of describing it in text.",
      "The HTML runs in a sandboxed iframe; inline all CSS/JS and load libraries from a CDN if needed.",
      "Prefer a single render_ui call carrying the whole document.",
    ],
    parameters: RENDER_UI_PARAMS,
    async execute(_toolCallId, params) {
      const bytes = (params.html ?? "").length;
      return {
        content: [
          { type: "text", text: `Rendered UI in the Gen UI panel (${bytes} bytes).` },
        ],
        details: { bytes, title: params.title ?? null },
      };
    },
  });
}
