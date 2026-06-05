import argparse
import json
import subprocess
import sys
from pathlib import Path


def require_dependency(module_name: str, install_hint: str):
    try:
        return __import__(module_name)
    except ImportError as exc:
        raise SystemExit(
            f"Missing dependency: {module_name}\nInstall with: {install_hint}"
        ) from exc


def get_ffmpeg_exe() -> str:
    try:
        imageio_ffmpeg = require_dependency(
            "imageio_ffmpeg",
            "python -m pip install -r requirements-audio.txt",
        )
        return imageio_ffmpeg.get_ffmpeg_exe()
    except SystemExit:
        return "ffmpeg"


def run_ffmpeg_extract(video_path: Path, wav_path: Path) -> None:
    ffmpeg = get_ffmpeg_exe()
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(wav_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise SystemExit(
            "ffmpeg is unavailable. Install audio dependencies with: "
            "python -m pip install -r requirements-audio.txt"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore")
        raise SystemExit(f"Audio extraction failed:\n{stderr}") from exc


def format_srt_time(seconds: float) -> str:
    milliseconds = int(round(max(0.0, seconds) * 1000.0))
    hours, rem = divmod(milliseconds, 3600000)
    minutes, rem = divmod(rem, 60000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_outputs(segments: list[dict], json_path: Path, txt_path: Path, srt_path: Path) -> None:
    payload = {"segments": segments}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text("".join(segment["text"] for segment in segments), encoding="utf-8")

    srt_blocks = []
    for index, segment in enumerate(segments, start=1):
        srt_blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_srt_time(segment['start'])} --> {format_srt_time(segment['end'])}",
                    segment["text"],
                ]
            )
        )
    srt_path.write_text("\n\n".join(srt_blocks) + ("\n" if srt_blocks else ""), encoding="utf-8")


def transcribe(args: argparse.Namespace) -> dict:
    faster_whisper = require_dependency(
        "faster_whisper",
        "python -m pip install -r requirements-audio.txt",
    )
    video_path = args.video_file.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = video_path.stem
    wav_path = output_dir / f"{stem}_audio16k.wav"
    json_path = args.json_file.resolve() if args.json_file else output_dir / f"{stem}_transcript.json"
    txt_path = args.text_file.resolve() if args.text_file else output_dir / f"{stem}_transcript.txt"
    srt_path = args.srt_file.resolve() if args.srt_file else output_dir / f"{stem}_transcript.srt"

    if json_path.exists() and txt_path.exists() and srt_path.exists() and not args.force:
        return {
            "cache_reused": True,
            "json": str(json_path),
            "text": str(txt_path),
            "srt": str(srt_path),
        }

    run_ffmpeg_extract(video_path, wav_path)

    model = faster_whisper.WhisperModel(
        args.model_size,
        device=args.device,
        compute_type=args.compute_type,
    )
    raw_segments, info = model.transcribe(
        str(wav_path),
        language=args.language or None,
        vad_filter=args.vad_filter,
        beam_size=args.beam_size,
    )

    segments = []
    for segment in raw_segments:
        text = " ".join(str(segment.text).strip().split())
        if not text:
            continue
        segments.append(
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "start_ms": int(round(float(segment.start) * 1000.0)),
                "end_ms": int(round(float(segment.end) * 1000.0)),
                "text": text,
            }
        )

    write_outputs(segments, json_path, txt_path, srt_path)
    if not args.keep_audio:
        wav_path.unlink(missing_ok=True)

    return {
        "cache_reused": False,
        "language": getattr(info, "language", args.language),
        "language_probability": getattr(info, "language_probability", None),
        "segments": len(segments),
        "json": str(json_path),
        "text": str(txt_path),
        "srt": str(srt_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe video audio into timed transcript files.")
    parser.add_argument("--video-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("output") / "test" / "audio_transcripts")
    parser.add_argument("--json-file", type=Path, default=None)
    parser.add_argument("--text-file", type=Path, default=None)
    parser.add_argument("--srt-file", type=Path, default=None)
    parser.add_argument("--model-size", default="small")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--vad-filter", action="store_true", default=True)
    parser.add_argument("--no-vad-filter", action="store_false", dest="vad_filter")
    parser.add_argument("--keep-audio", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    result = transcribe(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

