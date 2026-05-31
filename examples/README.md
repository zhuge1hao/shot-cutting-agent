# 示例素材说明

仓库不包含真实业务视频、基准图或生成 Excel。请在本地按以下结构准备素材：

```text
videos/
  test/
    sample.mp4
    imgs-sample/
      001.jpeg
      002.jpeg
      ...
output/
  test/
```

## 自动拆解

```powershell
python .\shot_cutting_agent.py --video-file ".\videos\test\sample.mp4" --output-dir ".\output\test"
python .\build_shot_text_excel_unified.py --video-file ".\videos\test\sample.mp4" --output-dir ".\output\test" --report-mode model --disable-same-subtitle-merge --subtitle-region bottom --ocr-workers 6
```

## 使用人工基准图校准

```powershell
python .\shot_cutting_agent.py --video-file ".\videos\test\sample.mp4" --output-dir ".\output\test" --reference-img-dir ".\videos\test\imgs-sample"
python .\build_shot_text_excel_unified.py --video-file ".\videos\test\sample.mp4" --output-dir ".\output\test" --report-mode reference --disable-same-subtitle-merge --subtitle-region bottom --ocr-workers 6
```

字幕区域可根据素材改为 `top`、`top-bottom`、`wide` 或 `auto`。

