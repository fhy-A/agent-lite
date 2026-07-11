---
name: office-files
description: 读取 Word、Excel、PPT、PDF 等办公文档，提取文本、表格、内容
keywords: docx, xlsx, pptx, pdf, word, excel, ppt, 文档, 表格, 幻灯片, 办公, 读取, 提取, 转换, office
tools: run_command, read_file, write_file
---

## Office 文件处理

本项目已预装处理库：`python-docx`、`openpyxl`、`python-pptx`、`PyPDF2`、`pandas`、`zipfile`。

所有操作都用 `python -c "..."` 执行，输出纯文本到 stdout，不要在脚本里写文件。

---

### Word (.docx) 读取

**提取全部段落文本：**
```bash
python -c "from docx import Document; doc=Document(r'文件路径'); [print(p.text) for p in doc.paragraphs if p.text.strip()]"
```

**提取所有表格：**
```bash
python -c "from docx import Document; doc=Document(r'文件路径'); [print('\t'.join(c.text for c in row.cells)) for t in doc.tables for row in t.rows]"
```

---

### Excel (.xlsx / .xls) 读取

**列出所有 Sheet 名：**
```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'文件路径', data_only=True); [print(s) for s in wb.sheetnames]"
```

**读取指定 Sheet（前 100 行）：**
```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'文件路径', data_only=True); ws=wb['Sheet名']; [print('\t'.join(str(c.value or '') for c in row)) for row in list(ws.iter_rows())[:100]]"
```

**用 pandas 读取（自动处理表头）：**
```bash
python -c "import pandas as pd; df=pd.read_excel(r'文件路径', sheet_name='Sheet名'); print(df.head(50).to_string())"
```

---

### PPT (.pptx) 读取

**提取所有幻灯片文本：**
```bash
python -c "from pptx import Presentation; prs=Presentation(r'文件路径'); [print(f'--- 第{i+1}页 ---\n'+'\n'.join(s.text for s in slide.shapes if s.has_text_frame)) for i,slide in enumerate(prs.slides)]"
```

---

### PDF 读取

**PyPDF2（基础文本提取）：**
```bash
python -c "from PyPDF2 import PdfReader; r=PdfReader(r'文件路径'); [print(r.pages[i].extract_text()) for i in range(len(r.pages))]"
```

**PyPDF2（指定页码范围，如第 1-3 页）：**
```bash
python -c "from PyPDF2 import PdfReader; r=PdfReader(r'文件路径'); [print(r.pages[i].extract_text()) for i in range(3)]"
```

---

### 通用 ZIP 内查看（docx/xlsx/pptx 本质是 ZIP）

**列出内部文件结构：**
```bash
python -c "from zipfile import ZipFile; z=ZipFile(r'文件路径'); [print(f'{i.filename} ({i.file_size} bytes)') for i in z.infolist()]"
```

---

### 注意事项

1. 路径中的反斜杠必须用 `r'原始路径'`（raw string）包裹，避免转义问题
2. 中文路径直接传入 r-string 即可，无需额外处理
3. 文件较大时控制输出量，避免撑爆上下文
4. 如需导出提取结果，用 `write_file` 工具写入项目目录，**不要**在 python 脚本里直接写文件（`open('...','w')` 会被拦）
