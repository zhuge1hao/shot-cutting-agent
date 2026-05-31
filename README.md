# Shot Cutting Agent

短视频镜头拆解、字幕 OCR 对齐和横向 Excel 生成工具。项目面向产品口播、内衣细节证明、快速混剪和场景类短视频，使用画面变化而不是固定时间间隔切分镜头。

## 核心能力

- 按动作、产品状态、模特姿势和画面职责变化切分镜头。
- 支持人工基准图回映视频帧，用于校准自动分割。
- 提取指定区域的白色字幕，并保持字幕与镜头图片对齐。
- 生成横向 Excel：每个镜头一列，嵌入参考图片。
- 提供可迁移的 Codex skills 和安装脚本。

## 环境依赖

建议使用 Python 3.12，并安装：

```powershell
python -m pip install opencv-python numpy pillow openpyxl rapidocr_onnxruntime
```

## 快速开始

镜头切分：

```powershell
python .\shot_cutting_agent.py --video-file "<video.mp4>" --output-dir ".\output\test"
```

字幕在下方时生成 Excel：

```powershell
python .\build_shot_text_excel_unified.py --video-file "<video.mp4>" --output-dir ".\output\test" --report-mode model --disable-same-subtitle-merge --subtitle-region bottom --ocr-workers 6
```

存在人工基准图时：

```powershell
python .\shot_cutting_agent.py --video-file "<video.mp4>" --output-dir ".\output\test" --reference-img-dir "<reference_img_dir>"
python .\build_shot_text_excel_unified.py --video-file "<video.mp4>" --output-dir ".\output\test" --report-mode reference --disable-same-subtitle-merge --subtitle-region bottom --ocr-workers 6
```

## 迁移 Skill

迁移包位于 `skill_migration_package/`。在目标机器执行：

```powershell
.\skill_migration_package\install_skills.ps1 -CodexHome "$env:USERPROFILE\.codex" -ProjectRoot "<目标项目目录>"
```

## 数据说明

真实视频、基准图、生成 Excel、OCR 缓存和输出目录不提交到 GitHub。需要本地复现时，按 [examples/README.md](examples/README.md) 准备素材目录。

