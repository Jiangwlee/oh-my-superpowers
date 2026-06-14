// Generative UI — persistent "shell" iframe, no-flicker postMessage design.
// Ported 1:1 from APP_HTML (Redline 5: invariants must not regress).
import { state } from "./state.js";

// Drop a trailing, not-yet-closed tag (e.g. "<butto") so the streamed
// partial HTML renders cleanly while it is still arriving.
export function cleanPartialHtml(html: string): string {
  return String(html || "").replace(/<[^>]*$/, "");
}

// Persistent "shell" iframe (built ONCE). A bootstrap script inside it
// receives postMessage updates and mutates head/body in place — the
// document is never re-navigated, so there is no white-flash flicker.
// This mirrors how CopilotKit drives @jetbrains/websandbox.
export const GENUI_SHELL = `<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;height:100%;background:#fff}</style></head><body></body><script>
(function(){
  function runScripts(srcDoc){
    var olds=srcDoc.querySelectorAll('script');
    // Execute scripts strictly in document order. External scripts must finish
    // loading before the next script runs, so a later inline/CDN script can rely
    // on an earlier CDN dependency, and DOMContentLoaded fires only after all run.
    function runAt(i){
      if(i>=olds.length){
        try { document.dispatchEvent(new Event('DOMContentLoaded', { bubbles: true })); } catch (e) {}
        try { window.dispatchEvent(new Event('load')); } catch (e) {}
        return;
      }
      var old=olds[i];
      var s=document.createElement('script');
      for(var k=0;k<old.attributes.length;k++){s.setAttribute(old.attributes[k].name,old.attributes[k].value);}
      if(old.src){
        s.async=false; s.defer=false;
        s.onload=function(){runAt(i+1);};
        s.onerror=function(){runAt(i+1);};
        document.body.appendChild(s);
      } else {
        s.textContent=old.textContent;
        document.body.appendChild(s);
        runAt(i+1);
      }
    }
    runAt(0);
  }
  window.addEventListener('message',function(e){
    var d=e.data; if(!d||d.__genui!==1) return;
    var doc=new DOMParser().parseFromString(d.html||'','text/html');
    document.head.innerHTML=doc.head.innerHTML;
    document.body.innerHTML=doc.body.innerHTML;
    if(d.run===1) runScripts(doc);  // only run inline <script> on final paint
  });
})();
<\/script></html>`;

// Monotonic render version. A pending (delta) frame captures the version it
// was scheduled under; if a newer render (e.g. the final gen_ui paint) bumps
// the version first, the stale scheduled post is ignored so it cannot overwrite
// the final scripted render and wipe runScripts() state.
let genUiRenderVersion = 0;

// Push the current (partial or final) HTML into the live shell, no reload.
export function postGenUi(run: boolean): void {
  // Any direct post (notably the final run=true paint) supersedes pending deltas.
  genUiRenderVersion++;
  state.genUiPending = false;
  const frame = document.getElementById("genui-frame") as HTMLIFrameElement | null;
  if (!frame || !frame.contentWindow) return;
  frame.contentWindow.postMessage(
    { __genui: 1, html: cleanPartialHtml(state.genUiHtml), run: run ? 1 : 0 },
    "*",
  );
}

// Throttle streaming updates so we don't postMessage on every token.
export function scheduleGenUiFrame(): void {
  if (state.genUiPending) return;
  state.genUiPending = true;
  const scheduledVersion = genUiRenderVersion;
  setTimeout(() => {
    // A newer render (final paint or another post) ran first — drop this stale
    // delta so it can't erase the final scripted render.
    if (!state.genUiPending || scheduledVersion !== genUiRenderVersion) return;
    state.genUiPending = false;
    postGenUi(false);
  }, 100);
}
