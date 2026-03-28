# Skill 设计模式：目录结构参考

5 种模式对应的标准目录结构。模式可以组合，组合时合并对应结构。

## Tool Wrapper

让模型成为特定技术/库的专家，动态加载规范文档。

```
<skill>/
├── SKILL.md          # 触发条件 + 动态加载指令
└── references/
    ├── README.md     # 索引
    └── conventions.md / rules.md / best-practices.md
```

## Generator

从模板生成结构化文档/代码，模板驱动输出。

```
<skill>/
├── SKILL.md          # 收集变量的问题 + 填充模板的步骤
├── assets/
│   └── <output-template>.md
└── references/
    └── style-guide.md
```

## Reviewer

按标准审查内容，按严重程度分类输出。

```
<skill>/
├── SKILL.md          # 审查协议 + 严重程度分类规则
└── references/
    ├── README.md
    └── review-checklist.md
```

## Inversion

先多轮追问收集需求，再生成输出。

```
<skill>/
├── SKILL.md          # 分阶段问题 + 门控指令
└── assets/
    └── <output-template>.md
```

## Pipeline

严格的多步骤工作流，带检查点和用户确认。

```
<skill>/
├── SKILL.md          # 分步骤指令 + 检查点
├── references/       # 各步骤按需加载的规范文档
│   └── README.md
├── assets/           # 各步骤使用的模板
└── scripts/          # 仅当某步骤涉及可执行操作
```
