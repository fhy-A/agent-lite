---
name: office-files
description: 只读提取 Word、Excel、PowerPoint 和 PDF 文件中的文本、表格、工作表与幻灯片内容。用于读取、提取、分析或总结已有 Office/PDF 文件；不用于创建或美化新文档。
keywords: 读取+word, 读取+docx, 提取+word, 读取+excel, 读取+xlsx, 提取+excel, 读取+ppt, 读取+pptx, 提取+ppt, 读取+pdf, 提取+pdf, 分析+pdf, 总结+pdf
tools: list_files, read_file, glob_files, run_command, write_file
---

# Office / PDF 内容提取

默认只读，不替换源文件。只有用户明确要求导出提取结果时，才用 `write_file` 写入用户指定的文本/Markdown 路径。

## 通用流程

1. 确认文件路径、扩展名和大小；多个候选时先列出文件。
2. 根据格式选择库，首次使用前通过短命令确认库可导入，不假设所有可选依赖都已安装。
3. 先提取结构摘要（页数、Sheet 名、幻灯片数、表格数），再按需读取范围，避免一次输出整个大文件。
4. 将空值与数字 `0` 区分开，保留工作表/页码/幻灯片索引以便追溯。
5. 交付时说明读取范围、跳过的内容和提取限制。

## Word (`.docx`)

使用 `python-docx`：

```powershell
python -c "from docx import Document; p=r'FILE.docx'; d=Document(p); print('paragraphs',len(d.paragraphs),'tables',len(d.tables)); [print(x.text) for x in d.paragraphs if x.text.strip()]"
```

需要表格时单独遍历 `d.tables`，为每张表和每行保留索引。页眉、页脚、文本框和修订内容可能不在普通段落列表中，不能声称已完整提取而未检查这些部位。

## Excel (`.xlsx` / `.xlsm`)

使用 `openpyxl.load_workbook(path, data_only=True, read_only=True)`，先列出 `sheetnames`，再读用户需要的 Sheet 和行列范围。如果需要公式本身，改用 `data_only=False`。

`.xls` 是旧二进制格式，`openpyxl` 不支持。可尝试 `pandas.read_excel` 与已安装引擎；引擎不存在时明确说明需要转为 `.xlsx`，不要偷换格式或写回原文件。

## PowerPoint (`.pptx`)

使用 `python-pptx`，按幻灯片索引输出文本形状和表格。对组合形状、图表、备注、SmartArt 和图片内文字要单独说明是否已检查；仅遍历 `shape.text` 不等于完整视觉内容。

## PDF

文本型 PDF 可使用 `PyPDF2.PdfReader` 或当前可用的 PDF 库，先获取页数，再按用户指定页码提取。

如果页面只返回空文本或乱序字符，可能是扫描件、字体编码或复杂分栏；说明需要 OCR 或页面渲染，不编造内容。

## 安全与输出

- 对不可信 Office 文件仅做内容解析，不执行宏、嵌入对象、外部链接或附带脚本。
- 用户未要求时不导出全文，优先给结构化摘要和可追溯的定位。
- 输出命令必须限制行数/页数，大文件分批读取，避免撑满上下文。
