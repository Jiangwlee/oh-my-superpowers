"""Indexed DOM extraction.

Walk the page for interactive elements, assign each a per-snapshot number, and
return an LLM-readable text listing. The number -> backendNodeId mapping is
handed back so ``act`` can resolve a number to a real node via
``DOM.resolveNode``. No CSS selectors are exposed; the caller points at numbers.

Extraction runs in-page JS (DOM API), not regex over HTML.
"""

from __future__ import annotations

import os

from .cdp_client import CDPClient, CDPError

# Monotonic counter → unique per-call global name, so a concurrent /dom call or
# a page script cannot overwrite the element array between descriptor generation
# and backendNodeId extraction.
_counter = 0

# Hard ceiling on returned elements — the container's own last-resort bound, so
# a single /dom never dumps a whole aggregator page even without q/viewport
# narrowing. mindora's tool-output-cap stays a pure fallback below this.
_DEFAULT_MAX = int(os.environ.get("OMP_DOM_MAX", "200"))


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
  const rects = [];
  for (const el of document.querySelectorAll(SEL)) {
    if (seen.has(el)) continue;
    seen.add(el);
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    if (el.hidden || el.getAttribute('aria-hidden') === 'true') continue;
    const style = window.getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') continue;
    els.push(el);
    // Viewport-relative box; the bounded-subset selection (viewport / q / role)
    // runs Python-side off these numbers, so no CSS selectors leak to the caller.
    rects.push({top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right});
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
  return JSON.stringify({
    viewport: {w: window.innerWidth, h: window.innerHeight},
    elements: els.map((el, i) => ({
      tag: el.tagName.toLowerCase(),
      role: el.getAttribute('role') || '',
      type: el.getAttribute('type') || '',
      name: name(el),
      disabled: !!el.disabled,
      rect: rects[i],
    })),
  });
})()
"""


def select_survivors(
    elements: list[dict],
    viewport: dict,
    q: str | None,
    role: str | None,
    cap: int,
) -> tuple[list[int], int]:
    """Choose which elements to return, by original index, plus the pre-cap
    match count.

    Scope: when ``q`` or ``role`` is given the whole page is searched (the target
    control may be off-screen); otherwise only elements intersecting the current
    viewport are kept. The two filters, when both present, must both match.

    Returns ``(indices, matched)`` where ``indices`` are original positions in
    document order truncated to ``cap``, and ``matched`` is the in-scope count
    before truncation (drives the "more" hint).
    """
    scoped = bool(q) or bool(role)
    q_lower = q.lower() if q else None
    survivors: list[int] = []
    for i, el in enumerate(elements):
        if scoped:
            if q_lower is not None and q_lower not in el.get("name", "").lower():
                continue
            if role and el.get("role") != role and el.get("tag") != role:
                continue
        else:
            r = el.get("rect") or {}
            if not (
                r.get("top", 0) < viewport.get("h", 0)
                and r.get("bottom", 0) > 0
                and r.get("left", 0) < viewport.get("w", 0)
                and r.get("right", 0) > 0
            ):
                continue
        survivors.append(i)
    matched = len(survivors)
    return survivors[:cap], matched


async def extract(
    cdp: CDPClient,
    cdp_session_id: str,
    *,
    q: str | None = None,
    role: str | None = None,
    max_elements: int = _DEFAULT_MAX,
) -> tuple[str, dict[int, int], int]:
    """Extract a bounded subset of interactive elements from the current page.

    Args:
        cdp: Connected CDP client.
        cdp_session_id: Flattened session bound to the page target.
        q: Optional substring filter on element name (whole-page scope).
        role: Optional role/tag filter (whole-page scope).
        max_elements: Hard ceiling on returned elements.

    Returns:
        ``(listing, index_map, total)`` where ``listing`` is LLM-readable text
        (one renumbered line per returned element, with a trailing "more" hint
        when the page holds elements not shown), ``index_map`` maps each returned
        number ``0..k-1`` to a backendNodeId, and ``total`` is the whole page's
        visible interactive-element count.
    """
    global _counter
    _counter += 1
    global_name = f"__omp_els_{_counter}"

    result = await cdp.send(
        "Runtime.evaluate",
        {"expression": _collect_js(global_name), "returnByValue": True},
        session_id=cdp_session_id,
    )
    payload = _unwrap_json(result)
    elements: list[dict] = payload.get("elements", [])
    viewport: dict = payload.get("viewport", {})
    total = len(elements)

    survivors, matched = select_survivors(elements, viewport, q, role, max_elements)

    index_map: dict[int, int] = {}
    descriptors: list[dict] = []
    try:
        # Grab the live element array so we can resolve survivors to backendNodeIds.
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
            # Map original index -> live element objectId (cheap; one call). The
            # expensive per-node describeNode below runs only for survivors.
            object_ids: dict[int, str] = {}
            for prop in props.get("result", []):
                if not prop.get("name", "").isdigit():
                    continue  # skip 'length' and non-index props
                obj_id = prop.get("value", {}).get("objectId")
                if obj_id:
                    object_ids[int(prop["name"])] = obj_id

            # Renumber survivors to a contiguous 0..k-1; an element that fails to
            # resolve is skipped WITHOUT leaving a hole, so listing numbers and
            # index_map keys stay one-to-one (the click/type contract).
            next_i = 0
            for orig in survivors:
                object_id = object_ids.get(orig)
                if not object_id:
                    continue
                described = await cdp.send(
                    "DOM.describeNode",
                    {"objectId": object_id},
                    session_id=cdp_session_id,
                )
                backend = described.get("node", {}).get("backendNodeId")
                if backend is None:
                    continue
                index_map[next_i] = backend
                descriptors.append({**elements[orig], "i": next_i})
                next_i += 1
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

    listing = _format(descriptors, total, q, role, matched)
    return listing, index_map, total


def _unwrap_json(evaluate_result: dict) -> dict:
    import json

    value = evaluate_result.get("result", {}).get("value")
    if not value:
        return {}
    return json.loads(value)


def _more_hint(
    count: int, matched: int, total: int, q: str | None, role: str | None
) -> str | None:
    """Trailing guidance so a bounded listing is never a dead end (redline ③).

    Tells the agent what was withheld and how to reach it: scroll for the
    viewport default, narrow the query for a scoped search.
    """
    truncated = matched > count
    if q or role:
        label = q if q else f"role={role}"
        parts = [f'匹配 "{label}" 命中 {matched} 项']
        if truncated:
            parts.append(f"仅显示前 {count}")
        parts.append(f"全页共 {total} 项，缩小关键词或 scroll 定位")
        return "— " + "；".join(parts) + " —"
    if count >= total:
        return None  # viewport already shows every interactive element
    if truncated:
        return (
            f"— 视口内匹配 {matched} 项，仅显示前 {count}；全页共 {total} 项。"
            "scroll 或缩小范围 —"
        )
    return (
        f"— 视口内 {count} 项，全页共 {total} 项。"
        "scroll 向下揭开更多，或 /dom?q=<关键词> 定位具体控件 —"
    )


def _format(
    descriptors: list[dict],
    total: int,
    q: str | None = None,
    role: str | None = None,
    matched: int | None = None,
) -> str:
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
    count = len(descriptors)
    hint = _more_hint(count, matched if matched is not None else count, total, q, role)
    if hint:
        lines.append(hint)
    return "\n".join(lines)
