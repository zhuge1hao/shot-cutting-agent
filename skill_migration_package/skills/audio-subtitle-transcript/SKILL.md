---
name: audio-subtitle-transcript
description: Transcribe speech from videos without burned-in subtitles, generate timed transcript files, and feed those timestamps into shot-text Excel workbooks when OCR subtitles are absent.
---

# Audio Subtitle Transcript

## Purpose

Use this skill when a video has no visible speaking subtitles, or when the user explicitly says the video is `无字幕`. Do not use bottom-white-subtitle OCR as the primary copy source in this mode. Extract speech from the audio track, create timed transcript segments, then align those segments to the existing shot boundaries for Excel拆解.

## Dependencies

Install the optional audio dependencies once:

```powershell
python -m pip install -r .\requirements-audio.txt
```

If the skill was installed without the project repository, install from the skill folder instead:

```powershell
python -m pip install -r "$env:USERPROFILE\.codex\skills\audio-subtitle-transcript\requirements.txt"
```

The transcription script uses `faster-whisper` and `imageio-ffmpeg`. It downloads the selected Whisper model on first use; do not commit downloaded model files.

## Workflow

1. Split the video with the normal shot cutter:

```powershell
python .\shot_cutting_agent.py --video-file "<video.mp4>" --output-dir ".\output\test"
```

If a valid shot report already exists, reuse it. This skill must not tune visual cutting thresholds, regenerate a different shot report, or add/remove shot columns just because the video has no subtitles. No-subtitle mode changes only the copy source, not the visual shot boundaries.

2. Transcribe the audio:

```powershell
python .\skills\audio-subtitle-transcript\scripts\transcribe_video_audio.py --video-file "<video.mp4>" --output-dir ".\output\test\audio_transcripts" --model-size small --language zh
```

This writes:

```text
output/test/audio_transcripts/<video_stem>_transcript.json
output/test/audio_transcripts/<video_stem>_transcript.txt
output/test/audio_transcripts/<video_stem>_transcript.srt
```

3. Generate Excel from timed audio text:

```powershell
python .\build_shot_text_excel_unified.py --video-file "<video.mp4>" --output-dir ".\output\test" --report-mode model --disable-same-subtitle-merge --no-subtitle --timed-transcript-json ".\output\test\audio_transcripts\<video_stem>_transcript.json"
```

## Alignment Rules

- Fill `文案` from audio transcript segments whose timestamps overlap the shot time range.
- Keep blank copy when no speech overlaps the shot.
- Do not borrow OCR text from product packaging, watermarks, disclaimers, or visual title cards.
- If one speech segment spans multiple visual shots, it may repeat across those shot columns; image-copy time alignment is more important than deduplicating.
- If transcript quality is poor, rerun with a larger model such as `medium`, then regenerate Excel with the same shot report.

## Shot Boundary Validation

No-subtitle workbooks should match normal workbooks or the source shot report on visual boundaries when they use the same `--report-mode`.

- `镜头` row must match column by column.
- `时间` row must match column by column.
- Embedded image count should equal the source report shot count.
- Embedded image bytes, dimensions, and anchor positions should match a control workbook when the same source report is used. If `xl/media/*` hashes differ, investigate report selection, evidence paths, thumbnail rebuilding, or workbook generation; do not tune the audio transcript step.
- Differences are expected only in `文案`, `文案框架`, and other copy-influenced planning rows.
- If `镜头` or `时间` changes, debug report selection first; do not adjust the audio transcript skill.

## Speed Defaults

- Start with `--model-size small --language zh`.
- Use `--model-size tiny` or `base` for fast drafts.
- Use `medium` only when Chinese transcription quality is visibly poor.
- Reuse the existing transcript JSON unless the source video, model, or language changed; pass `--force` only when regenerating.
