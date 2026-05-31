# Shot-Cutting Learned Model Profile

This reference records the core learned rules from `E:\USE\codexhome\fenge\SHOT_CUTTING_AGENT_MODEL.md` and later user calibration.

## Model Version

- Version: `shot_cutting_agent_v2_23_chucairiji_reference_density`
- Training samples: `1.mp4/imgs` through `11.mp4/imgs11`
- Core principle: high-recall candidate detection first, learned redundancy suppression second.
- Default final output without reference images: `model_optimized/model_optimized_shot_report.json`
- Final calibrated output with reference images: `reference_optimized/optimized_shot_report.json`

## Non-Negotiable Cutting Logic

- Do not split by equal seconds.
- Split only on substantial picture/action changes.
- Keep the video start establishing shot.
- Prefer the stable display frame after an action, not only the exact motion-trigger instant.
- Protect the pre-cut stable product state within about `550ms` before a hard visual switch.
- If cloth, packaging, or product moves from crumpled/closed to unfolded/open, preserve clear intermediate or final state frames when they show new information.

## Main Parameters

- Learned target density: about `0.52 shots/sec`
- Learned over-split compression ratio: `3.85x`
- Minimum representative gap: `720ms`
- Preferred representative gap: `1350ms`
- Representative frame offset: about `35%` into the shot, max `500ms`
- Recall tolerance for reference comparison: `24 frames`
- Product proof cluster guard: protect dense mid-sequence package/gusset/fabric proof states in a narrow learned block when at least `2` fast inner candidates sit between selected cuts.
- Medium short intimate-apparel detail mode: for 70-90s sparse product videos, keep the final result close to human reference density, while preserving rapid single-frame proof clusters when adjacent frames carry different product/styling evidence.

## Low Candidate Density Mode

Use for short videos that are visually sparse but contain meaningful product states:

- Trigger only when duration `<70s` and raw candidate density `<2.2 candidates/sec`
- Target density becomes `0.72 shots/sec`
- Over-split ratio becomes `2.65x`
- This protects short dense product-display samples such as video 7, where key frames like `001`, `011`, and `016-019` must not be merged away.

## Portrait Redundancy Suppression

- For continuous portrait talking scenes, keep multiple frames only when there is large action, a hard switch, or a clearly different posture/state.
- Within `2500ms`, repeated face/person shots usually keep only the first representative frame.
- Within `9000ms`, if portrait visual distance is below `0.24`, treat it as near-duplicate unless product or scene state clearly changes.
- This learned rule comes from video 8: continuous portrait screenshots need multiple frames only on large movement; reference `003` had only one image.

## Long Sparse Video Mode

Use when long videos are under-candidate but still have meaningful transitions:

- First trigger: duration `>=100s` and candidate density `<1.85/sec`
- Second trigger: duration `>=130s` and candidate density `<1.93/sec`
- Target density becomes `0.42 shots/sec`
- Over-split ratio becomes `4.4x`
- Calibrated from videos 10 and 11; it also fixed video 6 from `65` to `53`, matching the reference count.

## Borderline Reference-State Guard

Use this guard when a long product video has meaningful reference states but the automatic model returns too few shots:

- Trigger shape: duration `>=130s` and raw candidate density about `1.93-2.08/sec`.
- Target shape: around `0.62 shots/sec` and over-split ratio around `3.05x`.
- Purpose: loosen the final optimization layer, not the candidate detector.
- Keep adjacent states only if they add new拆解 evidence: product angle/detail, wearing verification, before/after body proof, package/quantity proof, material stretch,透薄,无痕, gusset/edge/seam detail, or a stable display state before/after a hard switch.
- Still drop repeated portrait frames, subtitle-only changes, blurred transition slivers, and hand/model micro-drift with no new product or story information.

Calibration note from `videos/test/2.mp4` against `videos/imgs`:

- Raw candidates: `318`
- Automatic model: `81`
- Reference optimized: `108`
- Delta: `+27` reference states
- Duration: `163.43s`
- Raw candidate density: about `1.95/sec`, just above the old extended long-sparse threshold `1.93/sec`
- Automatic density: about `0.50/sec`; reference density: about `0.66/sec`
- Candidate recall was high: `107/108` reference states within `24` frames and `108/108` within `45` frames.
- Conclusion: these frames were not missed by visual scanning. They were suppressed later because normal temporal NMS, minimum representative gaps, pre-cut limits, and portrait/neighbor duplicate suppression compressed adjacent product or wearing-proof states into one representative frame.
- Practical rule: when reference recovery adds many useful states in a long product-proof video, audit suppression clusters before tuning. Recover product/proof states, but do not turn the model into "more frames is better."

## Opening Subtitle-State Guard

Use this guard for the first `15s` when a product ad uses fast visual hooks while the bottom white subtitle sentence is still continuing:

- Window: first `15000ms`.
- Minimum protected opening-state gap: about `520ms`.
- Opening guard budget: about `20%` of the learned target count, so it changes which states are selected rather than blindly increasing total shots.
- Opening near-duplicate brake: within about `520ms`, if adjacent opening representatives have visual match distance below about `0.30`, treat them as too similar and keep only one.
- Keep if the subtitle line is unchanged or incomplete but the visual job changes, such as wearing proof -> lace/fabric close-up -> full-body model pose -> celebrity/口播 -> hand-held product or package state.
- Drop if it is the same portrait/product composition with only mouth movement, tiny hand drift, or repeated subtitle text.

Calibration note from `videos/test/柔软亲肤的蕾丝内裤好漂亮， 精选优质面料柔软舒适亲肤透气#仙女蕾丝.mp4` against `videos/test/ims柔软亲肤`:

- Raw candidates: `355`
- Old automatic model: `70`
- Reference optimized: `60`
- After opening guard: `75`
- Duration: `160.8s`, fps `60`
- Reference recall in raw candidates was high: `59/60` within `24` frames and `60/60` within `45` frames.
- The old model was not globally under-cut, but it missed or mis-represented early hook states. In the first `15s`, weakly covered reference states included `005.png` at `3.33s`, `006.png` at `4.23s`, `007.png` at `5.13s`, `008.png` at `6.52s`, `010.png` at `7.60s`, and `014.png` at `9.70s`.
- These frames mattered because the same/unfinished white subtitle spanned several different visual states: lace wearing proof, full-body model state, celebrity/口播 entrance, product hand-held display, and package/display state.
- After v2.13, the first `15s` alignment improved substantially, but it over-kept near-duplicates in the opening. User feedback: overly similar frames should not be retained, with examples like `001/002`, `004/005`, and `006/007`.
- v2.14 added a `900ms` opening near-duplicate brake. It removed repeated opening frames, but user calibration showed it was too broad for lace underwear: reference `005/006` and `010/011` looked visually close yet carried different sellable states.
- v2.15 tightens the brake to about `520ms`. Keep `001/002`, `004/005`, and `006/007`-style same-composition repeats collapsed, but preserve `005/006` when the shot changes from side/back wearing proof to front lace proof, and preserve `010/011` when the shot changes from front model/product state to back lace/waistband proof.

## Product Proof Cluster Guard

Use this guard for dense product-proof blocks after the opening hook, especially in women's underwear videos where packaging and gusset/fabric proof are core sales evidence:

- Trigger on a narrow dense proof block rather than the whole video. This prevents early ordinary transitions from consuming the proof budget.
- Keep a middle proof frame when two selected shots enclose multiple fast candidates and the inner frame adds a distinct claim: brand package front, independent sealed package, bottom-gusset/lining design, fabric/lace structure, stretch, thinness, or no-mark proof.
- Calibration from the lace underwear video: reference `037.png` at `00:00:30.333` was missed because the model jumped from multi-color box display to unfolded garment. It should be preserved as package-front trust proof.
- Calibration from the same video: reference `046.png` at `00:00:35.033` was missed because the model jumped from fabric handling to the model scene. It should be preserved as the last bottom-gusset/fabric proof before the portrait switch.
- After v2.16, automatic model count for this video became `73`, with reference `037` covered within `8` frames and reference `046` covered within `6` frames. The goal is targeted proof recovery, not increasing all shots.

## Neighbor Similarity Suppression

## Intimate Apparel Calibration

Use this calibration for women's underwear, bra, bralette, lifting bra, and other intimate-apparel product videos:

- The 5.8 bra sample initially returned only `30` model shots from `117` raw candidates across `73s`, which was too sparse for a product whose claims rely on cup shape, straps, deep-V back, support path, and wearing proof.
- v2.17 added a medium short product mode for videos around `70-90s` with candidate density around `1.2-2.0/sec`. It raised recall for structure, wearing proof, and rapid styling/product references without changing the no-equal-time-cut principle.
- User correction after v2.17: rapid single-frame proof is not bra-only; it also matters in underwear videos. The model must not record separate underwear vs bra logic as if only one category needs fast proof frames.
- Treat feedback such as `ModelShot_004/ModelShot_005` as output Excel/model numbering. Do not confuse it with raw `evidence/Shot_xxx` numbering. Raw candidate ids are only for tracing.
- v2.18 balances recall with adjacent duplicate cleanup. Preserve protected rapid/product proof frames across intimate-apparel categories, but remove adjacent output ModelShot pairs that perform the same visual job.
- If two very-near frames are almost identical, prefer the post-action stable proof frame over the earlier motion frame unless the earlier frame is the only clear state.
- The 5.8 calibration identified many adjacent output ModelShot pairs as duplicates after the recall boost. The lesson is not to reduce proof recall globally, but to add an output-stage adjacent task duplicate pass.
- Final 5.8 reference calibration against `videos/test/imgs文胸有棵树`: the human reference has `31` states. A good automatic result for this sample is close to the first-generation count (`30-35`), not the v2.18 recall-expanded `59`. However, the rapid proof cluster around raw `Shot_040`, `Shot_041`, `Shot_042`, and `Shot_043` must stay split because it is a fast single-frame product/styling switch sequence.
- v2.19 lowers the medium-short intimate-apparel target density to about `0.42 shots/sec`, adds budgets for bridge/micro/pre-long detail recovery, and keeps reference-optimized output as the final when a reference folder exists. This prevents detail recovery from inflating ordinary repeated display frames.
- 5.8 都市丽人 calibration: Excel `ModelShot_001/002` and `ModelShot_008/009` were output-level duplicates because the pictures were similar and each pair carried one continuing bottom subtitle sentence. Merge these as one shot. The raw evidence `Shot_009_000052.jpg` was a separate missed hook/proof state and should be recovered as raw candidate `Shot_009`; remember that `ModelShot_xxx` and raw `Shot_xxx` are different numbering systems.
- 5.9 嫦香诗 聚拢文胸 calibration: Excel `ModelShot_002/003` was an output-level duplicate and should be merged. Raw evidence `Shot_013`, `Shot_036`, `Shot_045`, `Shot_048`, `Shot_050`, `Shot_052`, `Shot_059`, `Shot_060`, `Shot_078`, `Shot_123`, `Shot_125`, and `Shot_149` should be protected as rapid proof/display states. Many are same model scene but with changed display text, or same product with different color attributes; these are meaningful proof frames and should not be suppressed as ordinary duplicates.
- 5.10 都市丽人 bra reference calibration: folder `videos/test/imgs5.10+文胸+都市丽人经典官方+11名` contains `50` clean reference states. Reference matching had no weak matches, median distance about `0.10`, max distance about `0.153`, and `50/50` baselines within `24` frames of raw candidates. Use `reference_optimized` as the calibrated result and preserve all `50` states; Excel generation should disable same-subtitle merging for this reference-calibrated output.
- Difference learned from old 5.8 都市丽人 output vs 5.10 reference output: the old `model_calibrated` workbook had `48` columns and was created by merging repeated subtitle/model outputs plus manually adding one missing evidence frame. The new `reference_optimized` workbook has `50` columns, but it is not merely old +2. It replaces many source candidates: `21` new reference source ids are not in the old output, and `19` old model source ids are not in the reference output. Reason: reference images select the human-preferred stable state inside each micro-action cluster, while model calibration often selected an earlier/later motion frame in the same semantic beat. When a clean reference folder exists, use it to choose representative states and boundaries, not just to adjust count.
- Additional 5.10 都市丽人 lesson: the model often misses the comparison/verification frame immediately after an on-body effect shot. These frames prove the on-body claim: shape change, no-mark effect, styling/color contrast, body-line improvement, or before/after validation. Treat them as rapid proof frames and protect them, even if the same model scene or same subtitle continues.
- Practical rule from this comparison: if a reference set has high-quality full-frame matches, treat source-id differences as representative-frame correction unless the visual state is plainly duplicated. Do not force old `ModelShot_xxx` numbering or old manually patched source ids to remain stable across a new reference calibration.
- 5.10 嫦香诗 聚拢文胸 reference calibration: folder `videos/test/imgs5.10+文胸+嫦香诗官方+1名` contains `62` clean states. Raw candidates were `177`, old base model output `42`, old `model_calibrated` output `51`, and `reference_optimized` output `62`. Reference matching was strong: median distance about `0.094`, max distance about `0.191`, `60/62` baselines within `24` frames, and `62/62` within `45` frames. The detector had enough recall; the difference came from optimization and representative-frame choice.
- Difference learned from old 嫦香诗 calibrated output vs 5.10 reference output: only `25` source candidates overlap; `37` reference-preferred source ids are new and `26` old source ids are dropped. This means the reference did not simply add frames. It replaced many earlier/later motion choices with stable display frames and recovered proof states in the first `15s` hook, the `24-45s` fast proof block, color/attribute switches, changed display-text frames, and comparison frames immediately after on-body effect shots.
- Practical rule from 嫦香诗 5.10: for medium-short 聚拢/内衣 videos around `60-70s`, a reference-calibrated density near `0.93 shots/sec` can be correct when the human reference has many clean fast proof states. Do not copy that density blindly to other videos; require high-quality reference matches and clear visual jobs for the extra states.
- 5.9 美嘉挺塑身内衣 reference calibration: folder `videos/test/imgs5.9+塑身+美嘉挺内衣+1名` contains `46` clean states across a `160.43s` video. Raw candidates were `262`, base model output `61`, and `reference_optimized` output `46`. Reference recall was complete within `24` frames (`46/46`), with one weak visual match above `0.35` at reference `038`; use the reference result but audit weak matches visually when needed.
- Difference learned from 美嘉挺: this is the opposite of Changxiangshi's high-density fast-proof case. The model over-kept `34` states not in reference, mostly in the long middle/late narration where similar model-wearing or transition states repeat. The reference still recovered `19` states not in the base model, concentrated in the first `15s` hook, 31-32s detail/transition states, 44-51s proof states, and late structural proof transitions. For long shapewear/塑身内衣 videos, keep key body-shape proof, before/after or on-body comparison, waist/abdomen/hip support, fabric/edge/no-mark proof, and product reveal states, but compress repeated talking/model posture and repeated wearing states aggressively.
- Practical rule from 美嘉挺: long shapewear videos around `160s` may correctly land near `0.29 shots/sec` when the human reference is sparse and clean. Do not force intimate-apparel fast-proof density upward just because the category is close-to-body; distinguish fast proof clusters from long explanatory sections.
- 5.11 婷美美形服饰02 manual calibration: base model output was `38` shots from `161` raw candidates across `84.23s`. User identified raw `Shot_031`, `Shot_037`, `Shot_058`, `Shot_068`, `Shot_080`, and `Shot_151` as missing. `Shot_068` was already present; the other five were added to `model_calibrated`, giving `43` final shots. This shows that medium-length收腹/塑形内裤 videos can still lose brief proof states even when the overall density looks reasonable.
- Practical rule from 婷美: raw candidates around quick product state changes,收腹/塑形 proof, and short transition-proof frames should be recovered when specifically identified. Use calibrated output and disable same-subtitle merging for Excel so these proof states remain visible. Do not duplicate already-retained raw ids.
- 5.14 出彩日记优选 / 云感冰丝收腹裤 reference calibration: folder `videos/test/imgs5.14+内裤+出彩日记优选+1名` contains `71` clean states across a `99.03s` video. Raw candidates were `200`, automatic model output `53`, and `reference_optimized` output `71`. Reference matching was excellent: median distance about `0.072`, max distance about `0.144`, no weak matches, no duplicate matches, and `71/71` baselines within `24` frames. The detector had enough recall; suppression merged meaningful visual states.
- Difference learned from 出彩日记: only `31` source candidates overlapped between model and reference; `40` reference-preferred states were missing from the model and `22` model states were not in the reference. Missing states were not isolated to one area: first-15s hook states, 27-30s fast proof, 45-60s product/wearing proof, and the late activity/closing section all needed extra states. Same or continuing white subtitles can span several useful visual jobs.
- Practical rule from 出彩日记: for 90-100s underwear videos with a flight-attendant/body-shape hook and dense product proof, clean reference density around `0.72 shots/sec` can be correct. Preserve hook visuals, product reveal, ice-silk/fabric proof,收腹/no-mark proof, thin-clothes styling validation, color/state changes, and fast sales-proof flashes. Use `reference_optimized` and disable same-subtitle merge for Excel.

## Neighbor Similarity Suppression

- Enable in low-candidate and long-sparse modes.
- If adjacent representatives are within `2200ms` and visual match distance is below `0.22`, treat them as one repeated display action.
- Do not apply this to hard cuts, flash/freeze moments, or strong visual switches.
- Calibrated from video 9 and video 10 to reduce duplicate model results while preserving recall.

## Reference Calibration

When `--reference-img-dir` is provided:

- Match every valid reference image back to a full video frame.
- Exclude helper images whose names contain preview/order/contact/sheet/map/manifest-like words.
- Use `reference_optimized` as the final calibrated result.
- Check `model_vs_reference_summary.json` for recall and weak matches.
- Good automatic results are usually within `0.85x - 1.20x` of reference image count.

## Training Summary 1-11

| Sample | Raw candidates | Auto model | Reference calibrated | Auto - Reference |
| --- | ---: | ---: | ---: | ---: |
| 1 | 318 | 89 | 108 | -19 |
| 2 | 234 | 62 | 66 | -4 |
| 3 | 262 | 54 | 60 | -6 |
| 4 | 242 | 66 | 75 | -9 |
| 5 | 260 | 66 | 56 | +10 |
| 6 | 223 | 53 | 53 | 0 |
| 7 | 93 | 40 | 35 | +5 |
| 8 | 211 | 55 | 43 | +12 |
| 9 | 113 | 46 | 41 | +5 |
| 10 | 213 | 46 | 43 | +3 |
| 11 | 275 | 59 | 50 | +9 |

Totals: raw candidates `2444`, automatic model `636`, reference calibrated `630`, automatic/reference ratio about `1.047x`.

## Later User Calibration

Video 7:

- Frames `016`, `017`, `018`, and `019` were all unfolded display states and must not be merged into one crumpled or motion frame.
- Earlier missed frames like `01` and `011` were important state frames.

Portrait videos:

- Continuous portrait screenshots should not be repeated unless there is a large action or composition change.

Women's underwear test video:

- Product category is `女士内裤`.
- Evidence frames 15 and 16 were nonessential and should be removed.
- Shots 32-35 were a fast product display sequence and should be kept because they showed product proof.
- For this category, keep rapid product proof involving bottom gusset, invisible/no-mark edge, powder/skin-tone color, three-in-one safety-shorts/tummy-control structure, packaging, and wearing verification in white/thin clothes or gym leggings.

5.20 product口播 / 混剪 / 活动促销 batch:

- All outputs used `model_optimized` because no reference folders were provided, and Excel generation used `--disable-same-subtitle-merge` for subtitle-picture alignment.
- `5.20-video_夏天内裤怎么选`: `338` raw candidates, `75` model shots, `143.47s`, about `0.52 shots/sec`.
- `5.20-video_春夏爱穿小裙子`: `258` raw candidates, `67` model shots, `121.43s`, about `0.55 shots/sec`.
- `5.20-1 超级编导`: `258` raw candidates, `58` model shots, `141.70s`, about `0.41 shots/sec`.
- `5.20-2 产品口播`: `210` raw candidates, `54` model shots, `92.63s`, about `0.58 shots/sec`.
- `5.20-3 产品口播`: `196` raw candidates, `49` model shots, `95.87s`, about `0.51 shots/sec`.
- `5.20-4 KOC 大丸子`: `167` raw candidates, `46` model shots, `83.80s`, about `0.55 shots/sec`.
- `5.20-5 产品口播`: `164` raw candidates, `43` model shots, `68.73s`, about `0.63 shots/sec`.
- `5.20-6 产品混剪`: `139` raw candidates, `54` model shots, `65.87s`, about `0.82 shots/sec`; higher density was acceptable because fast mixcut states carried product proof.
- `5.20-7 520 活动促销`: `274` raw candidates, `80` model shots, `141.70s`, about `0.56 shots/sec`; opening offer and long promotional proof sequence both needed protection.
- `5.20-8 520 活动`: `207` raw candidates, `43` model shots, `102.80s`, about `0.42 shots/sec`; repeated promotion/presenter segments compressed strongly.
- Practical lesson: this batch is not a single fixed-density mode. Pure口播 and repeated activity scripts can be closer to `0.42-0.58 shots/sec`; short product口播 and fast混剪 can rise to `0.63-0.82 shots/sec` when each kept shot adds product, wearing, scene, or offer proof.
- Keep activity hooks, presenter/scene switches, product reveal, package/product close-up, wearing/no-mark/收腹/safety proof, and final conversion frames. Suppress same-presenter same-composition mouth-movement repeats, even if subtitles continue.
