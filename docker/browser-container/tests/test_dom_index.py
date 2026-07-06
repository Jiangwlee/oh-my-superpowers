# file: tests/test_dom_index.py
# role: unit tests for the /dom bounded-subset logic — viewport/q/role selection,
#       renumbering, "more" hint, and extract() wiring. Pure logic + a scripted
#       FakeCDP; no live browser.
from __future__ import annotations

import asyncio
import json

import pytest

from app.engine import dom_index
from app.engine.dom_index import _format, _more_hint, extract, select_survivors

VIEWPORT = {"w": 1000, "h": 800}


def _el(name="", tag="button", role="", type="", disabled=False, rect=None):
    return {
        "tag": tag,
        "role": role,
        "type": type,
        "name": name,
        "disabled": disabled,
        "rect": rect or {"top": 10, "bottom": 30, "left": 10, "right": 100},
    }


def _in(top, bottom, left=10, right=100):
    return {"top": top, "bottom": bottom, "left": left, "right": right}


# -- select_survivors: viewport (default scope) ------------------------------

def test_viewport_keeps_only_intersecting():
    els = [
        _el("above", rect=_in(top=-50, bottom=-10)),   # fully above → drop
        _el("onscreen", rect=_in(top=100, bottom=140)),  # in view → keep
        _el("below", rect=_in(top=900, bottom=940)),   # below 800 → drop
        _el("straddle-top", rect=_in(top=-10, bottom=20)),  # crosses 0 → keep
    ]
    idx, matched = select_survivors(els, VIEWPORT, q=None, role=None, cap=200)
    assert idx == [1, 3]
    assert matched == 2


def test_viewport_horizontal_offscreen_dropped():
    els = [
        _el("left-off", rect=_in(top=100, bottom=140, left=-200, right=-10)),
        _el("right-off", rect=_in(top=100, bottom=140, left=1100, right=1300)),
        _el("in", rect=_in(top=100, bottom=140, left=10, right=100)),
    ]
    idx, matched = select_survivors(els, VIEWPORT, q=None, role=None, cap=200)
    assert idx == [2]


# -- select_survivors: query scope (whole page, ignores viewport) ------------

def test_q_matches_name_substring_case_insensitive_whole_page():
    els = [
        _el("登录", rect=_in(top=-999, bottom=-900)),   # offscreen but matches
        _el("Search Box", rect=_in(top=100, bottom=140)),
        _el("注销", rect=_in(top=100, bottom=140)),
    ]
    idx, matched = select_survivors(els, VIEWPORT, q="search", role=None, cap=200)
    assert idx == [1]
    assert matched == 1


def test_role_filter_matches_role_or_tag():
    els = [
        _el("a", tag="a", role="", rect=_in(top=100, bottom=140)),
        _el("tab1", tag="div", role="tab", rect=_in(top=100, bottom=140)),
        _el("btn", tag="button", role="", rect=_in(top=100, bottom=140)),
    ]
    idx, _ = select_survivors(els, VIEWPORT, q=None, role="tab", cap=200)
    assert idx == [1]
    idx, _ = select_survivors(els, VIEWPORT, q=None, role="button", cap=200)
    assert idx == [2]  # matched by tag


def test_q_and_role_both_must_match():
    els = [
        _el("login tab", tag="div", role="tab", rect=_in(top=100, bottom=140)),
        _el("login btn", tag="button", role="", rect=_in(top=100, bottom=140)),
    ]
    idx, _ = select_survivors(els, VIEWPORT, q="login", role="tab", cap=200)
    assert idx == [0]


# -- select_survivors: hard cap ----------------------------------------------

def test_cap_truncates_but_reports_full_matched():
    els = [_el(f"b{i}", rect=_in(top=100, bottom=140)) for i in range(10)]
    idx, matched = select_survivors(els, VIEWPORT, q=None, role=None, cap=3)
    assert idx == [0, 1, 2]        # document order, first N
    assert matched == 10           # pre-cap scope count preserved for the hint


# -- _more_hint ---------------------------------------------------------------

def test_hint_none_when_everything_visible():
    # viewport scope, nothing hidden, nothing truncated
    assert _more_hint(count=5, matched=5, total=5, q=None, role=None) is None


def test_hint_viewport_when_offscreen_exists():
    h = _more_hint(count=5, matched=5, total=40, q=None, role=None)
    assert h is not None
    assert "40" in h and "5" in h
    assert "scroll" in h.lower()


def test_hint_query_scope_mentions_matched_and_total():
    h = _more_hint(count=2, matched=2, total=3354, q="登录", role=None)
    assert "2" in h and "3354" in h
    assert "登录" in h


def test_hint_flags_truncation():
    h = _more_hint(count=200, matched=900, total=3354, q="li", role=None)
    assert "900" in h and "200" in h


# -- _format: renumber + hint tail -------------------------------------------

def test_format_lines_use_supplied_index_and_append_hint():
    descriptors = [
        {"i": 0, "tag": "a", "role": "", "type": "", "name": "首页", "disabled": False},
        {"i": 1, "tag": "button", "role": "tab", "type": "", "name": "消息", "disabled": True},
    ]
    out = _format(descriptors, total=40, q=None, role=None, matched=2)
    lines = out.splitlines()
    assert lines[0] == '[0] <a> "首页"'
    assert lines[1] == '[1] <button> role=tab "消息" (disabled)'
    # tail hint present because count(2) < total(40)
    assert lines[-1].startswith("—")
    assert "40" in lines[-1]


def test_format_no_hint_when_complete():
    descriptors = [{"i": 0, "tag": "a", "role": "", "type": "", "name": "x", "disabled": False}]
    out = _format(descriptors, total=1, q=None, role=None, matched=1)
    assert "—" not in out


# -- extract(): wiring against a scripted FakeCDP -----------------------------

class FakeCDP:
    """Scripts the exact CDP call sequence extract() performs, records which
    objectIds get the expensive describeNode so we can assert only survivors
    are resolved."""

    def __init__(self, payload: dict, backend_of: dict[str, int]):
        self._payload = payload
        self._backend_of = backend_of
        self.described: list[str] = []

    async def send(self, method, params=None, session_id=None, timeout=30.0):
        params = params or {}
        if method == "Runtime.evaluate":
            expr = params["expression"]
            if expr.startswith("window."):
                return {"result": {"objectId": "arr-1"}}
            if expr.startswith("delete window."):
                return {}
            # the collector
            return {"result": {"value": json.dumps(self._payload)}}
        if method == "Runtime.getProperties":
            result = [
                {"name": str(i), "value": {"objectId": f"el{i}"}}
                for i in range(len(self._payload["elements"]))
            ]
            result.append({"name": "length", "value": {"value": len(result)}})
            return {"result": result}
        if method == "DOM.describeNode":
            oid = params["objectId"]
            self.described.append(oid)
            idx = int(oid[2:])
            return {"node": {"backendNodeId": self._backend_of[idx]}}
        raise AssertionError(f"unexpected CDP method {method}")


def _run(coro):
    return asyncio.run(coro)


def test_extract_returns_subset_with_aligned_index_map():
    els = [
        _el("above", rect=_in(top=-50, bottom=-10)),      # 0 drop
        _el("first", rect=_in(top=100, bottom=140)),      # 1 keep -> [0]
        _el("below", rect=_in(top=900, bottom=940)),      # 2 drop
        _el("second", rect=_in(top=200, bottom=240)),     # 3 keep -> [1]
    ]
    payload = {"viewport": VIEWPORT, "elements": els}
    backend_of = {0: 1000, 1: 1001, 2: 1002, 3: 1003}
    cdp = FakeCDP(payload, backend_of)

    listing, index_map, total = _run(extract(cdp, "sid", q=None, role=None, max_elements=200))

    assert total == 4
    # only survivors (1, 3) resolved — off-screen never described
    assert cdp.described == ["el1", "el3"]
    # renumbered 0..k-1, keys align to survivors' backendNodeIds
    assert index_map == {0: 1001, 1: 1003}
    lines = listing.splitlines()
    assert lines[0] == '[0] <button> "first"'
    assert lines[1] == '[1] <button> "second"'
    assert lines[-1].startswith("—")  # 2 shown of 4 total → hint


def test_extract_query_scope_resolves_offscreen_match():
    els = [
        _el("登录", rect=_in(top=-999, bottom=-900)),   # offscreen, matches q
        _el("other", rect=_in(top=100, bottom=140)),
    ]
    payload = {"viewport": VIEWPORT, "elements": els}
    cdp = FakeCDP(payload, {0: 500, 1: 501})

    listing, index_map, total = _run(extract(cdp, "sid", q="登录", role=None, max_elements=200))

    assert index_map == {0: 500}
    assert cdp.described == ["el0"]
    assert total == 2


def test_extract_skips_survivor_that_fails_to_resolve_keeping_contiguous_numbers():
    # el1 resolves to no backend → must be skipped WITHOUT leaving a hole in the
    # numbering (index_map keys stay 0..k-1 contiguous, aligned to descriptors).
    els = [
        _el("a", rect=_in(top=100, bottom=140)),
        _el("b", rect=_in(top=150, bottom=190)),
        _el("c", rect=_in(top=200, bottom=240)),
    ]
    payload = {"viewport": VIEWPORT, "elements": els}

    class Holed(FakeCDP):
        async def send(self, method, params=None, session_id=None, timeout=30.0):
            if method == "DOM.describeNode" and params["objectId"] == "el1":
                self.described.append("el1")
                return {"node": {}}  # no backendNodeId
            return await super().send(method, params, session_id, timeout)

    cdp = Holed(payload, {0: 10, 1: 11, 2: 12})
    listing, index_map, total = _run(extract(cdp, "sid", q=None, role=None, max_elements=200))

    assert index_map == {0: 10, 1: 12}
    lines = listing.splitlines()
    assert lines[0].startswith("[0]") and '"a"' in lines[0]
    assert lines[1].startswith("[1]") and '"c"' in lines[1]


def test_extract_deletes_temp_global():
    els = [_el("x", rect=_in(top=100, bottom=140))]
    payload = {"viewport": VIEWPORT, "elements": els}

    deleted = []

    class Tracking(FakeCDP):
        async def send(self, method, params=None, session_id=None, timeout=30.0):
            if method == "Runtime.evaluate" and (params or {}).get("expression", "").startswith("delete window."):
                deleted.append(params["expression"])
            return await super().send(method, params, session_id, timeout)

    cdp = Tracking(payload, {0: 7})
    _run(extract(cdp, "sid", q=None, role=None, max_elements=200))
    assert len(deleted) == 1
