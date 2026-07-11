---
name: code-review
description: 代码审查、代码质量检查、bug 检测、安全审查
keywords: review, 审查, 代码审查, code review, bug, 安全, 漏洞, 质量
tools: read_file, search_files, glob_files
---

## 代码审查规范

当用户要求代码审查时：

1. **全面扫描**：用 search_files 搜索常见问题模式（TODO、FIXME、硬编码密钥、未处理异常）
2. **安全检查**：SQL 注入、XSS 漏洞、路径遍历、权限缺失
3. **性能审查**：不必要的循环、N+1 查询、内存泄漏隐患
4. **可读性**：命名规范、函数长度、注释完整性
5. **输出格式**：按严重性排列问题，每条附文件路径+行号+修复建议
