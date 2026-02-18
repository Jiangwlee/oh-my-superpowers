# Openclaw 适配要点

## 技能加载优先级

Openclaw 按以下优先级加载同名 skill：

1. `<workspace>/skills`（最高）
2. `~/.openclaw/skills`
3. bundled skills（最低）

## 可见性与 eligibility（门控）

Openclaw 会按环境/配置/二进制可用性筛选技能。`metadata.openclaw.requires` 可声明：

- `bins` / `anyBins`
- `env`
- `config`

不满足条件时，技能可能不会进入可用列表。

## 上下文预算意识

- 系统提示会注入"技能列表（name/description/path）"
- 列表越长、描述越冗长，上下文占用越高
- 所以 `description` 要短、准、可判定

## 部署测试流程

1. 拷贝到 `/Users/mindora/clawd/skills`
2. 执行 `openclaw gateway restart`
3. 用真实提示语回归触发与执行
