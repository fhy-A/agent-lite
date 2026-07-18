---
name: image-generation
description: 使用 matplotlib 和 Pillow 生成图表、统计图和数据可视化图片
keywords: matplotlib, pillow, 数据+可视化, 画+图表, 生成+图表, 柱状图, 折线图, 饼图, 散点图, chart, data+plot
tools: run_command, write_file
---

## 图片与图表生成

本项目已预装 `matplotlib` 和 `Pillow`。使用 `python -c "..."` 一行执行，输出 PNG 文件到项目目录。

---

### 核心规则

1. **所有图片保存到项目 `output/` 目录**，文件名用英文
2. 禁止在脚本里写 `input()`、`plt.show()`、`plt.pause()` 等交互/阻塞指令
3. 使用非交互式后端：`import matplotlib; matplotlib.use('Agg')`
4. 中文字体：`plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']`
5. `python -c` 必须在一行内，多行用 `\n` 连接；超过 2000 字符就写脚本文件然后 `python script.py` 执行

---

### 柱状图

```bash
python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; plt.rcParams['font.sans-serif']=['Microsoft YaHei']; data={'产品':['A','B','C','D'],'销量':[120,95,150,80]}; plt.figure(figsize=(10,5)); colors=['#1B3A5C','#2C5F8A','#4A7FB5','#82B8DA']; plt.bar(data['产品'],data['销量'],color=colors,width=0.6); plt.title('产品销量对比',fontsize=16,fontweight='bold',color='#1B3A5C',pad=15); plt.xlabel('产品',fontsize=12); plt.ylabel('销量',fontsize=12); plt.grid(axis='y',alpha=0.3); plt.tight_layout(); plt.savefig('output/bar-chart.png',dpi=150); print('saved')"
```

### 折线图

```bash
python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; import numpy as np; plt.rcParams['font.sans-serif']=['Microsoft YaHei']; months=['1月','2月','3月','4月','5月','6月']; a=[120,135,148,162,175,190]; b=[80,90,105,115,120,130]; plt.figure(figsize=(12,5)); plt.plot(months,a,'o-',color='#1B3A5C',linewidth=2.5,markersize=8,label='产品A'); plt.plot(months,b,'s--',color='#E8833A',linewidth=2.5,markersize=8,label='产品B'); plt.title('月度销售趋势',fontsize=16,fontweight='bold',color='#1B3A5C'); plt.legend(fontsize=11,loc='upper left'); plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig('output/line-chart.png',dpi=150); print('saved')"
```

### 饼图

```bash
python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; plt.rcParams['font.sans-serif']=['Microsoft YaHei']; labels=['CloudSync','DataViz','SecureVault','APIFlow','DataGuard']; sizes=[1608,1023,831,537,323]; colors=['#1B3A5C','#2C5F8A','#4A7FB5','#82B8DA','#B8D0E8']; explode=(0.05,0,0,0,0.05); plt.figure(figsize=(8,8)); wedges,texts,autotexts=plt.pie(sizes,explode=explode,labels=labels,colors=colors,autopct='%1.1f%%',startangle=140,pctdistance=0.8); [t.set_fontsize(11) for t in texts]; [t.set_color('white') for t in autotexts]; [t.set_fontweight('bold') for t in autotexts]; plt.title('Q2 营收分布',fontsize=16,fontweight='bold',color='#1B3A5C'); plt.tight_layout(); plt.savefig('output/pie-chart.png',dpi=150); print('saved')"
```

### 多子图仪表盘

脚本较长时创建临时文件执行（完事后删除）：

```bash
python -c "
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Q2 数据仪表盘', fontsize=18, fontweight='bold', color='#1B3A5C')
# subplot 1: 柱状图
axes[0,0].bar(['A','B','C','D'], [120,95,150,80], color=['#1B3A5C','#2C5F8A','#4A7FB5','#82B8DA'])
axes[0,0].set_title('产品销量')
axes[0,0].grid(axis='y', alpha=0.3)
# subplot 2: 折线图
axes[0,1].plot([1,2,3,4,5,6], [120,135,148,162,175,190], 'o-', color='#1B3A5C', linewidth=2)
axes[0,1].set_title('月度趋势')
axes[0,1].grid(alpha=0.3)
# subplot 3: 饼图
axes[1,0].pie([40,25,20,15], labels=['A','B','C','D'], colors=['#1B3A5C','#2C5F8A','#4A7FB5','#82B8DA'], autopct='%1.1f%%')
axes[1,0].set_title('占比')
# subplot 4: 散点图
import numpy as np
np.random.seed(42)
x = np.random.randn(50) + 2
y = x * 1.5 + np.random.randn(50) * 0.5
axes[1,1].scatter(x, y, c='#E8833A', alpha=0.6, s=60)
axes[1,1].set_title('相关性分析')
axes[1,1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig('output/dashboard.png', dpi=150)
print('saved')
"
```

### 使用 Pillow 处理已有图片

```bash
# 加水印
python -c "from PIL import Image,ImageDraw,ImageFont; img=Image.open('input.png'); draw=ImageDraw.Draw(img); draw.text((20,img.height-40),'Watermark',fill=(255,255,255,128)); img.save('output/watermarked.png'); print('saved')"

# 拼接两张图
python -c "from PIL import Image; a=Image.open('a.png'); b=Image.open('b.png'); w=max(a.width,b.width); result=Image.new('RGB',(w,a.height+b.height),'white'); result.paste(a,(0,0)); result.paste(b,(0,a.height)); result.save('output/combined.png'); print('saved')"

# 缩略图
python -c "from PIL import Image; img=Image.open('photo.jpg'); img.thumbnail((300,300)); img.save('output/thumb.jpg'); print('saved')"
```

### 常见错误及避免

| 错误 | 原因 | 避免方式 |
|------|------|----------|
| `msgs is not defined` | 变量未声明 | 每个脚本从头写，不引用不存在的变量 |
| `plt.show()` 阻塞 | 默认交互模式 | 使用 `matplotlib.use('Agg')` |
| 中文乱码/方框 | 无中文字体 | 加 `plt.rcParams['font.sans-serif']=['Microsoft YaHei']` |
| `ModuleNotFoundError` | 库未安装 | 先 `python -c "import matplotlib; print('ok')"` 确认 |
| 文件名中文/空格 | Windows 兼容 | 只用英文 + 下划线命名 |
| `FileNotFoundError: input.png` | 未确认文件存在 | 先 `dir` 或 `glob_files` 确认路径 |

### 非多模态模型的替代方案

对不支持图片识别的模型：用 `matplotlib` 把数据可视化为图表 PNG，模型通过代码逻辑分析数据值，不需要"看"图片。图表是给人看的，模型读数据就行。
