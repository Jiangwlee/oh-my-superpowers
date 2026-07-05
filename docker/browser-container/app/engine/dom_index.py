"""Indexed DOM extraction.

Walk the page for interactive elements, assign each a per-snapshot number, and
return an LLM-readable text listing. The number -> backendNodeId mapping is
handed back so ``act`` can resolve a number to a real node via
``DOM.resolveNode``. No CSS selectors are exposed; the caller points at numbers.

Extraction runs in-page JS (DOM API), not regex over HTML.
"""

from __future__ import annotations

from .cdp_client import CDPClient, CDPError

# Monotonic counter → unique per-call global name, so a concurrent /dom call or
# a page script cannot overwrite the element array between descriptor generation
# and backendNodeId extraction.
_counter = 0


def _collect_js(global_name: str) -> str:
    """Build the collector JS, stashing elements under a unique global."""
    return _COLLECT_JS_TEMPLATE.replace("__OMP_GLOBAL__", global_name)


# Collects interactive elements into ``window[<unique>]`` (same order as the
# returned descriptors) and returns a JSON array of descriptors. Visibility is
# checked so hidden/zero-size controls are skipped.
_COLLECT_JS_TEMPLATE = r"""
(() => {
  const SEL = [
    'a[href]', 'button', 'input', 'select', 'textarea',
    '[role=button]', '[role=link]', '[role=tab]', '[role=menuitem]',
    '[role=checkbox]', '[role=radio]', '[onclick]',
    '[contenteditable=""]', '[contenteditable=true]', '[tabindex]'
  ].join(',');
  const seen = new Set();
  const els = [];
  for (const el of document.querySelectorAll(SEL)) {
    if (seen.has(el)) continue;
    seen.add(el);
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    if (el.hidden || el.getAttribute('aria-hidden') === 'true') continue;
    const style = window.getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') continue;
    els.push(el);
  }
  window.__OMP_GLOBAL__ = els;
  const name = (el) => {
    // A leaf control (no interactive descendant) can safely use its full text,
    // covering the common <button><span>登录</span></button> case. A wrapper
    // that contains other interactive elements (e.g. a <li> holding several
    // links) uses only its own direct text nodes, so it does not swallow the
    // whole subtree's text into one noisy line.
    const ownText = [...el.childNodes]
      .filter(n => n.nodeType === 3)
      .map(n => n.textContent).join('').trim();
    const text = el.querySelector(SEL)
      ? ownText
      : (el.innerText || el.textContent || '').trim();
    return (
      el.getAttribute('aria-label') ||
      text ||
      el.getAttribute('placeholder') ||
      el.getAttribute('title') ||
      el.value || ''
    ).replace(/\s+/g, ' ').slice(0, 120);
  };
  return JSON.stringify(els.map((el, i) => ({
    i,
    tag: el.tagName.toLowerCase(),
    role: el.getAttribute('role') || '',
    type: el.getAttribute('type') || '',
    name: name(el),
    disabled: !!el.disabled,
  })));
})()
"""


async def extract(cdp: CDPClient, cdp_session_id: str) -> tuple[str, dict[int, int]]:
    """Extract interactive elements from the current page.

    Args:
        cdp: Connected CDP client.
        cdp_session_id: Flattened session bound to the page target.

    Returns:
        ``(listing, index_map)`` where ``listing`` is LLM-readable text
        (one line per element) and ``index_map`` maps each number to a
        backendNodeId for later resolution.
    """
    global _counter
    _counter += 1
    global_name = f"__omp_els_{_counter}"

    result = await cdp.send(
        "Runtime.evaluate",
        {"expression": _collect_js(global_name), "returnByValue": True},
        session_id=cdp_session_id,
    )
    descriptors = _unwrap_json(result)

    index_map: dict[int, int] = {}
    try:
        # Grab the live element array so we can resolve each to a backendNodeId.
        arr = await cdp.send(
            "Runtime.evaluate",
            {"expression": f"window.{global_name}", "returnByValue": False},
            session_id=cdp_session_id,
        )
        arr_object_id = arr["result"].get("objectId")
        if arr_object_id:
            props = await cdp.send(
                "Runtime.getProperties",
                {"objectId": arr_object_id, "ownProperties": True},
                session_id=cdp_session_id,
            )
            for prop in props.get("result", []):
                if not prop.get("name", "").isdigit():
                    continue  # skip 'length' and non-index props
                idx = int(prop["name"])
                obj = prop.get("value", {})
                object_id = obj.get("objectId")
                if not object_id:
                    continue
                described = await cdp.send(
                    "DOM.describeNode",
                    {"objectId": object_id},
                    session_id=cdp_session_id,
                )
                backend = described.get("node", {}).get("backendNodeId")
                if backend is not None:
                    index_map[idx] = backend
    finally:
        # Drop the temporary global so it does not leak across snapshots. Never
        # let cleanup failure mask the real extraction error (e.g. a timeout).
        try:
            await cdp.send(
                "Runtime.evaluate",
                {"expression": f"delete window.{global_name}"},
                session_id=cdp_session_id,
            )
        except CDPError:
            pass

    listing = _format(descriptors)
    return listing, index_map


def _unwrap_json(evaluate_result: dict) -> list[dict]:
    import json

    value = evaluate_result.get("result", {}).get("value")
    if not value:
        return []
    return json.loads(value)


def _format(descriptors: list[dict]) -> str:
    lines = []
    for d in descriptors:
        tag = d["tag"]
        if d["type"]:
            tag = f"{tag}:{d['type']}"
        label = f"[{d['i']}] <{tag}>"
        if d["role"]:
            label += f" role={d['role']}"
        if d["name"]:
            label += f' "{d["name"]}"'
        if d["disabled"]:
            label += " (disabled)"
        lines.append(label)
    return "\n".join(lines)
