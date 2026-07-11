---
name: document-design
description: 生成美化后的 Word、PPT、Excel 和 Markdown 文档，控制排版、配色、字体和表格样式
keywords: 美化, 排版, 生成, 样式, 配色, 字体, 设计, pptx, docx, xlsx, markdown, 报告, 周报, 演示, 表格
tools: run_command, write_file, read_file
---

## 文档美化与生成

所有输出文件的首要原则：**专业、统一、可读性强**。生成的文档应该可以直接用于正式场合（汇报、演示、存档）。

## 通用规范

- 使用等宽字体 Consolas / Cascadia Code 展示代码，正文用微软雅黑或 Calibri
- 配色方案统一，一个文档内不超过 3 种主色
- 表格必须有交替行色（斑马纹），表头加粗+深色背景
- 数字千分位格式（1,234,567），百分比保留 1 位小数，货币加符号
- 输出目录优先用用户指定的路径；未指定时检查当前目录是否存在 `output/` 文件夹，有则存入，无则存到项目根目录

### 配色方案库（12 套）

选择配色时先判断文档用途和受众，再从下表中选取最匹配的方案。每套方案含 5 个色值：**主色 / 辅色 / 背景 / 强调 / 文字**。

---

#### 1. 经典商务蓝 Classic Navy
**场景**: 正式汇报、年报、金融数据、董事会演示
**风格**: 稳重专业，永不翻车

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#0D3B66` | PPT 封面底色、表头、一级标题 |
| 辅色 | `#4A7FB5` | 二级标题、图表辅助色 |
| 背景 | `#F0F4FA` | 页面背景、交替行浅色 |
| 强调 | `#E8833A` | 关键指标高亮、CTA 按钮 |
| 文字 | `#1A1A2E` | 正文、表格数据 |

---

#### 2. 极简灰白 Executive Minimal
**场景**: 法律文书、咨询报告、高端提案
**风格**: 极致简约，留白至上

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#12110E` | 标题、正文文字 |
| 辅色 | `#757976` | 二级标题、分割线 |
| 背景 | `#FAFAFA` | 页面底色 |
| 强调 | `#C19A6B` | 重点标记、装饰线条 |
| 文字 | `#272523` | 正文段落 |

---

#### 3. 科技蓝紫 Tech Innovation
**场景**: SaaS 产品介绍、技术分享、开发者大会
**风格**: 现代科技感，深色调为主

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#1E1B4B` | 封面/深色区域底色 |
| 辅色 | `#7C3AED` | 图表、标签、二级标题 |
| 背景 | `#F5F3FF` | 浅色页面背景 |
| 强调 | `#06D6A0` | 数据高亮、增长指标 |
| 文字 | `#1F1833` | 正文 |

---

#### 4. 自然绿意 Earth & Green
**场景**: ESG 报告、可持续发展、医疗健康、农业
**风格**: 自然有机，舒适亲和

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#2D5A3F` | 封面、表头、主标题 |
| 辅色 | `#5B8C5A` | 二级标题、图表辅助 |
| 背景 | `#F2F7F2` | 页面背景、交替行 |
| 强调 | `#E8B44F` | 关键数据、警示 |
| 文字 | `#2C2C2C` | 正文 |

---

#### 5. 温暖大地 Warm Earth
**场景**: 生活方式、教育、非营利、文化活动
**风格**: 温暖质朴，接地气不过度

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#8B5E3C` | 标题、重点区域 |
| 辅色 | `#C49A6C` | 二级元素、装饰 |
| 背景 | `#FEF9F3` | 页面底色 |
| 强调 | `#E07A5F` | 数据高亮、按钮 |
| 文字 | `#3D2E1F` | 正文 |

---

#### 6. 黑金奢华 Black & Gold
**场景**: 高端品牌、奢侈品、VIP 闭门会、颁奖典礼
**风格**: 极致奢华，权威感拉满

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#0C0C0C` | 封面深色底、标题 |
| 辅色 | `#D4AF37` | 装饰线、重点文字 |
| 背景 | `#F8F6F0` | 浅色页面 |
| 强调 | `#C9A84C` | 数据高亮 |
| 文字 | `#1C1C1C` | 正文 |

---

#### 7. 海洋深邃 Ocean Depth
**场景**: 海事、旅游、环保海洋、心理学
**风格**: 沉稳深邃，宁静致远

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#0A3143` | 深色底、表头 |
| 辅色 | `#1F788A` | 二级标题、图表 |
| 背景 | `#EDF6F9` | 页面背景 |
| 强调 | `#F4A261` | 关键指标 |
| 文字 | `#1A2B33` | 正文 |

---

#### 8. 活力霓虹 Neon Pop
**场景**: 市场营销、创意提案、产品发布、社交内容
**风格**: 大胆醒目，年轻活力

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#0F0F0F` | 深色区域底色 |
| 辅色 | `#CBF400` | 图表、标签、标题 |
| 背景 | `#F8F8F8` | 浅色页面 |
| 强调 | `#FF3366` | 关键数据、CTA |
| 文字 | `#1C1C1C` | 正文 |

---

#### 9. 柔和马卡龙 Soft Pastel
**场景**: 教育课件、母婴、生活方式、内部培训
**风格**: 温柔甜美，降低压迫感

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#6C8EB4` | 标题、表头 |
| 辅色 | `#B8D0E8` | 二级标题 |
| 背景 | `#F7F9FC` | 页面底色 |
| 强调 | `#F2A3B6` | 重点标记 |
| 文字 | `#3A3A3A` | 正文 |

---

#### 10. 工业水泥 Urban Concrete
**场景**: 建筑、制造、物流、工程
**风格**: 粗粝硬朗，效率感

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#4A4A4A` | 标题、表头 |
| 辅色 | `#8C8C8C` | 二级元素 |
| 背景 | `#F0EFEB` | 页面底色 |
| 强调 | `#D35D2C` | 关键指标、警示 |
| 文字 | `#2B2B2B` | 正文 |

---

#### 11. 暗夜模式 Dark Mode
**场景**: 代码演示、终端风格、开发者工具、晚间展示
**风格**: 护眼酷炫，屏幕优先

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#1A1B26` | 整体底色 |
| 辅色 | `#414868` | 卡片、面板 |
| 背景 | `#1A1B26` | 页面背景（同主色） |
| 强调 | `#7DCFFF` | 代码高亮、链接 |
| 文字 | `#C0CAF5` | 正文 |
| 绿色 | `#9ECE6A` | 正向指标 |
| 红色 | `#F7768E` | 负向指标 |

---

#### 12. 杂志编辑 Editorial
**场景**: 设计作品集、时尚、媒体、品牌手册
**风格**: 排版优先，大图大字

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | `#1C1C1C` | 大标题、页眉 |
| 辅色 | `#E63946` | 引用线、重点词 |
| 背景 | `#FFFBF5` | 暖白底色 |
| 强调 | `#457B9D` | 链接、脚注 |
| 文字 | `#2C2C2C` | 正文 |

---

### 配色速查表

| # | 方案 | 适用场景 | 一句话 |
|---|------|----------|--------|
| 1 | 经典商务蓝 | 年报/金融/董事会 | 稳重不出错 |
| 2 | 极简灰白 | 法律/咨询/高端提案 | 留白即高级 |
| 3 | 科技蓝紫 | SaaS/技术分享/开发者 | 深色科技感 |
| 4 | 自然绿意 | ESG/医疗/可持续 | 自然亲和 |
| 5 | 温暖大地 | 教育/非营利/生活 | 接地气 |
| 6 | 黑金奢华 | 奢侈品/VIP/颁奖 | 极致奢华 |
| 7 | 海洋深邃 | 海事/旅游/环保 | 宁静致远 |
| 8 | 活力霓虹 | 营销/创意/产品发布 | 大胆醒目 |
| 9 | 柔和马卡龙 | 教育课件/母婴/培训 | 温柔不压迫 |
| 10 | 工业水泥 | 建筑/制造/工程 | 粗粝硬朗 |
| 11 | 暗夜模式 | 代码/终端/晚场演示 | 屏幕优先 |
| 12 | 杂志编辑 | 设计/时尚/品牌手册 | 排版优先 |

### 配色使用原则

- **60-30-10 法则**: 60% 背景色，30% 辅色，10% 强调色
- 单页不超过 4 种颜色（背景、文字、辅色、强调色各一）
- 正增长用绿色（#2E7D32），负增长用红色（#C62828）
- 深色背景用白色/浅灰文字，浅色背景用深灰/黑色文字
- 选定一套方案后整份文档统一使用，不混搭

---

### Word 文档生成 (.docx)

```bash
python -c "
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)

# 标题
h = doc.add_heading('标题', level=1)
h.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = h.runs[0]
run.font.size = Pt(22)
run.font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)

# 副标题
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = sub.add_run('副标题 | 日期')
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

doc.add_paragraph()  # 空行

# 二级标题
doc.add_heading('章节标题', level=2)

# 正文段落
p = doc.add_paragraph('正文内容...')

# 表格（带斑马纹）
table = doc.add_table(rows=5, cols=3, style='Table Grid')
table.alignment = WD_TABLE_ALIGNMENT.CENTER
# 表头
for i, text in enumerate(['列1', '列2', '列3']):
    cell = table.rows[0].cells[i]
    cell.text = text
    for p in cell.paragraphs:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    from docx.oxml.ns import qn
    shading = cell._element.get_or_add_tcPr()
    shading_elm = shading.makeelement(qn('w:shd'), {qn('w:fill'): '1B3A5C'})
    shading.append(shading_elm)
# 数据行（交替色）
for ri, data in enumerate(data_rows, 1):
    for ci, val in enumerate(data):
        cell = table.rows[ri].cells[ci]
        cell.text = str(val)
    if ri % 2 == 0:
        for ci in range(3):
            shading = table.rows[ri].cells[ci]._element.get_or_add_tcPr()
            shading_elm = shading.makeelement(qn('w:shd'), {qn('w:fill'): 'F5F5F5'})
            shading.append(shading_elm)

# 页脚
doc.add_paragraph()
footer = doc.add_paragraph()
footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
run = footer.add_run('生成日期: YYYY-MM-DD')
run.font.size = Pt(9)
run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

doc.save('output/report.docx')
"
```

**要点**:
- 封面页居中 + 大标题 + 副标题 + 日期
- 表格表头深蓝底白字，数据行斑马纹，居中对齐
- 数字列右对齐，文字列左对齐
- 章节之间留空行，不拥挤

---

### PPT 演示文稿生成 (.pptx)

```bash
python -c "
from pptx import Presentation
from pptx.util import Inches, Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

prs = Presentation()
prs.slide_width = Inches(13.333)   # 16:9 宽屏
prs.slide_height = Inches(7.5)

# --- 封面页 ---
slide = prs.slides.add_slide(prs.slide_layouts[6])  # 空白版式
bg = slide.background
fill = bg.fill
fill.solid()
fill.fore_color.rgb = RGBColor(0x1B, 0x3A, 0x5C)  # 深蓝底

# 标题
txBox = slide.shapes.add_textbox(Inches(1.5), Inches(2), Inches(10), Inches(2))
tf = txBox.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = '演示标题'
p.font.size = Pt(40)
p.font.bold = True
p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
p.alignment = PP_ALIGN.CENTER

# 副标题
p2 = tf.add_paragraph()
p2.text = '副标题 | 日期'
p2.font.size = Pt(18)
p2.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
p2.alignment = PP_ALIGN.CENTER

# --- 内容页 ---
slide2 = prs.slides.add_slide(prs.slide_layouts[6])
# 顶部色条
shape = slide2.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(0.08))
shape.fill.solid()
shape.fill.fore_color.rgb = RGBColor(0x1B, 0x3A, 0x5C)
shape.line.fill.background()

# 页面标题
txBox = slide2.shapes.add_textbox(Inches(0.8), Inches(0.3), Inches(11), Inches(0.8))
tf = txBox.text_frame
p = tf.paragraphs[0]
p.text = '页面标题'
p.font.size = Pt(28)
p.font.bold = True
p.font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)

# 表格
rows, cols = 5, 3
table_shape = slide2.shapes.add_table(rows, cols, Inches(0.8), Inches(1.5), Inches(11.5), Inches(5))
table = table_shape.table
for ci in range(cols):
    cell = table.cell(0, ci)
    cell.text = f'列{ci+1}'
    for p in cell.text_frame.paragraphs:
        p.font.bold = True
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.alignment = PP_ALIGN.CENTER
    cell.fill.solid()
    cell.fill.fore_color.rgb = RGBColor(0x1B, 0x3A, 0x5C)

for ri in range(1, rows):
    for ci in range(cols):
        cell = table.cell(ri, ci)
        cell.text = f'数据{ri},{ci}'
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(12)
        if ri % 2 == 0:
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(0xF0, 0xF4, 0xF8)

prs.save('output/presentation.pptx')
"
```

**要点**:
- 16:9 宽屏，封面深蓝底白字
- 内容页顶部细色条 + 大标题
- 表格斑马纹，表头深蓝底白字
- 最多 5 页，每页信息量适中
- 最后总结页用 3 列布局：关键发现 | 建议 | 下一步

---

### Excel 美化 (.xlsx)

```bash
python -c "
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = '数据'

HEADER_FILL = PatternFill(start_color='1B3A5C', end_color='1B3A5C', fill_type='solid')
HEADER_FONT = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
DATA_FONT = Font(name='Calibri', size=11)
ALT_FILL = PatternFill(start_color='F0F4F8', end_color='F0F4F8', fill_type='solid')
THIN_BORDER = Border(
    left=Side(style='thin', color='CCCCCC'),
    right=Side(style='thin', color='CCCCCC'),
    top=Side(style='thin', color='CCCCCC'),
    bottom=Side(style='thin', color='CCCCCC'))

headers = ['列A', '列B', '列C']
for ci, h in enumerate(headers, 1):
    cell = ws.cell(row=1, column=ci, value=h)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = THIN_BORDER

data = [['数据']*3 for _ in range(10)]
for ri, row in enumerate(data, 2):
    for ci, val in enumerate(row, 1):
        cell = ws.cell(row=ri, column=ci, value=val)
        cell.font = DATA_FONT
        cell.border = THIN_BORDER
        if isinstance(val, (int, float)):
            cell.number_format = '#,##0.00'
        if ri % 2 == 0:
            cell.fill = ALT_FILL

# 自适应列宽
for ci in range(1, len(headers)+1):
    max_len = max(len(str(ws.cell(row=ri, column=ci).value or '')) for ri in range(1, len(data)+2))
    ws.column_dimensions[get_column_letter(ci)].width = min(max_len * 1.3 + 4, 40)

# 冻结首行
ws.freeze_panes = 'A2'

wb.save('output/data.xlsx')
"
```

**要点**:
- 表头深蓝底白字，冻结首行
- 斑马纹交替行，统一边框
- 自适应列宽（中文约 2 字符 = 1 英文宽度）
- 数字列右对齐，文本列左对齐，居中按内容决定
- 货币列加 ¥ 前缀和千分位

---

### Markdown 报告生成

```markdown
# 报告标题

> 生成日期：YYYY-MM-DD | 数据来源：xxx

---

## 1. 章节标题

简短说明段落，不超过 3 行。

| 列 A | 列 B | 列 C | 变化 |
|------|------|------|------|
| 项目 1 | 1,234 | 5,678 | <span style="color:#2E7D32">+12.5%</span> |
| 项目 2 | 890 | 756 | <span style="color:#C62828">-15.0%</span> |

### 关键发现

- **正向指标**：用 **加粗** 突出
- <span style="color:#C62828">**负向指标**</span>：用红色加粗警示
- 每个要点一行，不超过 8 个字概括

### 代码示例

\`\`\`python
import pandas as pd
df = pd.read_csv('data.csv')
result = df.groupby('category').sum()
\`\`\`

---

## 2. 总结与建议

1. **核心结论**：一句话
2. **行动建议**：可操作的具体步骤
3. **风险提示**：需要注意的问题

---
*报告由 Agent Lite 自动生成*
```

**要点**:
- 标题层级不超过 3 级，结构清晰
- 表格必须有表头分隔线 `|------|`
- 正负变化用颜色标记（若渲染支持）
- 结论先行，数据支撑在后
- 底部加生成说明和日期

---

### 检查清单

生成任何文档前确认：
- [ ] 配色不超过 3 种主色
- [ ] 表格有斑马纹 + 表头样式
- [ ] 数字格式正确（千分位、百分比、货币）
- [ ] 字体统一（中文微软雅黑/英文 Calibri）
- [ ] 页边距/留白适当，不拥挤
- [ ] 输出目录确认无误（用户指定 > output/ > 项目根目录）
