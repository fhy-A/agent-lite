# Import 语句统计报告

**统计文件**：`server.py`（158.5 KB，项目核心文件）  
**统计时间**：2026-07-17 20:31

---

## 总览

| 指标 | 数量 |
|------|------|
| **Import 语句总数** | **21** |
| 简单 import（`import xxx`） | 16 |
| 别名 import（`import xxx as yyy`） | 1 |
| 从模块导入（`from xxx import yyy`） | 4 |

---

## 按语法分类

### 简单 import（16 条）

```python
import base64
import codecs
import ctypes
import difflib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import uuid
import sys
import threading
import time
import webbrowser
import pystray          # 条件导入（try 块内）
```

### 别名 import（1 条）

```python
import datetime as dt
```

### from ... import（4 条）

```python
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, parse, request
from PIL import Image, BmpImagePlugin, IcoImagePlugin, PngImagePlugin  # 条件导入（try 块内）
```

---

## 按来源分类

| 分类 | 数量 | 模块 |
|------|------|------|
| **标准库** | 19 | http.server, pathlib, urllib, base64, codecs, ctypes, datetime, difflib, json, mimetypes, os, re, shutil, subprocess, uuid, sys, threading, time, webbrowser |
| **第三方库** | 2 | pystray, PIL（均在 try 块内，为可选依赖） |

---

## 备注

- 第三方库 pystray 和 PIL 使用 `try/except ImportError` 做条件导入，缺失时不阻塞服务启动（`TRAY_AVAILABLE = False`）。
- 标准库占比约 90%，依赖非常轻量。
