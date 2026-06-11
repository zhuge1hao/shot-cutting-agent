---
name: shot-text-excel
description: Generate per-video Excel copy-planning workbooks from shot-cutting reports, OCR text, and embedded shot thumbnails. Use when Codex needs to extract on-screen copy from segmented short videos, create one workbook per video, or update the horizontal shot planning Excel format.
---

# Shot Text Excel

## Overview

This skill turns existing shot-cutting outputs into per-video Excel workbooks for review and copy planning. It reads shot reports, runs OCR on each shot evidence frame, prepares thumbnails, then exports one horizontal workbook per video with embedded reference images.

## Expected Inputs

Run this skill from the project root that contains the shot-cutting `output` directory. The preferred shot report for each video is:

```text
output/<video_id>/reference_optimized/optimized_shot_report.json
```

If reference-optimized reports are unavailable, use model reports:

```text
output/<video_id>/model_optimized/model_optimized_shot_report.json
```

Each shot report should include an evidence frame path, action label, start/end time, and start/end frame.

If the user provides a source video/link line, treat it as the workbook-level `视频链接` value. If no link is provided, keep the `视频链接` cell blank.

## Workflow

1. Confirm dependencies.

Use the current Python environment. If OCR import fails, install RapidOCR:

```powershell
python -m pip install rapidocr_onnxruntime -i https://pypi.org/simple
```

For Excel export, call `load_workspace_dependencies` and use the bundled Node runtime. If the project root has no `node_modules` and the returned dependency metadata includes a usable `node_modules` path, create a junction from the project root to that dependency folder before running the `.mjs` script.

2. Resolve the installed skill path. For new one-off videos, prefer the bundled unified Python builder:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$shotTextScript = Join-Path $codexHome "skills\shot-text-excel\scripts\build_shot_text_excel_unified.py"
python $shotTextScript --video-file "<video.mp4>" --output-dir ".\output\test" --report-mode model --disable-same-subtitle-merge --subtitle-region bottom --ocr-workers 6
```

The unified builder automatically uses `model_calibrated` first, then `reference_optimized`, then `model_optimized`; extracts the requested white subtitle region; preserves protected rapid proof frames; embeds images horizontally; and keeps the workbook row labels fixed.

3. Use the legacy multi-video workflow only when processing the older numbered batch format. Extract OCR text from shot evidence frames:

```powershell
python (Join-Path $codexHome "skills\shot-text-excel\scripts\extract_shot_text_ocr.py") --output-dir .\output --videos 1-11 --mode reference --target-width 900 --csv-file .\output\video_shot_text_ocr.csv --json-file .\output\video_shot_text_ocr.json
```

Use `--videos all`, `--videos 1-8`, or a comma list like `--videos 1,3,11` as needed. Use `--mode auto` when reference reports may be missing.

4. Prepare thumbnails for embedded workbook images.

```powershell
python (Join-Path $codexHome "skills\shot-text-excel\scripts\prepare_ocr_thumbnails.py") --root .
```

This writes:

```text
output/shot_text_excels/video_shot_text_ocr_with_thumbs.json
output/shot_text_excels/_thumbs/<video_id>/<shot_id>.jpg
```

5. Build one Excel workbook per video.

```powershell
node (Join-Path $codexHome "skills\shot-text-excel\scripts\build_individual_shot_text_excels.mjs") --root .
```

If using the bundled Node executable, replace `node` with the absolute `node.exe` path returned by `load_workspace_dependencies`.

When a video link is provided, pass it into the builder:

```powershell
node (Join-Path $codexHome "skills\shot-text-excel\scripts\build_individual_shot_text_excels.mjs") --root . --video-link "<user provided video link line>"
```

The workbooks are written to:

```text
output/shot_text_excels/video_01_shot_text.xlsx
output/shot_text_excels/video_02_shot_text.xlsx
...
```

For a new one-off video, use the bundled unified Python builder instead of creating another per-video script:

```powershell
python $shotTextScript --video-file "<video.mp4>" --output-dir ".\output\test" --excel-file "<optional output.xlsx>" --video-link "<optional link text>"
```

Speed rule: the unified builder caches evidence-frame OCR and targeted frame OCR under `output/shot_text_excels/_ocr_cache/` and uses `--ocr-workers` for first-pass OCR. Rebuilding the same video after template/copy tweaks should reuse these caches instead of re-OCRing frames. OCR crops are downscaled before recognition for speed, then boxes are mapped back for white-subtitle filtering; keep this enabled unless accuracy visibly drops. Do not change the OCR cache version for ordinary normalization or cleanup-rule updates, because cached text is normalized again when loaded. Use `--no-ocr-cache` only for debugging bad OCR cache, and use `--full-ocr-sampling` only when recall matters more than speed. The default fast mode uses evidence-frame OCR plus a bounded targeted fallback, not all-frame sampling. If the user tells you the subtitle region, pass it directly with `--subtitle-region` and do not use auto probing. Use `auto` only when the user does not specify where subtitles appear.

Default speed workflow: do not use `--full-ocr-sampling` on the first Excel generation unless the user explicitly asks for maximum recall. Generate with the specified `--subtitle-region`, `--disable-same-subtitle-merge` when alignment is required, and a bounded targeted budget. For normal bottom-subtitle videos start with `--targeted-ocr-frame-budget 48`; this keeps evidence-frame OCR plus near-end/start fallback while avoiding slow OCR over many blank or disclaimer-only frames. If important subtitles are still missing, raise the budget to `64`, then `96`; use `--full-ocr-sampling` only as a last diagnostic pass.

6.5 梵客隆/魔鬼身材收腹无痕提臀 calibration: the video had `89` model shots over about `214s`. First-pass cutting took about `68s`; Excel with budget `128` took about `30s` on warm OCR cache and pulled in 3 product-print false positives (`塑形裤呼吸/呵吸`) that had to be cleared. Budget `48` preserved the final `18` true bottom-subtitle cells with no fixed disclaimer/package text and is the preferred fast setting for this subtype.

Do not use the unified OCR mode as a perfect replacement for older transcript-driven workbooks. If the user provides a full transcript, pass that transcript through a transcript-aware workflow or keep the existing specialized transcript script until the unified builder has transcript alignment support. The 5.8 有棵树 workbook is transcript-driven, so OCR-only unified output changes the copy granularity.

Updated rule: the unified builder now supports transcript alignment. When the user gives a full口播/文案 transcript, pass it with `--transcript-text` or `--transcript-file`; the workbook should use the manual transcript as the primary `文案` source and fall back to OCR only where no transcript segment is assigned. When no transcript is given, use bottom-white-subtitle OCR.

No-subtitle audio rule: when the user says the video has no visible subtitles, use the `audio-subtitle-transcript` skill to create a timed transcript JSON, then generate Excel with `--no-subtitle --timed-transcript-json "<transcript.json>"`. This skips OCR and fills `文案` only from audio segments whose timestamps overlap each shot. Do not infer copy from product text in the picture. The no-subtitle flag must not change shot cutting or embedded images: use the same `--report-mode` and source shot report as the normal workflow, and validate that the `镜头` and `时间` rows are identical to a control workbook when comparing versions. If image differences are suspected, compare `xl/media/*` hashes, image dimensions, and worksheet anchors; they should match when the same report is used. Only copy/planning rows should differ.

Subtitle-image alignment rule: when the user says the Excel subtitles must align with the picture, generate with `--disable-same-subtitle-merge`. Each shot must remain one horizontal column, with its embedded image and `文案` taken only from OCR samples inside that shot's own time range. Do not carry the previous shot's subtitle forward, do not infer copy from product text in the image, and do not merge adjacent columns just because the same white subtitle continues. Blank `文案` is acceptable when no bottom white subtitle is visible in that shot.

For alignment-sensitive OCR, sample frames from within the shot boundaries only and prioritize the exact evidence frame embedded in Excel. Use evidence-frame OCR first, then targeted in-shot fallback samples; near-end and start frames are more useful than repeating the representative frame because the evidence frame has already been OCR'd. If multiple subtitle texts appear inside one long shot, do not choose a later longer subtitle just because it looks more complete; keep the text visible on the embedded evidence frame whenever it exists so `文案` aligns with the thumbnail. Never borrow from neighboring shots.

When a user reports missing subtitles after a fast run, do not immediately switch to full OCR. First rerun with the same explicit subtitle region and a higher targeted budget. Check whether the missing copy is in short windows at the start or near the end of otherwise blank shots. For top-bottom videos, the validated default is evidence OCR plus `--targeted-ocr-frame-budget 64`; on `5.25.mp4` this recovered the same 53 subtitle cells as the prior full-sampling run while cutting Excel generation from about 301 seconds to about 71 seconds, and cached reruns to about 2 seconds.

Latest speed calibration: on `5.28-video_品牌蕾丝质感内裤...`, downscaled OCR reduced first Excel generation from about `111s` to `84s` while increasing filled subtitles from `97` to `98`. Cached reruns were about `1.4s`; shot-cutting cache reuse was about `0.14s`. For speed-sensitive user requests, report both first-run time and cached rerun time.

6.10 lace underwear speed calibration: after enabling high-confidence short-subtitle retention, `--targeted-ocr-frame-budget 48` preserved the same `105/105` bottom-white-subtitle fill as the slower 64-frame pass. Cached rerun time was about `1.64s`. For similar bottom-subtitle underwear videos, use the default 48-frame budget first and escalate only when validation finds real missing subtitles.

For bottom-subtitle videos, remember that the actual speaking subtitle may sit in the lower-middle area rather than at the very bottom because bottom disclaimer text occupies the last band. Keep the bottom OCR band broad enough to capture these subtitles while still filtering fixed disclaimers and picture text. In 5.26 梵客隆/牛奶丝滑 underwear footage, broad bottom OCR recovered real subtitles such as `普通内裤你要给穿脏了`, but package text like `塑形裤|呼吸` and watermark variants such as `梵客隆V/Y` or `桥客隆V` must be removed from `文案`.

For intimate-apparel videos that carry fixed compliance disclaimers at the bottom, strip boilerplate such as `请树立正确价值观`, `仅为产品展示`, `非违反公序良俗`, `社会秩序`, `价值观`, and `非制造容貌焦虑` from `文案`. If OCR returns `真实字幕/免责声明`, keep only the true speaking subtitle before the disclaimer. If the OCR result is only disclaimer text, leave `文案` blank. In the 6.8 bra/tifting video this cleaned rows like `整件内衣一体成型/请树立正确价值观...` to `整件内衣一体成型` and removed pure disclaimer cells.

For 美宅/蚕丝/国风 underwear package shots, do not treat package print as bottom subtitle. Filter package OCR such as `美宅私物开袋即穿`, `私物开袋即穿`, or partial fragments like `物开袋即穿` when the user asks for white subtitles only. Common OCR correction: `我一口气买76条` should be normalized to `我一口气买了6条` when the visible subtitle shows `买了6条`.

For 美宅 product口播 videos, package print may overlap with the spoken subtitle in the same lower band. Strip the package prefix and keep the spoken subtitle when OCR returns forms like `美宅私物（开袋即穿 / 问了女知道`; normalize it to `问了才知道`. Other observed OCR fixes: `具的很明显` -> `真的很明显`, `属干` -> `属于`, `相当干` -> `相当于`, and `本白色底裆` -> `这个白色底裆`. Do not invent missing words for very short partial fragments; leave them as-is or blank if the subtitle cannot be recovered within the shot.

For reference-calibrated dense product proof videos, do not force a caption onto every reference state. If the evidence frame only shows a one-character fragment such as `穿`, leave `文案` blank rather than carrying a neighboring subtitle forward. Reference images may intentionally preserve visual proof states with no complete speaking subtitle; image-copy alignment is more important than filling every column.

When the user says subtitles may appear at the top of the video, run the unified builder with `--subtitle-region top-bottom` in addition to `--disable-same-subtitle-merge`. Keep the default `bottom` behavior for normal videos. In top-bottom mode, treat text in the upper subtitle band as possible `文案`, but still reject picture/product text in the middle of the image such as report-card text, package names, ingredient cards, or decorative claims.

When true speaking subtitles float in the middle of the frame, use `--subtitle-region wide` or leave the default `auto` to select it. This mode is for videos where the real white subtitle is not limited to the bottom band. It should still reject top disclaimers, side compliance text, package labels, brand watermarks, and high-saturation decorative title text. After using `wide`, verify a few empty and filled columns manually because this mode is more recall-oriented.

Subtitle region mapping from user instructions:
- `底部 / 下方 / 视频下方白字幕`: pass `--subtitle-region bottom`.
- `上方 / 顶部`: pass `--subtitle-region top`.
- `上方和下方 / 可能在上方也可能在下方`: pass `--subtitle-region top-bottom`.
- `中部 / 画面中间 / 不固定但不是包装文字`: pass `--subtitle-region wide` or `middle`.
- No explicit region: pass `--subtitle-region auto`.

5.24 Ufeel/brand summer underwear calibration: when using `imgs5.24-video_品牌夏款内裤` as baseline, generate from `--report-mode reference --subtitle-region bottom --disable-same-subtitle-merge`. Expected shape is about `121` shot columns / `121` embedded images / `118` filled subtitle cells. Empty columns around the single-word `穿` transition are acceptable and should not be backfilled from adjacent shots.

5.28 brand lace/pastel underwear reference calibration: when using `imgs5.28-video_品牌蕾丝质感内裤` as baseline, generate from `--report-mode reference --subtitle-region bottom --disable-same-subtitle-merge`. Expected shape is `132` shot columns / `132` embedded images / about `122` filled subtitle cells. The old model workbook had `110` columns and missed many first-minute proof states (`55` model vs `77` reference under `60s`), so the reference workbook should preserve those added visual columns even when the bottom subtitle repeats. Do not backfill blank columns from adjacent shots; image-copy alignment remains the priority.

For lace underwear / Ufeel-style videos, use the original specialized workbook density as the calibration baseline: `73` shot columns / `73` images / about `51` copy nodes. In this project, run unified generation with `--report-mode model --disable-same-subtitle-merge` for that calibration shape, because the old lace underwear script used `model_optimized` rather than `reference_optimized`. Do not over-compress lace underwear proof frames just because later reference output has fewer columns.

For 5.10 都市丽人 bra reference calibration, use:

```powershell
python $shotTextScript --video-file ".\videos\test\5.8+文胸+都市丽人经典官方+11名.mp4" --output-dir ".\output\test" --report-mode reference --disable-same-subtitle-merge
```

This preserves the `50` reference-image states from `imgs5.10+文胸+都市丽人经典官方+11名`. Do not let same-subtitle merging reduce a human reference-calibrated workbook unless the user explicitly says those reference states are duplicates.

When comparing an older workbook with a newer reference-calibrated workbook, expect source shot ids and time boundaries to shift. For 5.10 都市丽人, the new `50`-column reference workbook replaced many old source candidates rather than simply adding two columns. This is correct when reference images pick cleaner stable proof states. Compare by visual job and reference image state, not only by old `ModelShot` number.

Do not leave out comparison/verification frames immediately after an on-body effect shot. In Excel, label them as `上身效果对比证明`, `无痕效果对比`, `颜色/穿搭对比证明`, or `身形变化验证` as appropriate. Even if the subtitle is repeated or sparse, these frames are key proof columns rather than filler.

## Workbook Layout

Create one workbook per video. Do not merge all videos into one workbook unless the user explicitly asks.

Use a horizontal layout:

- Column A contains only field names.
- B, C, D, and subsequent columns each represent one shot.
- Row 1 is workbook-level metadata: A1 is `视频链接`, B1 contains the user-provided link text, and stays blank when no link is provided.
- Row 2 contains the shot id and an embedded thumbnail image for each shot column.
- Rows 3-10 contain planning data.

The required row labels are:

```text
视频链接
镜头
时间
视频结构（画面）
文案框架
文案
用户视角
配音
音效39个
视频亮点
```

Keep images embedded as workbook image objects, anchored to the shot column. Do not replace embedded images with file paths only.

## Filling Rules

The Excel builder script generates first-draft planning text from OCR text and action labels:

- `视频结构（画面）`: identify the shot phase and whether the frame is product detail, dialogue/subtitle, compliance notice, fast-cut freeze frame, or pure visual transition.
- `文案框架`: classify the copy role, such as hook, question-answer reveal, product proof, user pain point, compliance note, or closing reinforcement.
- `文案`: use the OCR text from the shot evidence frame.
- `用户视角`: explain the viewer angle, such as product evaluation, user experience, curiosity, compliance awareness, or bystander observation.
- `配音`: suggest voiceover style based on the text and shot role.
- `音效39个`: suggest an effect category or rhythm cue, such as whoosh, pop, ding, fabric movement, freeze-frame hit, or low-volume compliance cue.
- `视频亮点`: call out why the shot matters in the edit.

Treat generated planning text as an editable first draft. If OCR confidence is low or text is missing, preserve the shot and fill copy fields with visual/action-based placeholders instead of skipping the shot.

## Reference Writing Style

Match the style of short-video hit-breakdown workbooks:

- `视频结构（画面）`: use short scene labels or concise scene-function phrases, not long explanations. Good examples: `同行爆款画面`, `开袋`, `产品`, `模特上身`, `底档细节`, `产品多维度展示`, `生活场景，痛点突出`, `源头信任度+产品定位`.
- `文案框架`: classify the copy job in a compact phrase. Good examples: `疑问好奇拉停留`, `痛点警示开篇`, `主卖点留住人群`, `产品给到解决方案`, `打消顾虑，增加信任度`, `活动留人`.
- `文案`: keep the OCR/口播 text as the main evidence. Collapse noisy line breaks, remove obvious brand boilerplate OCR noise, but do not rewrite the user's actual copy.
- `用户视角`: write from the viewer's mental reaction, usually one short sentence. Good examples: `看到大肚腩会联想到自己身材`, `了解到产品卖点，觉得能解决痛点，对产品产生认可`, `刚好有活动，容易产生购买意愿`, `疑问增加好奇感，想继续看答案`.

Precision is more important than filling every shot. Leave cells blank when the shot is only a transition, repeated subtitle frame, short connector word, or the visual/copy role is not clear enough. This is especially true for `文案框架` and `用户视角`; these rows should mark key thinking nodes rather than describe every frame.
When the same cleaned copy repeats across adjacent split frames, write the planning judgment only on the first occurrence and leave the following repeated frames blank unless their visual state clearly changes.

Common mapping rules:

- Pain point visuals map to `痛点画面` / `痛点警示开篇` / viewer self-association.
- Product detail visuals map to `产品卖点展示` / `产品核心卖点` / product recognition.
- Source, factory, export, material, and professional claims map to trust-building language.
- Offer, welfare, price, stock, and buy-now copy maps to activity/closing conversion language.
- Empty subtitle shots should still be kept, using `画面承接` or visual-action placeholders.
- Fixed overlay compliance text such as `剧情演绎`, `无不良引导`, or `注意甄别` should not be treated as every shot's core copy. Strip it before judging the shot role, unless the user is explicitly analyzing compliance screens.
- Remove OCR residue such as random Latin model codes, duplicated brand boilerplate, and fixed overlay fragments before writing `文案`. Preserve real spoken product names such as `Ufeel` when they are part of the copy.

## Latest Learned Product Rules

When the user provides the transcript manually, use it as the primary `文案` source and align it to the nearest meaningful shot. Do not force OCR text over the user-provided copy.

For women's underwear videos, write the product category as `女士内裤` when the brand/product needs clarification. Avoid generic wording that makes the product sound like ordinary underwear when the visual proof is about high-waist, no-mark, safety-shorts, tummy-control, or bottom-gusset details.

Keep `视频结构（画面）`, `文案框架`, `文案`, and `用户视角` precise and sparse:

- Leave nonessential shots blank when they are only transition frames or repeated visuals.
- If the shot-cutting workflow drops evidence frames as nonessential, do not recreate them as Excel columns.
- Preserve rapid product display sequences when the frames show different product states or proof points. Write them as `快速产品展示`, `快速产品细节`, `快速上身展示`, or `快速产品上身展示`.
- For rapid product display, use compact frameworks such as `三合一卖点展示`, `隐形无痕卖点`, `穿搭场景验证`, and `产品给到解决方案`.
- For women's underwear user perspectives, describe the concrete viewer concern: visible panty line, thin/white clothing, gym leggings, skirt safety, lower-body comfort, bottom-gusset rubbing, stock-up trust, or not looking like ordinary underwear.

For bra / bralette / lifting-bra videos, preserve visual proof rows when the shot shows a distinct product claim. This does not mean bras uniquely require rapid proof frames; underwear videos also need rapid proof frames when adjacent frames show different product states, wearing proof, structure proof, or styling proof. Useful `视频结构（画面）` labels include `提拉内衣上身`, `法式三角杯细节`, `固定杯垫证明`, `深V美背展示`, `交叉肩带展示`, `无钢圈舒适证明`, `软支撑路径`, `副乳收拢验证`, and `快速穿搭参考单帧`. In `用户视角`, focus on the buyer's concrete concern: whether it显瘦, whether the cup pad runs after washing, whether it prevents凸点, whether it collects side breast, whether straps work with露背/吊带 clothes, and whether wireless support is comfortable.

When an intimate-apparel video is re-cut with extra detail recall, do not force every added detail frame to repeat the full transcript. Keep `文案` on the first shot of the relevant spoken segment, and use the extra columns mainly as visual proof with precise `视频结构（画面）` labels. When the user says `ModelShot_xxx` is duplicated, interpret it as the output Excel/model column id, not the raw evidence candidate id.

For the final 5.8 有棵树 bra calibration, use the `reference_optimized` report generated from `videos/test/imgs文胸有棵树` when available. The expected workbook is about `31` shot columns, still labeled horizontally as `ModelShot_001...ModelShot_031`; rapid single-frame proof columns around the 19-20s product/styling switch should remain separate.

For the 5.8 都市丽人 calibration, adjacent Excel `ModelShot` columns with similar visuals and the same bottom subtitle sentence should be merged into one workbook column unless there is a distinct product/proof state. If a user names a raw file like `Shot_009_000052.jpg`, recover that raw evidence candidate separately and then re-number the workbook columns as fresh `ModelShot_001...`.

For聚拢文胸 videos such as嫦香诗, classify copy nodes precisely around `聚拢胸型改善`, `旧内衣换新痛点`, `高定无痕面料`, `双C位软支撑`, `无钢圈舒适证明`, `品牌活动信任`, and `活动转化收口`. Bottom white subtitles remain the only copy source unless the user provides a transcript; product/package text inside the picture should be ignored.

For嫦香诗-style rapid proof frames, keep columns when the same model scene shows changed display text or when the same product appears in different color attributes. These frames may have little or repeated spoken subtitle text, so use `视频结构（画面）` to mark the visual proof rather than dropping the column as empty copy.

For the 5.10 嫦香诗 reference calibration, use `reference_optimized` with `--disable-same-subtitle-merge`; the expected workbook has `62` horizontal shot columns and `62` embedded images. The reference set corrected representative-frame choice as much as it added missing frames, so do not compare only by old `ModelShot` numbers. Fill added columns sparsely but accurately: `开场舒适痛点`, `快速单帧证明`, `上身效果对比证明`, `颜色/属性展示`, `聚拢结构证明`, `无痕/支撑验证`, and `活动转化收口` are preferred concise `视频结构（画面）` labels when they match the shot.

For shapewear / 塑身内衣 videos such as 美嘉挺, classify copy and visual rows around `塑身内衣产品露出`, `收腹提臀证明`, `上身塑形对比`, `腰腹/臀部支撑`, `无痕外穿证明`, `面料舒适证明`, and `活动转化收口`. The 5.9 美嘉挺 reference-calibrated workbook should use `reference_optimized` with `--disable-same-subtitle-merge` and preserve `46` horizontal shot columns. Fill long narration sparsely; repeated model-wearing columns do not need repeated framework/viewer text unless the visual proof changes.

For 婷美 / 美形服饰 / 收腹内裤 videos, avoid generic `女士内裤产品露出` labels when the claim is body-shaping. Prefer `塑身/收腹内裤产品露出`, `收腹提臀证明`, `上身塑形对比`, `无痕穿搭验证`, and `面料舒适证明` according to the visible proof and bottom white subtitle.

If the shot-cutting step has a user-calibrated `model_calibrated/optimized_shot_report.json`, generate the workbook with `--report-mode calibrated`. When the user explicitly names raw missing shots, disable same-subtitle merging so recovered proof frames stay visible as separate columns. In the 5.11 婷美 calibration, the recovered raw candidates appear in Excel as `ModelShot_010`, `ModelShot_013`, `ModelShot_016`, `ModelShot_026`, and `ModelShot_040`; raw `Shot_068` was already retained as `ModelShot_022`.

For 出彩日记 / 云感冰丝收腹裤 / 空姐身材 hook videos, use `reference_optimized` with `--disable-same-subtitle-merge` when a clean reference folder is provided. The 5.14 reference-calibrated workbook should preserve `71` horizontal columns and embedded images. Many added columns are visual proof under repeated or sparse subtitles, so fill `文案` only from bottom white OCR and use compact visual labels such as `空姐身材钩子`, `塑身/收腹内裤产品露出`, `云感冰丝面料证明`, `收腹无痕证明`, `薄衣穿搭验证`, `快速单帧证明`, and `活动转化收口`.

Recent calibration example: if evidence 15/16 are nonessential transition shots, remove them; if shots 32-35 are a fast product display sequence, keep them and fill the key rows because they communicate product proof.

For 5.20-style product口播 / product混剪 / KOC口播 / 520 activity promotion videos:

- When the user asks for subtitle-picture alignment, always run the unified builder with `--report-mode model --disable-same-subtitle-merge` unless a calibrated/reference report is explicitly available.
- Treat bottom white subtitles as the only `文案` source. Ignore product/package/sale-card text inside the picture, even when those visual cards are important evidence frames.
- Keep one workbook column per final shot. It is normal for some columns to have blank `文案` when the shot has no bottom subtitle or the subtitle is between OCR samples.
- Activity and price hooks should be labeled sparsely but clearly: use compact row-4/row-5 ideas such as `活动钩子`, `520促销开场`, `价格利益点`, `限时活动转化`, `产品口播承接`, `产品证明`, `快速混剪证明`, and `收口转化`.
- For product口播, fill planning rows mainly on meaningful nodes: opening activity claim, problem/pain statement, product reveal, product detail proof, wearing/no-mark/收腹 proof, package or quantity trust, and final offer. Leave repeated presenter continuation columns blank except for the OCR `文案`.
- For product混剪, do not treat fast visual columns as filler. If the shot shows a new wearing state, product angle, color, package, no-mark/safety/收腹 proof, or use scenario, mark row 4 even when the same subtitle continues.
- Expect OCR noise in sale subtitles, such as a digit or short character being misread in `一折来了`-style lines. Preserve the OCR as evidence unless the correction is obvious from the same shot; do not rewrite product text from the image into `文案`.
- Validation for this subtype: data columns must equal final report shots exactly, embedded images must equal data columns, and early activity-hook columns should be spot-checked because repeated sale subtitles are where accidental merging or subtitle carryover most often happens.

## Validation

After export, validate every workbook:

- A1:A10 exactly match the required row labels.
- The workbook has 10 rows in the used planning area.
- B1 contains the provided video link, or is blank when no link was provided.
- The number of data columns equals the number of shots for that video.
- The number of embedded images equals the number of shots when thumbnails exist.
- If the user requested subtitle-picture alignment, the number of data columns must equal the final shot report count exactly. If it is lower, same-subtitle merging likely happened; regenerate with `--disable-same-subtitle-merge`.
- For alignment-sensitive outputs, spot-check early columns and any fast-cut clusters: each column's `时间`, embedded image, and `文案` must come from the same shot interval. Do not accept a workbook where the subtitle line visibly belongs to the previous or next image.
- Long Chinese text wraps and row heights are large enough to display normally.

Use `openpyxl` for structural checks when available.

## Script Reference

- `scripts/extract_shot_text_ocr.py`: reads shot reports and writes OCR CSV/JSON.
- `scripts/prepare_ocr_thumbnails.py`: creates fixed-size thumbnails and adds `缩略图` paths to OCR JSON.
- `scripts/build_individual_shot_text_excels.mjs`: builds horizontal, image-embedded Excel workbooks.
