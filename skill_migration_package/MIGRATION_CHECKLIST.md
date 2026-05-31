# 迁移检查清单

## 安装位置

- `skills/shot-cutting-agent` 已复制到目标 `$CODEX_HOME/skills/shot-cutting-agent`
- `skills/shot-text-excel` 已复制到目标 `$CODEX_HOME/skills/shot-text-excel`
- `skills/scene-video-breakdown` 已复制到目标 `$CODEX_HOME/skills/scene-video-breakdown`
- `project_scripts/shot_cutting_agent.py` 已复制到目标项目根目录
- `project_scripts/build_shot_text_excel_unified.py` 已复制到目标项目根目录

## Python 依赖

至少确认：

```powershell
python - <<'PY'
import cv2, numpy, PIL, openpyxl
from rapidocr_onnxruntime import RapidOCR
print("deps ok")
PY
```

如果缺 RapidOCR：

```powershell
python -m pip install rapidocr_onnxruntime -i https://pypi.org/simple
```

常见依赖：

```powershell
python -m pip install opencv-python numpy pillow openpyxl rapidocr_onnxruntime -i https://pypi.org/simple
```

## 功能验证

1. 选一个 30-60 秒测试视频。
2. 跑镜头切分：

```powershell
python <ProjectRoot>\shot_cutting_agent.py --video-file "<video.mp4>" --output-dir "<ProjectRoot>\output\test"
```

3. 确认生成：

```text
output/test/<video_stem>/model_optimized/model_optimized_shot_report.json
output/test/<video_stem>/model_optimized/evidence/*.jpg
```

4. 跑 Excel：

```powershell
python <ProjectRoot>\build_shot_text_excel_unified.py --video-file "<video.mp4>" --output-dir "<ProjectRoot>\output\test" --report-mode model --disable-same-subtitle-merge --subtitle-region bottom --ocr-workers 6
```

5. 检查 Excel：

- 列数等于镜头数 + A 列。
- 嵌入图片数量等于镜头数。
- 字幕只来自本镜头时间范围。
- 水印、包装字、免责声明没有进入 `文案`。

## 迁移后常用参数

- 字幕在下方：`--subtitle-region bottom`
- 字幕在上方：`--subtitle-region top`
- 字幕上下都有：`--subtitle-region top-bottom`
- 字幕浮在中间：`--subtitle-region wide`
- 字幕需和画面对齐：`--disable-same-subtitle-merge`
- 提高 OCR 召回但保持速度：`--targeted-ocr-frame-budget 96` 或 `128`
- 只有最后兜底才用：`--full-ocr-sampling`

