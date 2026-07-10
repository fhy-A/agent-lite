# @图片路径 → 模型自主读取图片

## 需求

用户在消息中通过 `@path/to/image.png` 引用图片时，如果图片没有以 `image_url` 附加到消息中，模型需要能自主通过 `read_file` 读取该图片并真正"看到"图片内容。

## 当前问题

`server.py` 的 `tool_read_file` 对图片文件已经返回 base64 + mime + `binary: true` 标记，不抛错。但模型拿到 base64 是纯文本，无法当作图片识别——只有 `image_url` 格式的消息内容块才能触发多模态识别。

## 需要做的事

在 `app.js` 中拦截 `read_file` 返回的 `binary: true` 的工具结果，检测到图片 base64 时，自动往对话中注入一条带 `image_url` 的用户消息，让模型在下一轮能看到这张图。
