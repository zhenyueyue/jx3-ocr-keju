# OCR 科举助手

Windows 本地科举答题辅助工具：框选剑网3科举的“题目 + 全部选项”区域后，程序持续检测画面变化；出现新题目时自动使用本地 RapidOCR 识别、优先匹配 SQLite 题库，并直接在游戏画面上描边正确选项。本地未命中时再查询 JX3BOX，并自动缓存结果。

## 已实现

- PySide6 桌面主界面
- 多显示器虚拟桌面框选“题目 + 全部选项”区域
- 记忆检测区域
- 常驻实时画面变化检测，无需快捷键
- RapidOCR + ONNX Runtime 本地中文 OCR
- OCR 图像增强
- SQLite 本地题库
- RapidFuzz 本地容错匹配
- JX3BOX `pull-gplugin` 实时查询兜底
- 一键批量同步题库
- 远端查询结果自动写入本地
- 未收录题自动提取题干和选项，可一键点正确答案补录
- 用户补录题优先于 JX3BOX，后续同步不会覆盖用户答案
- Always-on-top、鼠标穿透的正确答案原位描边框
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
3. 点击 **框选题目 + 选项区域**，把完整题干和所有答案选项都框进去，尽量不要包含其他会持续动画的 UI。
4. 框选完成后实时检测会自动开启；程序会优先监控上一题的题干实际区域，用文字变化像素比例判断是否换题。
5. 一旦检测到新题，上一题的绿色框会立即消失，并在检测区域外显示 **“检测到新题 · 识别中…”**，随后自动 OCR。
6. 匹配到答案后，会直接在游戏画面上给正确选项画绿色描边框；该框鼠标穿透，不影响点击游戏。
7. 如果新题已经检测到但答案没有成功定位，会显示 **“已检测新题 · 未定位答案”**，便于区分“没换题”和“识别失败”。
8. 如果本地和 JX3BOX 都没有这道题，主界面会出现 **“题库未收录 · 点一下正确答案即可补录”**，题目和选项会由本次 OCR 自动填好；直接点正确选项即可写入本地用户题库。
9. 补录成功后当前题会立即画出绿色答案框，下一次再遇到这道题会直接自动命中；用户补录答案优先级高于远端题库。
10. 如需临时停止，可点击 **暂停实时检测**；**立即检测** 可用于手动强制识别当前画面。

源码开发模式下，配置保存在 `data/settings.json`，题库保存在 `data/questions.db`。Windows 打包版则使用 `%LOCALAPPDATA%\jx3-ocr-keju\` 作为持久数据目录，因此重新打包、删除或覆盖 `dist` 不会再删除题库和用户补录题。

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
屏幕题目 + 选项区域
  -> 轻量画面变化检测
  -> 仅在新题出现时进行图像增强
  -> RapidOCR（本地，保留文字坐标）
  -> 自动从顶部 OCR 行提取题干
  -> 文本标准化
  -> SQLite 完全匹配
  -> RapidFuzz 全库模糊匹配
      -> 达到阈值：本地直接返回
      -> 未达到阈值：pull-gplugin API 查询
          -> 有结果：写入 SQLite，选择最接近题目并返回答案
          -> 无结果：自动生成待补录题目 + 选项
              -> 用户点正确选项
              -> 保存为 source=user
              -> 立即刷新本地题库索引
  -> 用答案文字匹配 OCR 选项坐标
  -> 在屏幕原位置描边正确选项
```

默认本地模糊匹配阈值为 `0.78`。

## 题库同步说明

`https://pull-gplugin.jx3box.com/api/exam?search=` 的空搜索会被拒绝，但对题型前缀支持模糊搜索。开发时验证 `search=单选题` 能一次返回 1453 条不同远端 ID、且标题均为正常的“单选题：...”记录，因此当前 `sync` 以此作为批量初始化入口。

单独按普通关键词搜索时，接口还能返回一些历史或异常编码变体，所以本地数据库条数可能高于 1453。这些记录会保留为远端缓存，但正常中文题目优先匹配标准题目。

JX3BOX 当前 PVX 前端源码还公开使用 `next2.jx3box.com/api/game/exam/search` 与 `.../random` 接口；本项目没有把随机接口当成“完整题库”依据，而是继续使用你指定的 `pull-gplugin` 接口作为题库答案来源。

## 数据目录

Windows 打包版默认使用：

```text
%LOCALAPPDATA%\jx3-ocr-keju\
├─ questions.db
└─ settings.json
```

源码开发模式仍使用项目根目录的 `data/`。本地 `scripts/build_windows.ps1` 在 PyInstaller 清理 `dist` 之前，会把旧的项目 `data/` 和旧版 `dist/ocr-keju/data/` 中尚未迁移的运行数据复制到持久目录；打包程序自身启动时也会尝试迁移旧版程序目录中的数据。迁移只补缺失文件，绝不会覆盖已经存在的持久数据库。

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

## 自动发布 Release

仓库包含 `.github/workflows/release.yml`。推送 `v*` 标签后，GitHub Actions 会在 Windows Runner 上自动：

1. 安装 Python 3.13 和 `uv`。
2. 按 `uv.lock` 安装依赖。
3. 执行测试与 `rapidocr check`。
4. 使用 PyInstaller 构建 Windows x64 程序。
5. 将完整 `dist/ocr-keju` 目录压缩成 ZIP。
6. 创建 GitHub Release 并上传 ZIP。

例如发布测试版：

```powershell
git tag v0.1.0-beta.1
git push origin v0.1.0-beta.1
```

标签名包含 `-` 时（例如 `beta`、`rc`）会自动标记为 Pre-release。

正式版：

```powershell
git tag v0.1.0
git push origin v0.1.0
```

生成的附件命名类似：

```text
jx3-ocr-keju-v0.1.0-windows-x64.zip
```

也可以在 GitHub Actions 页面手动运行工作流进行构建验证；手动运行只上传 Actions Artifact，不自动创建 Release。
