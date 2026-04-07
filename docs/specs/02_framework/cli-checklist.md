# CLI Checklist

新增或修改 CLI 命令时逐项检查。全部通过才允许合入。

> 完整规范见 [cli-development-guide.md](cli-development-guide.md)

---

## 工具 CLI 模块（cli/<tool>/main.py）

- [ ] 目录名与 `omp <tool>` 的 tool 名一致（自动路由依据）
- [ ] 入口文件为 `main.py`，使用 typer 管理子命令
- [ ] main.py 不含业务逻辑，仅做参数解析 + 路由 + 输出格式化
- [ ] 业务逻辑在 `skills/<tool>/scripts/` 中实现，独立于 CLI 框架
- [ ] 通过 `$OMP_HOME` 定位实现脚本，无相对路径或硬编码路径
- [ ] 启动时加载 `$OMP_HOME/.env`（使用 `os.environ.setdefault`，不覆盖已有值）
- [ ] 无参数时输出 help（`no_args_is_help=True`）

## --help 输出

- [ ] 每个命令和子命令都响应 `--help` / `-h`（typer 自动处理）
- [ ] 包含 usage 行（展示完整调用格式）
- [ ] 包含一句话描述（typer app help + command docstring）
- [ ] 包含参数/选项列表（含类型和默认值，typer 从类型注解生成）
- [ ] 包含至少一个 Example（在 docstring 或 epilog 中）
- [ ] 无参数或参数错误时自动输出 usage 提示

## 参数设计

- [ ] 必填参数使用 `typer.Argument`，可选参数使用 `typer.Option`
- [ ] flag 使用 `--long-flag` 小写连字符格式
- [ ] 所有可选参数有合理默认值
- [ ] 无交互式输入（无 TTY prompt、无 confirm dialog）
- [ ] 破坏性操作需要 `--force` 或 `--confirm` 显式确认

## 输出设计

- [ ] 结构化数据走 stdout（JSON 单行，不 pretty-print）
- [ ] 诊断信息走 stderr（进度、警告、调试）
- [ ] 错误信息包含：错了什么、期望什么、怎么修
- [ ] 默认输出量有上限，提供 `--limit` / `--offset` 控制
- [ ] 管道可组合：stdout 输出可直接被下游命令消费

## 退出码

- [ ] 成功返回 0
- [ ] 业务失败返回 1
- [ ] 用法错误（未知命令、缺参数、stdin 非法 JSON）返回 2
- [ ] 权限/环境缺失（环境变量未设置、认证过期）返回 4

## 错误处理

- [ ] 环境变量校验在入口处完成，缺失则 stderr 报错 + exit 4
- [ ] 业务层异常由 CLI 层 catch，输出到 stderr + 设置退出码
- [ ] 不吞错误：禁止 catch 后静默继续

## 与 SKILL.md 的协作

- [ ] SKILL.md 中使用 `omp <tool> <subcommand>` 格式调用，不写脚本路径
- [ ] SKILL.md 引导 LLM 使用 `omp <tool> <subcommand> --help` 查看完整参数
- [ ] SKILL.md 中的示例与实际 --help 一致（命令名、参数名）

## 路由绑定

- [ ] `cli/<tool>/` 目录名 == `omp <tool>` 中的 tool 名
- [ ] `omp <tool> --help` 能正确输出该工具的帮助信息
- [ ] `omp <tool> <unknown-subcommand>` 返回错误 + usage 提示
