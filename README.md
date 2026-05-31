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
python -m pip install -r .\requirements.txt
```

## 通过 GitHub 安装 Skills

### 在 Codex 中直接安装

将下面这段请求发送给 Codex。Codex 会使用内置 `skill-installer` 从 GitHub 安装三个 skill：

```text
请从 GitHub 仓库 zhuge1hao/shot-cutting-agent 安装以下 skills：
- skills/shot-cutting-agent
- skills/shot-text-excel
- skills/scene-video-breakdown
```

安装后重启 Codex，使新 skills 生效。

当前仓库为私有仓库时，安装用户需要先获得仓库访问权限，并在本机登录 Git 凭据。若希望任何人都可以直接安装，请将仓库调整为公开。

### 克隆后手工安装

```powershell
git clone https://github.com/zhuge1hao/shot-cutting-agent.git
cd .\shot-cutting-agent
python -m pip install -r .\requirements.txt
powershell -ExecutionPolicy Bypass -File .\install_skills.ps1
```

如果目标机器已经存在同名 skill，显式使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_skills.ps1 -Force
```

需要同时将便携脚本复制到一个工作目录时：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_skills.ps1 -ProjectRoot "D:\shot-cutting-workspace"
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

旧版迁移包仍保留在 `skill_migration_package/`，用于兼容已有迁移方式。新用户优先使用仓库根目录的 `skills/` 和 `install_skills.ps1`。

```powershell
powershell -ExecutionPolicy Bypass -File .\skill_migration_package\install_skills.ps1 -CodexHome "$env:USERPROFILE\.codex" -ProjectRoot "<目标项目目录>"
```

## 数据说明

真实视频、基准图、生成 Excel、OCR 缓存和输出目录不提交到 GitHub。需要本地复现时，按 [examples/README.md](examples/README.md) 准备素材目录。
