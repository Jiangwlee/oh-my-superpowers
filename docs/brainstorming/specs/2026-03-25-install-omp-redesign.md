# install.sh 双模式重写 + omp CLI Python/Typer 重写

> 将 install.sh 升级为双模式（dev symlink / remote clone），将 omp CLI 从 Bash 重写为 Python + Typer，补全 agent install/remove 缺口，提供彩色输出和自动 Help。

## 目录

- [设计方案](#设计方案)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

当前 `install.sh` 仅支持 dev-bootstrap（symlink 模式），无彩色输出，无依赖检查，无法通过 `curl | bash` 给非开发者使用。`bin/omp` 是 451 行 Bash，缺少 `omp install/remove agent`，彩色输出，Help 朴素。用户读取了 Python + Typer 最佳实践笔记后，决定全面现代化。

**成功标准：**
- `curl -fsSL https://raw.githubusercontent.com/Jiangwlee/oh-my-superpowers/main/install.sh | bash` 可用
- `./install.sh` 仍是 dev symlink 模式
- `omp install agent <name>`、`omp remove agent <name>` 可用
- `omp run <name> prompt words without quotes` 可用
- `uv run --script` 驱动，无需手动管理 venv

### 架构

**文件改动范围（最小）：**

```
install.sh          ← 双模式 Bash 重写（新增彩色/依赖检查/remote 分支）
bin/omp             ← 完整 Python + Typer 重写（替换现有 Bash 实现）
```

bin/ 下的其他文件（`omp-media-*`）不变。

**omp 单文件结构（bin/omp）：**

```
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///

常量区（OMP_HOME、SKILLS_SRC、AGENTS_SRC）
Console（Rich 彩色输出）
辅助函数（_symlink、_remove_link、_list_dir、_stream_verbose、_read_agents_json）
Typer app
  install(type_, name, global_)
  remove(type_, name, global_)
  list_cmd(type_, global_)
  run(name, model, prompt)
  test(name)
if __name__ == "__main__": app()
```

**install.sh 双模式检测：**

```bash
if [[ "${BASH_SOURCE[0]:-/dev/stdin}" == "/dev/stdin" || -z "${BASH_SOURCE[0]:-}" ]]; then
  MODE="remote"    # curl | bash → git clone
else
  MODE="local"     # ./install.sh → symlink（开发者模式）
fi
```

Remote 流程：依赖检查（git、uv）→ clone 或 pull `~/.oh-my-superpowers/` → 注册 bin/ → PATH 提示

Local 流程：依赖检查（uv）→ symlink `~/.oh-my-superpowers/` → 注册 bin/ → PATH 提示

### 关键决策

- **uv inline script dependencies**：`omp` 使用 `#!/usr/bin/env -S uv run --script` + `# /// script` 块，运行时自动缓存 typer/rich，无需手动 venv，与项目已有 uv 工具链一致。
- **动词优先命令结构**：`omp install skill/agent`、`omp remove skill/agent`、`omp run`、`omp list`、`omp test`，与 `omp install skill` 现有用法向后兼容。
- **run 的 prompt 为 `List[str]`**：`omp run media-editor 今天有什么 AI 动态` 无需引号，内部 join 为字符串传给 pi。
- **agent install/remove 目标路径**：`~/.pi/agents/<name>.md`（全局）/ `$PWD/.pi/agents/<name>.md`（局部），与 `docs/specs/02_framework/installation.md` 一致。
- **install.sh 保留 Bash**：双模式检测逻辑简单，无需 Python 启动开销，维持与 `curl | bash` 的兼容。

---

## 行动原则

- **TDD: Red → Green → Refactor**：先写失败测试，再写最小实现。**禁止：** 先写实现再补测试。
- **Break, Don't Bend**：`omp run agent foo -p "..."` 旧语法直接废弃，不建兼容层。**禁止：** deprecated/legacy 兼容代码。
- **Zero-Context Entry**：`bin/omp` 文件前 20 行注释列出所有命令和关键函数。**禁止：** 文件无头部说明。
- **Explicit Contract**：每个命令的参数类型、可选值、默认值在 Typer 声明中明确。**禁止：** 魔法默认值；隐式行为。
- **Minimum Blast Radius**：两个 Task 独立提交，install.sh 和 omp 互不依赖，可单独回滚。**禁止：** 一次提交混合两个文件的改动。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `install.sh` | 双模式重写，新增彩色输出、依赖检查、remote 分支 |
| 修改 | `bin/omp` | Python + Typer 完整重写，替换现有 Bash 实现 |
| 修改 | `docs/specs/02_framework/installation.md` | 更新 omp 命令语法示例 |

---

### Task 1：install.sh 双模式重写

**Files:**
- 修改: `install.sh`

- [ ] **Step 1：写集成测试（T1 静态 + 手动检查清单）**

  ```bash
  # 检查脚本通过 shellcheck
  shellcheck install.sh

  # 检查双模式检测逻辑（单元级）
  # local 模式：直接执行
  bash install.sh   # 预期：[INFO] Mode: local (dev symlink)

  # remote 模式：模拟 curl 管道
  bash < install.sh  # 预期：[INFO] Mode: remote (clone from GitHub)
  ```

- [ ] **Step 2：写 install.sh**

  结构：
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail

  # ── 配置 ──
  GITHUB_REPO="Jiangwlee/oh-my-superpowers"
  INSTALL_DIR="${HOME}/.oh-my-superpowers"
  BIN_DIR="${HOME}/.local/bin"

  # ── 彩色输出 ──
  info()    { printf '\033[34m[INFO]\033[0m %s\n' "$1"; }
  success() { printf '\033[32m[OK]\033[0m %s\n' "$1"; }
  warn()    { printf '\033[33m[WARN]\033[0m %s\n' "$1"; }
  fail()    { printf '\033[31m[ERROR]\033[0m %s\n' "$1" >&2; exit 1; }

  # ── 模式检测 ──
  detect_mode() { ... }   # 返回 "local" 或 "remote"

  # ── 依赖检查 ──
  check_deps() { ... }    # local: uv; remote: git + uv

  # ── 安装逻辑 ──
  install_local()  { ... }  # symlink
  install_remote() { ... }  # clone / pull

  # ── 注册 bin/ ──
  register_bins() { ... }

  # ── PATH 检查 ──
  check_path() { ... }

  main() {
    MODE=$(detect_mode)
    info "Mode: ${MODE}"
    check_deps "${MODE}"
    if [[ "${MODE}" == "remote" ]]; then
      install_remote
    else
      install_local
    fi
    register_bins
    check_path
    success "Bootstrap complete."
  }

  main "$@"
  ```

- [ ] **Step 3：验证**

  ```bash
  shellcheck install.sh
  bash install.sh   # local 模式验证
  ls -la ~/.oh-my-superpowers  # 确认是 symlink
  ls -la ~/.local/bin/omp      # 确认已注册
  ```

- [ ] **Step 4：提交**

  ```bash
  git add install.sh
  git commit -m "feat: rewrite install.sh with dual-mode (local symlink + remote clone)"
  ```

---

### Task 2：omp CLI Python + Typer 重写

**Files:**
- 修改: `bin/omp`

- [ ] **Step 1：写功能测试**

  ```bash
  # Help 正常显示
  omp --help
  omp install --help
  omp run --help

  # 命令结构验证（dry-run 级别）
  omp list
  omp list --type skill
  omp list --type agent --global
  ```

- [ ] **Step 2：写 bin/omp**

  完整命令实现：

  ```python
  #!/usr/bin/env -S uv run --script
  # /// script
  # dependencies = ["typer", "rich"]
  # ///
  #
  # omp — oh-my-superpowers CLI
  #
  # Commands:
  #   install <skill|agent> <name> [--global]
  #   remove  <skill|agent> <name> [--global]
  #   list    [--type skill|agent] [--global]
  #   run     <name> [--model TEXT] [prompt...]
  #   test    <name>

  import json
  import subprocess
  import sys
  from pathlib import Path
  from typing import Optional

  import typer
  from rich.console import Console
  from typing_extensions import Annotated

  OMP_HOME   = Path.home() / ".oh-my-superpowers"
  SKILLS_SRC = OMP_HOME / "skills"
  AGENTS_SRC = OMP_HOME / "agents"

  console = Console()
  app = typer.Typer(name="omp", help="oh-my-superpowers CLI", add_completion=False)

  # ── helpers ─────────────────────────────────────────────────────────────────

  def _check_home() -> None: ...
  def _symlink(src: Path, dst: Path) -> None: ...
  def _remove_link(dst: Path) -> None: ...
  def _list_dir(label: str, directory: Path) -> None: ...
  def _read_agents_json() -> dict: ...
  def _stream_verbose(proc: subprocess.Popen) -> int: ...

  # ── commands ─────────────────────────────────────────────────────────────────

  @app.command()
  def install(
      type_:   Annotated[str,  typer.Argument(metavar="skill|agent", help="skill 或 agent")],
      name:    Annotated[str,  typer.Argument(help="名称")],
      global_: Annotated[bool, typer.Option("--global", "-g", help="全局安装")] = False,
  ) -> None:
      """安装 skill 或 agent"""

  @app.command()
  def remove(
      type_:   Annotated[str,  typer.Argument(metavar="skill|agent")],
      name:    Annotated[str,  typer.Argument()],
      global_: Annotated[bool, typer.Option("--global", "-g")] = False,
  ) -> None:
      """卸载 skill 或 agent"""

  @app.command(name="list")
  def list_cmd(
      type_:   Annotated[Optional[str],  typer.Option("--type", "-t", metavar="skill|agent")] = None,
      global_: Annotated[bool, typer.Option("--global", "-g")] = False,
  ) -> None:
      """列出已安装的 skills 和 agents"""

  @app.command()
  def run(
      name:   Annotated[str,               typer.Argument(help="Agent 名称")],
      model:  Annotated[Optional[str],     typer.Option("--model", "-m", help="LLM 模型")] = None,
      prompt: Annotated[Optional[list[str]], typer.Argument(help="提示词（多词无需引号）")] = None,
  ) -> None:
      """运行 Pi Agent"""

  @app.command()
  def test(
      name: Annotated[str, typer.Argument(help="skill 名称")],
  ) -> None:
      """运行 skill T1 测试"""

  if __name__ == "__main__":
      _check_home()
      app()
  ```

- [ ] **Step 3：补全 agent install/remove 逻辑**

  ```python
  # install agent（全局）
  src = AGENTS_SRC / f"{name}.md"
  dst = Path.home() / ".pi" / "agents" / f"{name}.md"
  _symlink(src, dst)

  # install agent（局部）
  dst = Path.cwd() / ".pi" / "agents" / f"{name}.md"
  _symlink(src, dst)
  ```

- [ ] **Step 4：验证**

  ```bash
  chmod +x bin/omp
  omp --help
  omp install --help
  omp list
  omp install skill media-editor
  omp remove skill media-editor
  ```

- [ ] **Step 5：提交**

  ```bash
  git add bin/omp
  git commit -m "feat: rewrite omp CLI in Python + Typer with agent install/remove support"
  ```

---

### Task 3：文档更新

**Files:**
- 修改: `docs/specs/02_framework/installation.md`

- [ ] **Step 1：更新命令示例**

  将文档中的 `omp list agents` → `omp list --type agent`，更新 run 命令示例语法。

- [ ] **Step 2：提交**

  ```bash
  git add docs/specs/02_framework/installation.md
  git commit -m "docs: update installation.md for new omp CLI command structure"
  ```
