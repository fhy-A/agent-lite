# Claude Code CLI 安装教程（面向零基础用户）

> 适用系统：Windows / macOS  
> 更新时间：2026-07-21  
> 适用版本：Claude Code 2.x（原生二进制版本）

---

## 一、Claude Code 是什么

Claude Code 是 Anthropic 官方提供的**命令行 AI 编程助手**。安装后，你在终端里敲 `claude` 就能和 AI 对话，让它帮你读代码、改代码、跑命令。

---

## 二、前置准备：安装 Node.js

Claude Code 通过 npm（Node.js 的包管理器）安装，所以你需要先装 Node.js。

### Windows 用户

1. 打开浏览器，访问 **https://nodejs.org**
2. 点击左边的 **"LTS"** 按钮（长期支持版，最稳定），下载安装包
3. 双击下载的 `.msi` 文件，一路点 **Next**，全部默认选项即可
4. 安装完成后，**关掉当前命令行窗口，重新打开一个新的**（这步很重要，否则 `node` 命令不会被识别）

### macOS 用户

1. 同样访问 **https://nodejs.org**，下载 LTS 版的 `.pkg` 安装包
2. 双击安装，一路继续即可
3. 安装完成后打开终端验证

### 验证 Node.js 是否装好

按下 `Win + R`，输入 `cmd` 回车（macOS 打开"终端"），输入：

```
node -v
```

如果出现 `v22.x.x` 或 `v24.x.x` 就说明装好了。**版本必须 ≥ 22**，如果低于 22，去官网重新下载最新 LTS。

再输入：

```
npm -v
```

出现版本号就是正常的。

---

## 三、安装 Claude Code

### 3.1 打开命令行

- **Windows**：按 `Win + R`，输入 `cmd`，回车
- **macOS**：打开"终端"应用（在"启动台 → 其他"里）

### 3.2 执行安装命令

**复制下面这行命令**，在命令行窗口里**右键粘贴**，然后回车：

```
npm install -g @anthropic-ai/claude-code --registry=https://registry.npmjs.org/
```

> **为什么要加 `--registry=https://registry.npmjs.org/`？**  
> 很多国内用户配置了淘宝/腾讯等 npm 镜像加速，但这些镜像只代理 npm 包本身，无法正确下载 Claude Code 所需的原生程序（约 250MB）。加上这个参数可以强制从官方源下载，避免安装出问题。

### 3.3 等待安装完成

安装过程通常需要 2-5 分钟（需下载约 250MB 的原生程序），安装后约占用 500MB 磁盘空间。你会看到类似这样的输出：

```
added 2 packages in 15s
```

看到这个就说明安装成功了。

### 3.4（推荐）一劳永逸：让 `--registry` 永久生效

每次安装和更新都要加 `--registry=https://registry.npmjs.org/`，容易忘记。运行下面这行命令，一次配置，永久有效：

```
npm config set '@anthropic-ai:registry' https://registry.npmjs.org/
```

> 这行命令的意思是：**只让 `@anthropic-ai` 的包走官方源**，其他包继续用你的镜像加速（淘宝/腾讯云等）。今后安装和更新都不需要手动加 `--registry` 参数了。

---

## 四、验证安装

在命令行里输入：

```
claude --version
```

如果出现版本号（比如 `2.1.216`），就说明安装完全成功，可以直接用了。

### 常见的失败情况

#### 错误 1：提示 "claude 不是内部或外部命令"

说明 npm 的全局安装目录没有加入系统 PATH。解决方法：

1. 在命令行输入 `npm config get prefix`，记住输出的路径
2. **Windows**：打开"系统属性 → 高级 → 环境变量"，在"用户变量"里找到 `Path`，添加 `C:\Users\你的用户名\AppData\Roaming\npm`，确定后重启命令行
3. **macOS**：一般不会遇到这个问题，如果遇到了，运行 `echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zshrc` 然后重启终端

#### 错误 2：提示 "指定的可执行文件不是此操作系统平台的有效应用程序"

这就是镜像下载问题。**先卸载再重新安装**：

```
npm uninstall -g @anthropic-ai/claude-code
npm install -g @anthropic-ai/claude-code --registry=https://registry.npmjs.org/
```

如果你之前用淘宝镜像（`npmmirror.com`）或腾讯云镜像（`mirrors.cloud.tencent.com`）安装过，一定要按上面两步走。

#### 错误 3：安装卡住不动 / 超时

网络原因导致无法连接 `registry.npmjs.org`。可以尝试：

- 换个网络环境（比如连手机热点）
- 如果你开了代理软件，确保代理模式为**全局模式**而非 PAC 模式，否则 npm 可能不走代理
- 如果公司网络有限制，联系 IT 开放 `registry.npmjs.org` 的访问

---

## 五、第一次使用

安装好后，输入 `claude` 回车，首次运行会提示你完成以下操作：

1. **登录 Anthropic 账号**：浏览器会自动打开，用你的 Google 账号或邮箱登录
2. **选择付费方案**：Claude Code 需要绑定付费方式（Max 方案或 API Key）
3. **授权完成**后，命令行会显示 `Claude Code` 就绪

然后你就可以直接在终端里和 Claude 对话了。试试输入：

```
帮我看看当前文件夹里有什么文件
```

---

## 六、更新 Claude Code

Claude Code 更新非常频繁（几乎每天都有新版）。更新命令：

```
npm install -g @anthropic-ai/claude-code@latest --registry=https://registry.npmjs.org/
```

> 如果你已经按照 3.4 节配置了作用域 registry，可以省略 `--registry` 参数。另外注意，`npm update` 对全局包有时更新不完整，建议直接用 `npm install -g @latest`。

---

## 七、卸载

如果不用了，卸载命令：

```
npm uninstall -g @anthropic-ai/claude-code
```

---

## 八、常见问题速查

| 问题 | 解决方法 |
|------|---------|
| node -v 版本低于 22 | 去 nodejs.org 下载最新 LTS |
| 提示不是有效应用程序 | 用官方 registry 重新安装 |
| 装完不能用，claude 命令找不到 | 检查 PATH 环境变量 |
| 安装一直转圈没反应 | 换网络，或确保代理为全局模式 |
| An error occurred during authentication | 网络无法访问 api.anthropic.com，检查代理 |

---

> 如果以上步骤都试过了还是不行，把命令行里的完整报错信息复制下来，去 Claude Code 的 GitHub Issues 页面搜索或提问：https://github.com/anthropics/claude-code/issues
