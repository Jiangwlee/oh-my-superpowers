# Anthropics Skills 深度分析

来源：`github_cache/skills_repos/anthropics-skills/`（16个官方 skills）

---

## 一、核心架构：三层渐进加载

Anthropic 官方 skill-creator 明确揭示了 skill 的三层加载机制：

```
层级 1: Frontmatter metadata（name + description）
        → 始终存在于 context（约 100 词）
        → 用于决定是否触发 skill

层级 2: SKILL.md body（正文内容）
        → 仅在 skill 触发后加载（建议 < 500 行）
        → 包含工作流程和核心指令

层级 3: 附属资源（scripts/ references/ assets/）
        → 仅在 Claude 判断需要时按需加载
        → 量可无限，因为脚本可以"执行而不读入"
```

**关键推论**: description 是**唯一的触发机制**。body 里写的"When to Use This Skill"章节，在触发前不可见，毫无意义。所有触发条件必须写在 description 里。

---

## 二、description 写作公式

官方示例（docx skill）：
```
"Comprehensive document creation, editing, and analysis with support for
tracked changes, comments, formatting preservation, and text extraction.
Use when Claude needs to work with professional documents (.docx files) for:
(1) Creating new documents, (2) Modifying or editing content,
(3) Working with tracked changes, (4) Adding comments, or any other document tasks"
```

公式：**[能力全景] + "Use when" + [场景列表 (1)(2)(3)...]**

- 前半部分：告诉系统 skill **做什么**（关键词扫描用）
- 后半部分：告诉系统 skill **什么时候用**（触发判断用）

---

## 三、自由度设计原则

根据任务的脆弱性和变异性匹配指令的具体程度：

| 自由度 | 适用场景 | 指令形式 |
|--------|----------|----------|
| 高 | 多种方法都可行，依上下文判断 | 文字指令 + 方向性建议 |
| 中 | 有推荐模式，可接受一定变化 | 伪代码 / 参数化脚本 |
| 低 | 操作脆弱易错，必须精确执行 | 具体脚本 + 严格步骤 |

比喻（skill-creator 原文）：
> 窄桥悬崖上的探险者需要具体护栏（低自由度），而开阔草原允许多条路径（高自由度）。

实例：
- `webapp-testing` 提供决策树（中-低自由度）
- `frontend-design` 只给设计哲学（高自由度）
- `mcp-builder` 分4个阶段，每阶段都有具体步骤（中自由度）

---

## 四、资源目录设计模式

### scripts/ —— 黑盒化执行

**核心原则**：脚本作为黑盒使用，不要读源码。

```markdown
# webapp-testing SKILL.md 的指导语：
"Always run scripts with `--help` first to see usage.
DO NOT read the source until you try running the script first and find
that a customized solution is absolutely necessary.
These scripts can be very large and thus pollute your context window."
```

脚本好处：
- Token 节省（执行而不读入）
- 确定性（避免 Claude 每次重写）
- 可直接调用 black-box

### references/ —— 域驱动组织

**模式 A：按业务领域拆分**
```
bigquery-skill/
├── SKILL.md (导航层)
└── reference/
    ├── finance.md   (财务指标)
    ├── sales.md     (销售数据)
    └── product.md   (产品用法)
```

**模式 B：按技术变体拆分**
```
cloud-deploy/
├── SKILL.md (选择提供商)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

用户选择 AWS 时，只加载 aws.md。精准按需，不浪费 context。

**规则**：
- 参考文件只有1层深度，直接从 SKILL.md 链接
- 参考文件 > 100 行时，在顶部加目录
- 在 SKILL.md 中明确写"何时读取某文件"

### assets/ —— 模板文件库

存放**不读入 context、但作为输出素材**的文件：

| 类型 | 示例 |
|------|------|
| 起始模板 | `viewer.html`, `hello-world/` 前端样板 |
| 品牌素材 | `logo.png`, 字体文件 |
| 文档模板 | `slides.pptx`, `template.docx` |

`algorithmic-art` 最典型：SKILL.md 明确要求"必须先读取 templates/viewer.html，再基于它修改"，而不是从零开始重建 HTML。

---

## 五、禁止在 Skill 中创建的文件

官方 skill-creator 明确列出：

```
❌ README.md
❌ INSTALLATION_GUIDE.md
❌ QUICK_REFERENCE.md
❌ CHANGELOG.md
```

原则：skill 只包含 AI Agent 完成任务所需的信息，不包含人类开发者的辅助文档。

---

## 六、工作流组织模式

### 模式 A：顺序工作流（Sequential）

用于多步骤任务，步骤清晰：

```markdown
PDF 表单填写流程：
1. 分析表单（运行 analyze_form.py）
2. 创建字段映射（编辑 fields.json）
3. 验证映射（运行 validate_fields.py）
4. 填充表单（运行 fill_form.py）
5. 验证输出（运行 verify_output.py）
```

### 模式 B：条件工作流（Conditional）

用于有分支的任务，减少歧义：

```markdown
确定修改类型：
**创建新内容？** → 执行"创建工作流"
**编辑现有内容？** → 执行"编辑工作流"
```

### 模式 C：三阶段交互工作流

用于需要用户持续参与的复杂任务（`doc-coauthoring` 模式）：

```
Stage 1: Context Gathering（信息收集）
  → 提问 → 信息 dump → 追问澄清
Stage 2: Refinement & Structure（逐段打磨）
  → 头脑风暴 → 筛选 → 起草 → 迭代
Stage 3: Reader Testing（读者测试）
  → 预测读者问题 → 用子智能体验证 → 修复
```

### 模式 D：决策树（Decision Tree）

用于工具/方法选择场景（`webapp-testing` 模式）：

```
是否静态 HTML？
  ├─ 是 → 直接读 HTML 识别选择器
  └─ 否 → 服务器是否已运行？
      ├─ 否 → 先用 with_server.py
      └─ 是 → Reconnaissance-then-action 模式
```

---

## 七、内容格式最佳实践

### 写作语态
使用祈使/不定式形式（imperative/infinitive form）：
- ✅ "Navigate to the settings page"
- ✅ "Run the script with --help first"
- ❌ "You should navigate to..."
- ❌ "Claude will navigate..."

### 关键词段（brand-guidelines 模式）

在 skill body 中加 Keywords 段，增强关键词覆盖：

```markdown
**Keywords**: branding, corporate identity, visual identity, styling, brand colors
```

### 嵌套层级限制

- 参考文件嵌套不超过 1 层（都从 SKILL.md 直接链接）
- SKILL.md body 建议 < 500 行
- 超过 500 行必须拆分到 references/

### 模板优先原则（algorithmic-art 模式）

当 skill 有固定输出格式时，提供模板并强制要求先读模板：

```markdown
## ⚠️ STEP 0: READ THE TEMPLATE FIRST ⚠️

1. Read `templates/viewer.html` using the Read tool
2. Use that file as the LITERAL STARTING POINT
3. Keep all FIXED sections exactly as shown
4. Replace only the VARIABLE sections
```

---

## 八、输出模式设计

### 严格模板（用于 API 响应、数据格式）

```markdown
ALWAYS use this exact template structure:
# [Analysis Title]
## Executive summary
[One-paragraph overview]
## Key findings
- Finding 1 with supporting data
```

### 弹性指引（用于需要适应上下文的场景）

```markdown
Here is a sensible default format, but use your best judgment:
# [Analysis Title]
## Key findings
[Adapt sections based on what you discover]
```

### 示例驱动（用于输出风格高度依赖理解的场景）

```markdown
**Example 1:**
Input: Added user authentication with JWT tokens
Output:
feat(auth): implement JWT-based authentication
Add login endpoint and token validation middleware
```

---

## 九、复杂 Skill 参考文件组织实例

### mcp-builder（4阶段 + 分语言文档）

```
mcp-builder/
├── SKILL.md          # 4阶段概览，链接所有 reference
└── reference/
    ├── mcp_best_practices.md    # 阶段1必读
    ├── python_mcp_server.md     # Python 选手读
    ├── node_mcp_server.md       # TypeScript 选手读
    └── evaluation.md            # 阶段4必读
```

SKILL.md 中用 emoji 标注每个引用文件：
```markdown
- 📋 View Best Practices: ./reference/mcp_best_practices.md
- 🐍 Python Guide: ./reference/python_mcp_server.md
- ⚡ TypeScript Guide: ./reference/node_mcp_server.md
- ✅ Evaluation Guide: ./reference/evaluation.md
```

---

## 十、关键反模式（官方归纳）

| 反模式 | 正确做法 |
|--------|----------|
| body 里写"When to Use" | 移到 description |
| SKILL.md 塞满细节不拆分 | 关键信息 SKILL.md，细节 references/ |
| 直接读大脚本源码 | 先运行 --help，黑盒调用 |
| 创建 README/CHANGELOG 等 | 只保留 Agent 工作所需文件 |
| 参考文件嵌套多层 | 最多1层，直接从 SKILL.md 链接 |
| description 只描述功能 | 同时包含"what + when to use" |
| 从零重建有模板的输出 | 先读模板，基于模板修改 |
