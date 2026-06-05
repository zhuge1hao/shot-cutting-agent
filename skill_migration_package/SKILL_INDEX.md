# Skill 拆解索引

## 1. shot-cutting-agent

用途：把短视频切成动作触发的镜头单元。

迁移内容：

- `skills/shot-cutting-agent/SKILL.md`
- `skills/shot-cutting-agent/references/learned-model-profile.md`
- `skills/shot-cutting-agent/scripts/shot_cutting_agent.py`
- 建议同时使用 `project_scripts/shot_cutting_agent.py`，这是当前项目里的最新执行版。

核心规则：

- 禁止等分切割。
- 镜头由动作、产品状态、模特姿态、手部位移、场景变化触发。
- 保留快速证明帧：不同产品状态、颜色属性、上身证明、结构细节、无痕/收腹/提臀/底裆证明。
- 抑制重复：同构图、同字幕、同动作连续且无新增画面价值时合并。
- 有人工基准图时，以基准图密度校准，但不是越多越好。

## 2. shot-text-excel

用途：从切分报告生成横向 Excel，嵌入镜头图片，提取白色字幕并填写拆解字段。

迁移内容：

- `skills/shot-text-excel/SKILL.md`
- `skills/shot-text-excel/scripts/*`
- 建议同时使用 `project_scripts/build_shot_text_excel_unified.py`，这是当前项目里的最新统一生成器。

核心规则：

- 横向展开：A 列为字段，B 列开始每列一个镜头。
- 固定字段：视频链接、镜头、时间、视频结构（画面）、文案框架、文案、用户视角、配音、音效39个、视频亮点。
- 图片必须嵌入 Excel，不只写路径。
- 字幕和画面对齐：使用 `--disable-same-subtitle-merge`，不借用相邻镜头字幕。
- 字幕区域由用户指定时直接传参：`bottom`, `top`, `top-bottom`, `wide`。
- 提速方案：证据帧 OCR + 定向补采样，默认 `--targeted-ocr-frame-budget 64`，必要时升到 `96/128`，不要一上来全量采样。
- 过滤固定水印、包装字、免责声明，保留真实白色口播字幕。

## 3. scene-video-breakdown

用途：处理场景/氛围/叙事视频，避免套用产品证明类高密度切分。

迁移内容：

- `skills/scene-video-breakdown/SKILL.md`

核心规则：

- 保留场景节拍：地点、人物进出、动作开始/结束、环境变化、情绪转场。
- 不保留每个产品微细节，除非它承担明确叙事或卖点证明。
- 有参考图时使用 reference 模式。

## 4. 项目脚本

`project_scripts/shot_cutting_agent.py` 和 `project_scripts/build_shot_text_excel_unified.py` 是迁移后最重要的执行脚本。

如果只迁移 skill 文档而不迁移这两个脚本，新环境可能知道规则，但无法复现当前自动切分和 Excel 生成效果。

## 5. audio-subtitle-transcript

用途：处理没有内嵌白色字幕的视频，从音频语音生成带时间戳的文案，并交给 Excel 生成器按镜头时间范围对齐。

迁移内容：
- `skills/audio-subtitle-transcript/SKILL.md`
- `skills/audio-subtitle-transcript/scripts/transcribe_video_audio.py`

核心规则：
- 用户明确说“无字幕”时使用，不从画面包装字、产品字或水印推断文案。
- 先生成 `<video_stem>_transcript.json`，再用 `build_shot_text_excel_unified.py --no-subtitle --timed-transcript-json ...` 填写 `文案`。
- 音频一句话跨多个镜头时可按时间重叠重复填入，优先保证字幕和画面时间对齐。
- 可选依赖单独安装：`python -m pip install -r requirements-audio.txt`。
