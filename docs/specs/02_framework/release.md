# Release Guide

版本管理与发布流程规范。

---

## 版本号规范

### 格式

[Semantic Versioning 2.0.0](https://semver.org/)：`MAJOR.MINOR.PATCH`

| 变更类型 | 示例 | 版本号变化 |
|----------|------|-----------|
| 不兼容的 API/CLI 变更 | 命令重命名、参数删除 | MAJOR +1 |
| 新增功能（向后兼容） | 新 skill、新子命令 | MINOR +1 |
| Bug 修复、文档、小改进 | --help 修复、typo | PATCH +1 |

### 单一来源

```
VERSION        ← 项目根目录，内容仅一行：0.1.1
bin/omp        ← 运行时从 $OMP_HOME/VERSION 读取
```

`bin/omp` 不硬编码版本号。找不到 VERSION 文件时 fallback 为 `0.0.0-dev`。

---

## 发布流程

### 步骤

```bash
# 1. 更新版本号
echo "0.2.0" > VERSION

# 2. 提交
git add VERSION
git commit -m "chore: release v0.2.0"

# 3. 打 tag
git tag v0.2.0

# 4. 推送（commit + tag）
git push origin main && git push origin v0.2.0
```

### 自动化

推送 `v*` tag 后，GitHub Actions 自动执行（`.github/workflows/release.yml`）：

1. **校验一致性**：VERSION 文件内容必须与 tag 版本一致，不一致则失败
2. **创建 GitHub Release**：基于两个 tag 之间的 commit 自动生成 Release Notes

### 规则

- tag 格式：`v` + 版本号（如 `v0.2.0`），必须与 VERSION 文件一致
- commit message：`chore: release v0.2.0`
- 一个 tag 对应一个 release，不修改已发布的 tag
- Release Notes 由 GitHub `generate_release_notes` 自动生成，不手写 CHANGELOG

---

## 用户侧更新

```bash
omp upgrade
```

执行逻辑：

1. `git pull --ff-only` 拉取最新代码（基于 `$OMP_HOME` 解析的 git 目录）
2. 重新注册 `bin/` 下的可执行文件到 `~/.local/bin/`
3. 输出版本变化（`v0.1.1 → v0.2.0`）或提示已是最新

---

## 文件清单

| 文件 | 作用 |
|------|------|
| `VERSION` | 版本号单一来源 |
| `bin/omp` | 运行时读取 VERSION，提供 `--version` 和 `upgrade` 命令 |
| `.github/workflows/release.yml` | tag 触发 GitHub Release |
