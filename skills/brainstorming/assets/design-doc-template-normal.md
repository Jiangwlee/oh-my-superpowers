# [Feature Name]
#
# 用途：Normal 模式设计文档模板
# 目录：设计方案 / 行动原则 / 行动计划
# 使用说明：替换所有 [占位符]，删除所有注释行（# 开头）

> [一句话描述：这个方案解决什么问题，面向谁]

## 目录

- [设计方案](#设计方案)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

[2-4 句话说明：为什么要做这个？当前痛点是什么？成功标准是什么？]

### 架构

[描述整体结构：组件/模块划分、数据流向、关键接口。复杂系统用列表或表格，简单改动 2-3 句即可。]

### 关键决策

[列出重要的设计选择及理由，格式：**决策**：理由。不需要列显而易见的决定。]

- **[决策 1]**：[理由]
- **[决策 2]**：[理由]

---

## 行动原则

> 从固定原则库（`references/principles-library.md`）中选取适用原则，可补充任务专属原则。

- **[原则名]**：[一句话说明] **禁止：** [具体禁止项]
- **[原则名]**：[一句话说明] **禁止：** [具体禁止项]
- **[可选：任务专属原则]** `[任务专属]`：[说明]

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `path/to/new-file.py` | [职责说明] |
| 修改 | `path/to/existing-file.py` | [改动说明] |
| 删除 | `path/to/removed-file.py` | [删除原因] |

### 任务步骤

#### Task 1: [组件/功能名称]

**Files:**
- 新增: `path/to/file.py`
- 修改: `path/to/existing.py`
- 测试: `tests/path/to/test_file.py`

- [ ] **Step 1: 写失败测试**

```python
def test_[specific_behavior]():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/path/test_file.py::test_name -v
# 预期：FAIL
```

- [ ] **Step 3: 写最小实现**

```python
def function(input):
    # 最小实现
    return expected
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/path/test_file.py::test_name -v
# 预期：PASS
```

- [ ] **Step 5: 提交**

```bash
git add path/to/file.py tests/path/test_file.py
git commit -m "feat: [具体描述]"
```

#### Task 2: [下一个组件/功能]

[重复上述结构]

#### Task N: 文档更新（重大变更必须包含此任务）

> 适用条件：架构变更、接口变更、目录结构调整、新增/删除核心模块等重大改动。
> 小功能迭代或 bug 修复无需此任务。

**Files:**
- 修改: `README.md` 或其他受影响的文档

- [ ] **Step 1: 识别需要更新的文档**

  检查以下位置是否有过时内容：
  - `README.md`（项目概述、架构图、目录结构）
  - `docs/specs/` 下相关规范文档
  - 受影响模块的 `references/` 文档

- [ ] **Step 2: 更新文档内容**

  只更新因本次变更而过时的部分，不做无关改动。

- [ ] **Step 3: 提交**

```bash
git add README.md  # 或其他文档
git commit -m "docs: update [文档名] for [变更描述]"
```
