---
name: scene-video-breakdown
description: Split scene-driven short videos into calibrated visual story beats and generate horizontal Excel breakdowns with bottom-white-subtitle OCR. Use when Codex needs to process scenario, atmosphere, lifestyle, brand-film, or narrative scene videos separately from product口播, underwear/bra detail-proof, mixed-cut sales, or activity promotion videos.
---

# Scene Video Breakdown

## Purpose

Use this skill for scene-driven videos where the main value is visual storytelling, mood, character movement, environment change, or narrative rhythm. Do not apply the high-density product-proof rules used for underwear, bra, shapewear, 520 promotion, KOC口播, or product混剪 unless the scene video itself clearly enters a product-proof sequence.

## Workflow

Resolve the installed skill scripts, then run the normal shot cutter from the current video project:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$shotCutter = Join-Path $codexHome "skills\shot-cutting-agent\scripts\shot_cutting_agent.py"
$shotTextExcel = Join-Path $codexHome "skills\shot-text-excel\scripts\build_shot_text_excel_unified.py"
python $shotCutter --video-file "<video.mp4>" --output-dir ".\output\test"
```

If a human reference folder is provided, calibrate with it:

```powershell
python $shotCutter --video-file "<video.mp4>" --output-dir ".\output\test" --reference-img-dir "<reference_img_dir>"
```

Generate the Excel with subtitle-picture alignment:

```powershell
python $shotTextExcel --video-file "<video.mp4>" --output-dir ".\output\test" --report-mode reference --disable-same-subtitle-merge
```

Use `--report-mode model` only when no reference folder exists. Use `--report-mode reference` when reference calibration exists.

## Scene Cutting Rules

- Never cut by equal time intervals.
- Keep scene state changes: location change, camera angle change, character entrance/exit, body action start/end, prop interaction, mood shift, lighting/composition shift, or narrative beat.
- Prefer stable, readable scene states over transitional motion frames.
- Compress adjacent frames that show the same person, same composition, same action continuation, and no new story information.
- Do not keep every small product or texture detail just because it changes slightly. Scene videos should preserve the story beat, not every product-proof micro-state.
- Keep subtitle-state changes only when the visual state also matters. A new bottom white subtitle alone is not enough if the picture remains the same.
- If a reference folder is clean and intentional, treat it as the scene-beat baseline. Reference-calibrated output may have fewer columns than the generic model because human scene choices often prefer broader story states.

## Excel Rules

- Extract only bottom white subtitles for `文案`; ignore text printed inside the picture, product cards, ingredient cards, or decorative overlay text unless the user explicitly asks otherwise.
- When the user says subtitles must align with the picture, always use `--disable-same-subtitle-merge`.
- Keep one Excel column per final shot. Blank `文案` is acceptable when the shot has no bottom white subtitle.
- Fill planning rows sparsely. Use `视频结构（画面）` to mark scene jobs such as `场景开场`, `人物动作`, `氛围承接`, `环境细节`, `情绪转场`, `产品自然露出`, `字幕信息承接`, or `收尾画面`.
- Do not force product-selling labels like `快速产品证明`, `收腹证明`, `活动促销`, or `价格利益点` unless the scene explicitly functions that way.

## Ubras 5.20 Calibration

Calibration source:

```text
video: videos/test/5.20-ubras.mp4
reference: videos/test/imgs5.20ubras
```

Learned result:

- Reference folder contained `36` human scene-state images.
- Generic raw candidates: `173`.
- Generic model output: `44` shots across `75.71s`.
- Reference-optimized output: `35` shots.
- Reference summary showed full baseline recall within `60` frames, with `33/36` within `45` frames and median match distance about `0.114`.
- Lesson: the generic model over-split the scene video. The calibrated scene baseline is closer to `0.46 shots/sec`, not the denser product-proof style.
- One pair of reference images collapsed into the same effective scene state; this is acceptable when the visual job is duplicated.

## Validation

After export, check:

- Data columns equal the final report shot count.
- Embedded images equal data columns.
- A1:A10 use the standard horizontal workbook row labels.
- Early scene columns are not accidentally merged by repeated subtitles.
- `文案` comes only from in-shot bottom white subtitle OCR and is not borrowed from neighboring shots.
