# AGENTS.md - OpenclawSkills 开发指南

本项目开发了一系列满足 Openclaw 规范的 Skills（智能体技能），主要用于金融数据抓取、分析与研究。

## IRON RULES

- No coding WITHOUT reading Skills-Dev-Guides.md
- Every skill in `skills/` is independent and autonomous

## 规范参考

- [Agent Skills](https://github.com/agentskills/agentskills): Openclaw 遵从的 Skills 规范
- [Tools](https://docs.openclaw.ai/tools/browser): Openclaw 内置工具
- [Skills Development Guide](Skills-Dev-Guide.md)：Skills开发经验，当发现一种有效的Skill编写模式时，可追加到此文件中。
- [JVQuant 平台参考](docs/jvquant-reference.md)：JVQuant 券商交易接口文档，含 API 规格、计费标准、费用优化策略。

## 技术栈

- **语言**: Python 3.10+ (标准库为主)
- **测试**: unittest / pytest
- **HTML 解析**: html.parser (禁止正则)

## 研究与参考

开发新的Skills时，要避免重复造轮子。对于用户的需求，首先要在使用`gh search`命令在github上检索相关项目，对于关联度较高的项目，下载代码至`github_cache`目录并深入研究。
`github_cache`管理规范：
1.为每个研究主题建立一个子目录，比如：`github_cache/skills`. 与该主题相关的项目将下载至该目录中。
2.用`github_cache/INDEX.md`为所有github项目建立索引，方便快速检索项目。

---

## 开发命令

```bash
# 运行单个测试文件
python -m unittest skills/ashare-assistant/tests/test_taoguba_fetchers.py

# 运行单个测试方法
python -m unittest skills.a_share_review_planner.tests.test_taoguba_fetchers.TaogubaFetchersTest.test_now_recommend

# 运行所有测试
python -m unittest discover -s skills -p "test_*.py"

# 语法检查
python -m py_compile <file.py>
```

---

## 代码风格

### 1. 导入排序

标准库 → 第三方 → 本地模块，组内按字母排序：

```python
import json
import logging
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from typing import Any

import requests
from scripts import fetchers
```

### 2. 类型注解

- Python 3.10+ 联合类型: `str | None` (非 `Optional[str]`)
- 复杂类型用 type alias:

```python
Post = dict[str, Any]
Posts = list[Post]
```

### 3. 命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 模块 | 小写下划线 | `taoguba.py` |
| 类 | 大驼峰 | `TaogubaFetchersTest` |
| 函数 | 小写下划线 | `fetch_taoguba_hot()` |
| 私有函数 | 前缀下划线 | `_fetch_detail()` |
| 常量 | 全大写 | `_BASE_URL` |

### 4. Docstring (Google 风格)

```python
def fetch_data(count: int = 20) -> list[dict]:
    """获取数据。

    Args:
        count: 返回数量。

    Returns:
        数据列表，出错时返回空列表。
    """
```

### 5. 错误处理

- 数据获取函数: 捕获异常后返回空列表/字典，不抛出
- 用 `logger.exception()` 记录错误
- 网络请求设置 timeout (默认 15 秒)

```python
def fetch_data(url: str) -> list[dict]:
    try:
        return data
    except Exception as e:
        logger.exception("fetch_data 出错: %s", e)
        return []
```

### 6. HTML 解析

**禁止正则**，必须用 `html.parser`：

```python
from html.parser import HTMLParser

class _MyParser(HTMLParser):
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div" and self._get_attr(attrs, "id") == "first":
            self._in_content = True

    def _get_attr(self, attrs, key: str) -> str:
        for name, val in attrs:
            if name == key:
                return val or ""
        return ""
```

### 7. 并发

用 `ThreadPoolExecutor`:

```python
with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
    contents = list(pool.map(_fetch_detail, urls))
```

### 8. 日志

`logger = logging.getLogger(__name__)`，用 `logger.debug()` / `logger.warning()` / `logger.exception()`

---

## 项目结构

```
skills/
├── ashare-assistant/
│   ├── scripts/
│   │   ├── fetchers/   # 数据抓取
│   │   └── utils/      # 工具
│   ├── tests/         # 单元测试
│   ├── references/    # 参考文档
│   ├── evolution/     # 演进记录
│   ├── strategy/      # 策略配置
│   └── SKILL.md
├── github-researcher/
└── openclaw-github-tracker/
```

---

## 禁止事项

1. 禁止正则解析 HTML
2. 禁止硬编码敏感信息
3. 禁止 rsync 部署，只用 `cp` / `scp`

---

## Skills 目录结构与部署规则

**源码目录是唯一修改入口，部署目录是只读副本，不直接修改。**

```
skills/<skill-name>/          ← 源码（在此修改）
.claude/skills/<skill-name>/  ← 部署副本（Claude Code 用）
.agents/skills/<skill-name>/  ← 部署副本（其他 agent 用）
```

修改 skill 的正确流程：

```bash
# 1. 在源码目录修改
vim skills/<skill-name>/SKILL.md

# 2. 部署到本地两个部署目录
cp -r skills/<skill-name>/ .claude/skills/<skill-name>/
cp -r skills/<skill-name>/ .agents/skills/<skill-name>/
```

**禁止直接修改 `.claude/skills/` 或 `.agents/skills/` 下的文件。**

---

## 部署

详见 `Deployment.md`:

```bash
# 本地
cp -r skills/<skill-name>/ ~/clawd/skills/<skill-name>/
openclaw gateway restart

# 远端
scp -r skills/<skill-name>/ root@tencent-vps:/root/.openclaw/workspace-smartrader/skills/
ssh root@tencent-vps "source ~/.nvm/nvm.sh && openclaw gateway restart"
```

---

## 测试检查清单

- [ ] 测试通过: `python -m unittest discover -s skills`
- [ ] 无语法错误: `python -m py_compile`
- [ ] 类型注解完整
- [ ] Docstring 完整
- [ ] HTML 解析用 html.parser
