---
name: shot-cutting-agent
description: Split short videos into action-triggered shot units using learned visual cutting rules. Use when Codex needs to process product, model, hand-action, rapid-display, or short-video ad footage into evidence frames and shot reports for later Excel拆解, especially when avoiding equal-time cutting and matching human reference shot choices.
---

# Shot Cutting Agent

## Overview

Use this skill to split a short video into meaningful visual shots. The cut logic is action-triggered, not time-triggered: keep frames where the picture state, product state, model pose, hand position, or sales proof changes in a way that matters for later拆解.

For the full learned model record from videos 1-11 and later user feedback, read `references/learned-model-profile.md` when tuning thresholds, judging whether a result is over/under-cut, or updating the model rules.

## Workflow

Run the bundled script from the video project root. Resolve the installed skill path from `CODEX_HOME`, falling back to the current user's `.codex` directory:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
python (Join-Path $codexHome "skills\shot-cutting-agent\scripts\shot_cutting_agent.py") --video-file "<video.mp4>" --output-dir "<output_dir>"
```

Outputs include:

```text
<output_dir>/<video_stem>/shot_report.json
<output_dir>/<video_stem>/model_optimized/model_optimized_shot_report.json
<output_dir>/<video_stem>/model_optimized/evidence/*.jpg
```

Use `model_optimized_shot_report.json` for normal downstream Excel拆解 unless a reference image folder is provided.

Speed rule: for repeated work on the same video, reuse existing reports. The bundled `scripts/shot_cutting_agent.py` skips re-cutting automatically when `shot_report.json`, `model_optimized_shot_report.json`, evidence frames, and the saved model profile are still valid and newer than the source video. Use `--force` only when the cutting model/profile changed or the user explicitly asks to re-run visual segmentation from scratch.

## Core Rules

- Never cut by equal time intervals.
- Treat any material visual change as a candidate: hand movement starts/stops, product unfolds, package opens, model pose changes, screen composition changes, close-up detail appears, or dialogue scene switches.
- Preserve fast-paced product display sequences when each frame shows a new product angle, detail, wearing state, package state, color, or proof point.
- Suppress dead-air and redundant frames after an action completes.
- Do not keep ultra-short or accidental micro-frames when they add no new visual information.
- Prefer the stable display frame after an action instead of only the motion-trigger instant.
- Preserve stable product states shortly before hard visual switches so the next portrait/scene does not swallow the prior product display.
- In the first `15s`, protect distinct hook-state frames when the subtitle line continues but the visual state changes clearly. Examples include wearing proof changing to product detail, product detail changing to model upper-body display, celebrity/口播 scene entering, or a hand-held product state changing angle.

- In dense mid-video product proof blocks, keep package-front, bottom-gusset, fabric-structure, and material-proof frames even when they sit between two already selected high-motion cuts.
- When a user provides a calibrated reference image folder, trust the reference image density over the model target count. For the 5.24 Ufeel/brand summer underwear case, the model output had `101` shots but the reference folder kept `121` visual states. Those extra frames are mostly product wearing/proof states, quick mannequin/on-body changes, and single-word transition frames; keep them as visual evidence rather than compressing back to model density.

## Learned Keep Rules

Keep these even if they are fast:

- Product unboxing, unfolding, lifting, stretching, pinching, or rotating.
- Rapid product display sequences that show different angles or details across adjacent frames.
- Close-ups of key sellable parts, such as waistband, bottom gusset, crotch lining, seams, material thickness, stretch, color, or packaging.
- Wearing verification shots: tight pants, white/thin/transparent clothing, gym leggings, mirror checks, side/back views, or no-mark/no-edge proof.
- Dialogue or conflict scenes that create a hook and then reveal product proof.
- Opening hook sequences where one white subtitle sentence spans multiple visual shots. Keep multiple frames only when each frame has a different visual job, not when it is just the same portrait or product drifting slightly.

For women's underwear videos, the sales product is `女士内裤`; prioritize shots showing:

- Product body, packaging, and multi-pack/stock-up quantity.
- High waist, tummy-control, safety-shorts, three-in-one structure, invisible/no-mark edge, powder/skin-tone color, milk-skin texture, or soft fabric.
- Bottom gusset length and comfort proof. Long-gusset comparison shots should be kept.
- Scene validation: summer thin pants, white/transparent clothes, gym leggings, skirt safety, and visible panty-line embarrassment.
- Mid-sequence trust/proof states: brand package front, independent sealed package, unfolded lace/fabric front, bottom-gusset close-up, and the last product detail immediately before a model/portrait scene switch.

## Learned Drop Rules

Drop or suppress these unless the user explicitly asks to keep every split:

- Evidence frames that are only accidental transition slivers or blurred micro-cuts.
- Repeated subtitle frames with no new picture state.
- Adjacent portrait/model frames with only tiny pose drift and no new action, especially when the shot is not a fast product proof sequence.
- Ultra-short flashes that do not reveal a new product angle, product state, or story beat.

Recent calibration example: in a women's underwear test video, evidence frames 15 and 16 were nonessential and should be removed; a later rapid product display sequence around shots 32-35 was important and should be kept because it showed fast product proof.

## Learned Density Modes

Use these as model guidance, not rigid user-visible promises:

- Normal learned target density is about `0.52 shots/sec`, with high-recall candidates compressed by about `3.85x`.
- For short low-candidate videos under `70s` and below `2.2 candidates/sec`, protect product state frames with a higher target density around `0.72 shots/sec`.
- For long sparse videos at `>=100s` and below `1.85 candidates/sec`, use long-sparse suppression with target density around `0.42 shots/sec`.
- For `>=130s` videos near `1.85-1.93 candidates/sec`, consider the extended long-sparse trigger.
- For continuous portrait scenes, suppress near-duplicate portrait frames unless posture, scene, product, or action changes clearly.

## Reference-State Recovery

When a reference folder is available and the calibrated result has many more frames than the model result, first decide whether this is a detection miss or an optimization miss:

- If reference recall is high in raw candidates, such as almost all reference frames within `24-45` frames of a raw candidate, do not raise the detector sensitivity. The issue is redundancy suppression merging meaningful states.
- For long product videos around `>=130s` where raw candidate density sits just above the long-sparse trigger, about `1.93-2.08 candidates/sec`, use borderline reference-state protection instead of normal compression.
- In this mode, protect adjacent states only when the image adds new拆解 value: product angle/detail, body-wearing proof, before/after body state, package quantity, material stretch/透薄/无痕 proof, or a stable state just before/after a hard switch.
- Do not protect frames merely because subtitles changed, the same portrait continues, or a hand/model has tiny drift with no new sellable visual information.
- A good reference-guided target for this kind of long product proof video can be around `0.60-0.70 shots/sec`, but the final count must still be judged by visual value. More shots is not automatically better.

## Opening Subtitle-State Guard

Use this rule for product ads whose first `15s` contain dense hook storytelling:

- A single bottom white subtitle sentence may continue across several visual shots. Do not merge these shots automatically if the picture state changes materially.
- Preserve separate opening frames for different visual jobs: body/wearing proof, fabric or lace close-up, model pose change, product hand-held display, package/box display, celebrity/口播 appearance, or clear scene switch.
- Still suppress repeated frames when the same person/product remains in the same composition and only the mouth, hand, or subtitle line moves slightly.
- Suppress opening near-duplicates even if they were protected by the opening guard. Use a tight duplicate window around `520ms`: very close same-composition frames should collapse, but nearby frames beyond that window can both be kept when their visual job differs.
- In the lace underwear calibration, `001/002`, `004/005`, and `006/007`-style same-composition repeats should not both be retained. But reference `005/006` and `010/011` should be retained because they are similar in color/layout yet describe different states: side/back wearing proof vs front lace proof, and front model/product state vs back lace/waistband proof.
- This guard should improve representative-frame choice, not inflate the whole video. Later redundant frames should still be compressed.

## Product Proof Cluster Guard

Use this rule when a women's underwear video enters a dense product-proof block after the opening hook:

- If two selected shots enclose several fast product candidates, preserve one middle proof frame when it shows a different sales claim, such as package-front trust, gusset/lining design, fabric detail, lace structure, stretch, thinness, or no-mark proof.
- Do not let a later model/portrait scene switch swallow the last product-detail frame before it. The lace underwear calibration showed reference `046` should be kept because it was a bottom-gusset/fabric proof immediately before the model scene.
- Do not let a multi-product display swallow the brand/package-front trust frame. The same calibration showed reference `037` should be kept because it was a package-front frame distinct from the preceding multi-color box display and following unfolded garment.
- For 5.28 brand lace/pastel underwear videos, the clean reference folder `imgs5.28-video_品牌蕾丝质感内裤` has `132` meaningful visual states while the automatic model kept `110`. The missing `22` states were almost all in the first `60s` (`55` model states vs `77` reference states), so treat this as early-section optimization suppression rather than a whole-video density problem.
- In the first minute of lace/pastel underwear videos, protect quick proof states when they change the visual job: opening wearing proof, package or tag trust frame, pastel color/set display, lace/fabric close-up, gusset/detail proof, on-body fit comparison, and same-scene product state changes. These states can share the same subtitle and still need separate evidence frames.
- Prefer the reference's stable proof frame over the model's nearby motion/transition frame when both map to the same micro-action. Do not simply add every nearby raw candidate; replace blurry or in-between representatives with the clearer reference-matched state.
- Keep this guard budgeted and narrow: it is for missing product proof states, not for retaining every hand movement in a display cluster.

## Bra / Intimate Apparel Detail Recall

Use this rule for short intimate-apparel product videos, including women's underwear, bra, bralette, lifting bra, safety-shorts underwear, and similar close-to-body garments:

- Do not frame the logic as underwear-only or bra-only. Rapid proof frames matter in both categories when each frame shows a different product state, wearing proof, structure proof, or styling proof.
- Treat user feedback like `ModelShot_004/ModelShot_005` as output-model numbering from the Excel/report, not raw evidence numbering. Use raw `Shot_xxx` only for tracing the source candidate behind an output column.
- Keep structural proof frames: cup shape, fixed cup pad, anti-nipple proof, side support, underarm/side-breast collection, shoulder strap path, deep-V back, cross-back/normal-wear conversion, wireless design, fabric stretch, gusset/crotch lining, waistband, no-mark edge, and close-up seams/edges.
- Keep model-wearing proof frames when the model pose demonstrates a product claim. Portrait/model frames can be product evidence, not dead-air talking-head frames.
- Preserve rapid single-frame styling or product references when they are genuinely different. In the 5.8 intimate-apparel calibration, output frames corresponding to fast styling references should not be collapsed into one shot.
- Still drop adjacent output ModelShot pairs that perform the same visual job. If two adjacent ModelShot columns show the same composition/product state with only hand drift, pose drift, or a slightly later version of the same display, keep the cleaner/more stable proof frame and remove the duplicate.
- For very-near duplicates, prefer the post-action stable proof frame over the earlier motion frame unless the earlier frame is the only clear product state.
- If two adjacent Excel `ModelShot_xxx` columns are visually similar and carry the same bottom subtitle sentence, treat them as one shot unless the second frame reveals a new product state. This applies especially to opening hook frames where the subtitle line continues through a small motion drift.
- If user names a raw evidence file such as `Shot_009_000052.jpg`, trace it back to the raw candidate `Shot_009` and recover it if it represents a missing hook/proof state. Do not confuse it with the current Excel `ModelShot_009`.
- Protect fast single-frame proof candidates even inside the same model/product scene when the display text changes or when the same product is shown in different color attributes. In the 5.9 聚拢文胸 calibration, raw `Shot_013`, `Shot_036`, `Shot_045`, `Shot_048`, `Shot_050`, `Shot_052`, `Shot_059`, `Shot_060`, `Shot_078`, `Shot_123`, `Shot_125`, and `Shot_149` were recovered for this reason.
- Preserve comparison/verification frames that appear immediately after an on-body effect shot. These are fast proof frames, not ordinary adjacent repeats. Examples: after showing upper-body wearing effect, keep the next contrast frame that proves shape change, no-mark effect, color/styling difference, before/after body line, or product claim validation.
- For reference-image recalibration, trust a clean human reference set when every reference image matches the video with no weak matches and all baselines are within about `24` frames of raw candidates. In the 5.10 都市丽人 bra calibration, `50` reference images became the new baseline density; do not re-merge these reference states just because the bottom subtitle repeats.
- In the 5.10 Changxiangshi bra reference calibration, `62` clean reference states became the baseline. The old calibrated output had `51` states, but the new reference output was not simply old +11: it kept only `25` old source candidates, added `37` reference-preferred states, and dropped `26` old motion/transition representatives. Treat this as representative-frame correction and missed proof-state recovery, not as blind density inflation.
- For Changxiangshi-style 聚拢文胸 videos, pay extra attention to the first `15s` hook and the `24-45s` proof block. Keep distinct states for same-model scenes when display text changes, when the same bra appears in different colors/attributes, when a detail shot shifts from upper-body effect to comparison proof, or when a stable post-action frame is clearer than the earlier motion frame.
- For long shapewear / 塑身内衣 videos, do not inherit Changxiangshi's high-density fast-proof shape. In the 5.9 美嘉挺 calibration, a `160.43s` video had `262` raw candidates, `61` automatic model shots, and only `46` clean reference states. Preserve body-shape proof, waist/abdomen/hip support, before/after or on-body comparison, no-mark/edge/fabric proof, and first-15s hook states; compress long repeated narration, similar model-wearing frames, and transition-only states.
- If the automatic model has more shots than a clean reference set in a long shapewear video, first strengthen duplicate suppression in repeated wearing/model sections. Do not reduce raw candidate recall, because reference states can still be fully covered within `24` frames.
- For Tingmei / 美形服饰 / 收腹内裤 videos, protect short raw candidates that show product-proof state changes even if they look like brief flashes. In the 5.11 婷美 calibration, raw `Shot_031`, `Shot_037`, `Shot_058`, `Shot_080`, and `Shot_151` were recovered, while `Shot_068` was already present. These represent missing收腹/塑形 proof, product state, or quick transition evidence rather than ordinary dead-air.
- When the user names raw `Shot_xxx` ids as missing, create or update `model_calibrated/optimized_shot_report.json`, add only missing source candidates, keep already-present ids without duplication, sort by start time, and regenerate Excel from `--report-mode calibrated` with same-subtitle merging disabled.
- For 出彩日记 / 云感冰丝收腹裤 / flight-attendant-hook underwear videos, clean reference images may require higher visual-proof density than the default model. In the 5.14 calibration, `71` reference states across `99.03s` replaced the automatic `53` shots; all reference states matched within `24` frames and there were no weak matches. The issue was optimization suppression, not detector recall.
- In this subtype, preserve same-subtitle visual states when they show new hook images, product reveal, fabric/ice-silk proof,收腹 or no-mark wearing proof, thin-clothes/flight-attendant styling validation, color/state changes, or fast sales-proof flashes. Do not merge human-reference states just because the bottom subtitle line is still continuing.
- Final 5.8 reference calibration: the human folder `imgs文胸有棵树` contains `31` meaningful states, so this video should stay near the first-generation count (`30-35`) rather than the over-recalled `59`. Keep the rapid single-frame switch cluster around source `Shot_040-043`, but budget other bridge/detail recovery tightly.
- When a reference folder is provided, prefer `reference_optimized/optimized_shot_report.json` for downstream Excel. Keep Excel-facing shot labels as `ModelShot_001...` even if the internal reference report uses `OptShot_xxx`.

## 5.20 Koubo / Mixcut / Promo Pattern

Use this rule for 8020/Ufeel-style product口播, product混剪, KOC口播, and 520 activity promotion videos when no reference image folder is provided:

- Use `model_optimized/model_optimized_shot_report.json` as the normal downstream report, then let the Excel step disable same-subtitle merging if subtitle-picture alignment is requested.
- Preserve opening promotion hooks as separate shots when the visual state changes: price/discount callout, dialogue reaction, product reveal, presenter switch, package/product display, or fast activity graphic. Do not merge these only because the bottom subtitle is one continuing sale sentence.
- In product口播, keep useful speaker/product state changes: different person or scene, product held up, package shown, fabric/detail close-up, on-body proof, activity price/stock cue, and final conversion frame.
- In product混剪, use a slightly higher recall posture than pure口播. Fast cuts can each be a valid proof shot when they show a new wearing state, color/product angle, no-mark/safety/收腹 proof, package state, or usage scene.
- Still suppress repeated talking-head frames: same presenter, same composition, same product state, and only mouth movement or subtitle continuation should collapse to one stable representative.
- For 520/618-style activity videos, treat offer information as a visual job only when the picture changes meaningfully. Keep the first clear activity card or presenter claim, but do not keep every repeated price subtitle frame.
- Recent 5.20 batch calibration landed in a practical range of about `0.42-0.82 shots/sec`: pure口播/活动 videos often stayed around `43-58` shots for `68-142s`; denser product混剪 or long promo videos can reach `54-80` shots when many visual states are distinct. Judge by visual proof value, not by matching these counts mechanically.

## Output Use

For each final shot, preserve:

- `shot_id`
- start/end time and frame
- action label
- confidence/model score
- `evidence_frame` path

These fields are consumed by the Excel拆解 workflow, where each retained shot becomes a horizontal column with an embedded image.
