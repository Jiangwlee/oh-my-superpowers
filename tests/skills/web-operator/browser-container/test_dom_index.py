"""T1: indexed DOM formatting is deterministic and LLM-readable."""

from app.engine import dom_index


def test_unwrap_json_empty():
    assert dom_index._unwrap_json({"result": {"value": ""}}) == []
    assert dom_index._unwrap_json({}) == []


def test_format_numbers_and_labels():
    descriptors = [
        {"i": 0, "tag": "a", "role": "", "type": "", "name": "首页", "disabled": False},
        {"i": 1, "tag": "input", "role": "", "type": "text", "name": "搜索", "disabled": False},
        {"i": 2, "tag": "button", "role": "tab", "type": "", "name": "登录", "disabled": True},
    ]
    out = dom_index._format(descriptors).splitlines()
    assert out[0] == '[0] <a> "首页"'
    assert out[1] == '[1] <input:text> "搜索"'
    assert out[2] == '[2] <button> role=tab "登录" (disabled)'
