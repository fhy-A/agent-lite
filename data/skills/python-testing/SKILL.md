---
name: python-testing
description: 为 Python 项目运行、诊断或编写 pytest/unittest 测试，遵循项目现有测试风格并用可复现行为验证功能。
keywords: pytest, unittest, python+测试, 测试+python, 单元测试, 补充+测试, 编写+测试, 测试+用例, test+python, test+pytest
tools: list_files, read_file, search_files, glob_files, write_file, propose_edit, run_command
---

# Python 测试

## 先判断用户要的动作

- **只运行测试**：找到项目根目录和现有命令，运行后汇报结果，不修改文件。
- **诊断失败**：确定第一个根因，区分实现错误、测试过期、环境/依赖问题；用户没有要求修复时只报告。
- **补充测试**：先读被测公开接口与相邻测试，再用项目已有框架和 fixture 编写。
- **修复缺陷/实现功能**：需要时先写能复现目标行为的失败测试，再修改实现。

## 编写原则

1. 遵循现有命名、目录、fixture、参数化和断言风格；不统一改写无关测试。
2. 一个测试聚焦一个行为，名称说清场景和预期结果。
3. 测公开行为和稳定输出，不把内部实现顺序写成脆弱断言。
4. 覆盖正常路径、关键边界和有意义的错误路径；不为了数量穷举等价输入。
5. 优先使用真实代码和小型 fixture。只在网络、时间、随机、外部进程或高成本服务无法稳定控制时 mock。
6. 每个测试隔离临时文件、环境变量、数据库和全局状态，在 Windows 路径与文件锁场景下正确清理。
7. 不让单元测试依赖真实网络、本机私密或执行顺序。

## 运行方式

优先使用项目文档、CI 配置或现有脚本中的命令。无明确约定时：

```powershell
python -m pytest tests/path/test_file.py::test_name -vv
python -m pytest tests/path/test_file.py -q
python -m pytest -q
```

先跑最小定向用例，通过后再扩大到相关模块和全量回归。命令无输出时先确认当前目录、测试收集和进程状态，不重复盲目启动。

交付时说明测试的行为目标、运行命令、通过/失败数量和剩余未覆盖风险。
