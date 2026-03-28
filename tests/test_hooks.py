"""T1 测试：skill hooks 安装/卸载的 JSON 合并逻辑。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 将 lib/ 加入 sys.path 以便导入 omp_hooks
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))


@pytest.fixture()
def settings_dir(tmp_path):
    """提供临时 ~/.claude/ 目录。"""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return claude_dir


@pytest.fixture()
def settings_file(settings_dir):
    """提供 settings.json 路径（可能不存在）。"""
    return settings_dir / "settings.json"


@pytest.fixture()
def sample_hooks_json(tmp_path):
    """创建示例 hooks.json 文件。"""
    hooks = {
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "omp-insight recall --source $PWD --format md",
                            "timeout": 5000,
                        }
                    ]
                }
            ],
            "PostCompact": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "omp-insight capture --source $PWD --since 1d",
                            "timeout": 30000,
                        }
                    ]
                }
            ],
        }
    }
    path = tmp_path / "hooks.json"
    path.write_text(json.dumps(hooks, indent=2))
    return path


def test_install_hooks_to_empty_settings(settings_file, sample_hooks_json):
    """合并到空 settings.json（文件不存在）。"""
    from omp_hooks import install_hooks

    install_hooks(sample_hooks_json, "insight", settings_file)

    assert settings_file.exists()
    data = json.loads(settings_file.read_text())
    assert "hooks" in data
    assert "SessionStart" in data["hooks"]
    assert "PostCompact" in data["hooks"]
    # 验证 _omp_skill 标记
    for event_hooks in data["hooks"].values():
        for hook_group in event_hooks:
            assert hook_group.get("_omp_skill") == "insight"


def test_install_hooks_to_existing(settings_file, sample_hooks_json):
    """合并到已有 hooks 的 settings.json，不覆盖其他 skill。"""
    from omp_hooks import install_hooks

    # 预置其他 skill 的 hooks
    existing = {
        "hooks": {
            "SessionStart": [
                {
                    "_omp_skill": "other-skill",
                    "hooks": [{"type": "command", "command": "other-command", "timeout": 1000}],
                }
            ]
        }
    }
    settings_file.write_text(json.dumps(existing, indent=2))

    install_hooks(sample_hooks_json, "insight", settings_file)

    data = json.loads(settings_file.read_text())
    session_start = data["hooks"]["SessionStart"]
    # 应该有 2 个条目：other-skill + insight
    assert len(session_start) == 2
    skills = {h.get("_omp_skill") for h in session_start}
    assert skills == {"other-skill", "insight"}


def test_install_hooks_idempotent(settings_file, sample_hooks_json):
    """重复安装同一 skill 不产生重复条目。"""
    from omp_hooks import install_hooks

    install_hooks(sample_hooks_json, "insight", settings_file)
    install_hooks(sample_hooks_json, "insight", settings_file)

    data = json.loads(settings_file.read_text())
    session_start = data["hooks"]["SessionStart"]
    insight_hooks = [h for h in session_start if h.get("_omp_skill") == "insight"]
    assert len(insight_hooks) == 1


def test_install_hooks_safe_write(settings_file, sample_hooks_json):
    """验证安装后 settings.json 是合法 JSON，且有 .bak 备份。"""
    from omp_hooks import install_hooks

    # 先创建一个已有的 settings.json
    settings_file.write_text(json.dumps({"existing": True}, indent=2))

    install_hooks(sample_hooks_json, "insight", settings_file)

    # 结果必须是合法 JSON
    data = json.loads(settings_file.read_text())
    assert "hooks" in data
    assert data.get("existing") is True  # 已有内容保留

    # 应有 .bak 备份文件
    bak = settings_file.parent / (settings_file.name + ".bak")
    assert bak.exists()


def test_install_hooks_abort_on_invalid_hooks_json(settings_file, tmp_path):
    """hooks.json 格式错误时应抛出异常。"""
    from omp_hooks import install_hooks

    bad_hooks = tmp_path / "bad_hooks.json"
    bad_hooks.write_text("not valid json {{{")

    with pytest.raises((json.JSONDecodeError, ValueError)):
        install_hooks(bad_hooks, "bad-skill", settings_file)

    # settings.json 不应被创建/修改
    assert not settings_file.exists()


def test_remove_hooks_precise(settings_file, sample_hooks_json):
    """卸载只移除目标 skill 的 hooks。"""
    from omp_hooks import install_hooks, remove_hooks

    # 安装两个 skill
    install_hooks(sample_hooks_json, "insight", settings_file)

    # 手动加一个其他 skill 的 hook
    data = json.loads(settings_file.read_text())
    data["hooks"]["SessionStart"].append({
        "_omp_skill": "other-skill",
        "hooks": [{"type": "command", "command": "other-cmd"}],
    })
    settings_file.write_text(json.dumps(data, indent=2))

    remove_hooks("insight", settings_file)

    data = json.loads(settings_file.read_text())
    session_start = data["hooks"]["SessionStart"]
    # insight 的应该没了
    skills = {h.get("_omp_skill") for h in session_start}
    assert "insight" not in skills
    assert "other-skill" in skills


def test_remove_hooks_cleanup_empty(settings_file, sample_hooks_json):
    """卸载后清理空的 hook event 数组。"""
    from omp_hooks import install_hooks, remove_hooks

    install_hooks(sample_hooks_json, "insight", settings_file)
    remove_hooks("insight", settings_file)

    data = json.loads(settings_file.read_text())
    # PostCompact 里只有 insight，移除后应该整个 key 消失或数组为空
    assert "PostCompact" not in data.get("hooks", {}) or data["hooks"]["PostCompact"] == []


def test_install_preserves_non_hook_settings(settings_file, sample_hooks_json):
    """安装 hooks 不影响 settings.json 中的其他配置。"""
    from omp_hooks import install_hooks

    settings_file.write_text(json.dumps({
        "apiKey": "sk-xxx",
        "theme": "dark",
    }, indent=2))

    install_hooks(sample_hooks_json, "insight", settings_file)

    data = json.loads(settings_file.read_text())
    assert data["apiKey"] == "sk-xxx"
    assert data["theme"] == "dark"
