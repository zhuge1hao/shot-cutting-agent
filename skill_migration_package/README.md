# 拆解 Skill 迁移包

这个目录把当前短视频拆解工作流拆成可迁移的模块，方便搬到其他 Codex 环境或其他机器。

## 目录结构

```text
skill_migration_package/
  skills/
    shot-cutting-agent/       镜头切分规则和学习记录
    shot-text-excel/          字幕 OCR、文案拆解、横向 Excel 生成规则
    scene-video-breakdown/    场景类视频的独立拆解规则
    audio-subtitle-transcript/ 无字幕视频的音频转写和时间戳文案规则
  project_scripts/
    shot_cutting_agent.py
    build_shot_text_excel_unified.py
    SHOT_CUTTING_AGENT_MODEL.md
  SKILL_INDEX.md
  MIGRATION_CHECKLIST.md
  install_skills.ps1
```

## 推荐迁移方式

1. 将 `skills/*` 复制到目标环境的 `$CODEX_HOME/skills/`。
2. 如需在项目根目录保留便携脚本，将 `project_scripts/*` 复制到目标项目目录。
3. 在目标环境安装 Python 依赖：`opencv-python`, `numpy`, `pillow`, `openpyxl`, `rapidocr_onnxruntime`。
4. 用 `MIGRATION_CHECKLIST.md` 做一次验证。

也可以在 PowerShell 里运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_skills.ps1 -CodexHome "$env:USERPROFILE\.codex" -ProjectRoot "<目标项目目录>"
```

## 核心命令模板

镜头切分：

```powershell
python <ProjectRoot>\shot_cutting_agent.py --video-file "<video.mp4>" --output-dir "<ProjectRoot>\output\test"
```

生成 Excel：

```powershell
python <ProjectRoot>\build_shot_text_excel_unified.py --video-file "<video.mp4>" --output-dir "<ProjectRoot>\output\test" --report-mode model --disable-same-subtitle-merge --subtitle-region bottom --ocr-workers 6
```

有基准图时：

```powershell
python <ProjectRoot>\shot_cutting_agent.py --video-file "<video.mp4>" --output-dir "<ProjectRoot>\output\test" --reference-img-dir "<reference_img_dir>"
python <ProjectRoot>\build_shot_text_excel_unified.py --video-file "<video.mp4>" --output-dir "<ProjectRoot>\output\test" --report-mode reference --disable-same-subtitle-merge --subtitle-region bottom --ocr-workers 6
```

## 无字幕视频：音频转文案

当视频没有白色字幕时，安装可选音频依赖：

```powershell
python -m pip install -r <RepoRoot>\requirements-audio.txt
```

先生成带时间戳的音频文案：

```powershell
python <ProjectRoot>\skills\audio-subtitle-transcript\scripts\transcribe_video_audio.py --video-file "<video.mp4>" --output-dir "<ProjectRoot>\output\test\audio_transcripts" --model-size small --language zh
```

再生成 Excel，并用 `--no-subtitle` 禁用 OCR 字幕读取：

```powershell
python <ProjectRoot>\build_shot_text_excel_unified.py --video-file "<video.mp4>" --output-dir "<ProjectRoot>\output\test" --report-mode model --disable-same-subtitle-merge --no-subtitle --timed-transcript-json "<ProjectRoot>\output\test\audio_transcripts\<video_stem>_transcript.json"
```
