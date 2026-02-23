# 开发与测试

## 单测

```bash
python3 -m unittest discover -s skills/markdown-to-anything/tests -p "test_*.py"
```

## 指定测试文件

```bash
python3 -m unittest skills/markdown-to-anything/tests/test_validator.py
python3 -m unittest skills/markdown-to-anything/tests/test_convert.py
python3 -m unittest skills/markdown-to-anything/tests/test_report_render.py
```

## 语法检查

```bash
python3 -m py_compile skills/markdown-to-anything/scripts/*.py
```

## 本地部署（只从源码目录复制）

```bash
cp -r skills/markdown-to-anything/ .claude/skills/markdown-to-anything/
cp -r skills/markdown-to-anything/ .agents/skills/markdown-to-anything/
cp -r skills/markdown-to-anything/ ~/clawd/skills/markdown-to-anything/
```

注意：不要直接修改 `.claude/skills/` 或 `.agents/skills/` 副本。
