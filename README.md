# OCR 科举助手

Windows 本地科举答题辅助工具：框选剑网3科举题目区域后，使用本地 RapidOCR 识别文字，优先从本地 SQLite 题库模糊匹配答案；本地未命中时再查询 JX3BOX，并自动缓存结果。

## 已实现

- PySide6 桌面主界面
- 多显示器虚拟桌面框选题目区域
- 记忆截图区域
- `Alt + Q` 全局快捷键识别
- RapidOCR + ONNX Runtime 本地中文 OCR
- OCR 图像增强
- SQLite 本地题库
- RapidFuzz 本地容错匹配
- JX3BOX `pull-gplugin` 实时查询兜底
- 一键批量同步题库
- 远端查询结果自动写入本地
- Always-on-top 答案悬浮窗
- CLI 调试工具
- 自动化测试

OCR 图片不会上传到 JX3BOX；远端接口只接收识别后的题目文字。

## 环境

项目使用 Python `>=3.12,<3.14`，仓库的 `.python-version` 指定 3.13。`uv` 会自动准备合适的 Python。

```powershell
uv sync --extra dev
```

当前 OCR 技术栈为 `rapidocr + onnxruntime`。

## 启动桌面程序

```powershell
uv run ocr-keju-gui
```

首次使用建议：

1. 点击 **同步题库**，把当前 JX3BOX 科举题库写入本地 SQLite。
2. 把剑网3科举界面打开到正常位置。
3. 点击 **框选题目区域**，只框题目文字，尽量不要包含答案按钮和无关 UI。
4. 之后按 `Alt + Q` 即可识别。
5. 主窗口和右上角悬浮窗会显示答案、匹配度和 OCR 置信度。

配置保存在 `data/settings.json`，题库保存在 `data/questions.db`。

## CLI

初始化数据库：

```powershell
uv run ocr-keju init-db
```

同步当前 JX3BOX 科举题库：

```powershell
uv run ocr-keju sync
```

查询题目：

```powershell
uv run ocr-keju search "稻香村的村长是谁"
```

对本地图片 OCR：

```powershell
uv run ocr-keju ocr-image .\question.png
```

查看题库统计：

```powershell
uv run ocr-keju stats
```

## 查询链路

```text
屏幕题目区域
  -> 图像增强
  -> RapidOCR（本地）
  -> 文本标准化
  -> SQLite 完全匹配
  -> RapidFuzz 全库模糊匹配
      -> 达到阈值：本地直接返回
      -> 未达到阈值：pull-gplugin API 查询
          -> 写入 SQLite
          -> 选择最接近题目
          -> 返回答案
```

默认本地模糊匹配阈值为 `0.78`。

## 题库同步说明

`https://pull-gplugin.jx3box.com/api/exam?search=` 的空搜索会被拒绝，但对题型前缀支持模糊搜索。开发时验证 `search=单选题` 能一次返回 1453 条不同远端 ID、且标题均为正常的“单选题：...”记录，因此当前 `sync` 以此作为批量初始化入口。

单独按普通关键词搜索时，接口还能返回一些历史或异常编码变体，所以本地数据库条数可能高于 1453。这些记录会保留为远端缓存，但正常中文题目优先匹配标准题目。

JX3BOX 当前 PVX 前端源码还公开使用 `next2.jx3box.com/api/game/exam/search` 与 `.../random` 接口；本项目没有把随机接口当成“完整题库”依据，而是继续使用你指定的 `pull-gplugin` 接口作为题库答案来源。

## 数据目录

可通过环境变量修改：

```powershell
$env:OCR_KEJU_DATA_DIR="D:\ocr-keju-data"
uv run ocr-keju-gui
```

其他环境变量：

- `OCR_KEJU_API_BASE_URL`
- `OCR_KEJU_API_TIMEOUT`

## 测试

```powershell
uv run pytest
uv run rapidocr check
```

项目包含 API 解析、标准化、SQLite、本地缓存、模糊匹配、同步、配置持久化和 OCR 结果转换测试。
