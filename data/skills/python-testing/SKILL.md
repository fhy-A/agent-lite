---
name: python-testing
description: Python 单元测试、pytest 编写和运行
keywords: pytest, unittest, python+测试, 测试+python, 单元测试, 补充+测试, 编写+测试, 测试+用例, test+python, test+pytest
tools: read_file, write_file, run_command
---

## Python 测试规范

当用户需要编写或运行 Python 测试时：

1. **先读现有测试**：了解项目已有的测试风格和框架
2. **遵循 pytest 惯例**：
   - 测试文件命名为 `test_*.py`
   - 测试函数命名为 `test_*`
   - 放在项目根目录的 `tests/` 或与被测文件同级
3. **运行测试**：`python -m pytest tests/ -v` 或 `python -m pytest test_file.py -v`
4. **失败时**：阅读错误输出，定位原因，修复后重新运行
5. **关键约定**：不改测试逻辑时只补充缺失用例，保持现有测试风格一致
