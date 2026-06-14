// Markdown rendering — marked wrapper with inline fallback. Ported 1:1 from APP_HTML.
import { esc } from "./state.js";

declare global {
  interface Window {
    marked?: any;
    Terminal?: any;
    FitAddon?: any;
  }
}

export function renderMarkdown(markdown: string): string {
  if (window.marked) {
    window.marked.setOptions({ gfm: true, breaks: false });
    return window.marked.parse(markdown);
  }
  return renderMarkdownFallback(markdown);
}

function renderMarkdownFallback(markdown: string): string {
  const lines = markdown.split(/\r?\n/);
  const out: string[] = [];
  let inCode = false;
  let listOpen = false;
  for (const raw of lines) {
    const line = raw.replace(/\s+$/, "");
    if (line.startsWith("```")) {
      if (inCode) out.push("</code></pre>");
      else out.push("<pre><code>");
      inCode = !inCode;
      continue;
    }
    if (inCode) {
      out.push(esc(raw) + "\n");
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      if (!listOpen) {
        out.push("<ul>");
        listOpen = true;
      }
      out.push(`<li>${inlineMd(line.replace(/^\s*[-*]\s+/, ""))}</li>`);
      continue;
    }
    if (listOpen) {
      out.push("</ul>");
      listOpen = false;
    }
    if (line.startsWith("# ")) out.push(`<h1>${inlineMd(line.slice(2))}</h1>`);
    else if (line.startsWith("## ")) out.push(`<h2>${inlineMd(line.slice(3))}</h2>`);
    else if (line.startsWith("### ")) out.push(`<h3>${inlineMd(line.slice(4))}</h3>`);
    else if (line.startsWith("> ")) out.push(`<blockquote>${inlineMd(line.slice(2))}</blockquote>`);
    else if (!line.trim()) out.push("");
    else out.push(`<p>${inlineMd(line)}</p>`);
  }
  if (listOpen) out.push("</ul>");
  if (inCode) out.push("</code></pre>");
  return out.join("\n") || '<div class="empty">No preview content.</div>';
}

function inlineMd(text: string): string {
  return esc(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
}
