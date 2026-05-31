import json
import argparse
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create embedded Excel thumbnails for shot OCR rows.")
    parser.add_argument("--root", default=".", help="Project root. Defaults to current working directory.")
    parser.add_argument("--input-json", default="", help="OCR JSON path. Defaults to <root>/output/video_shot_text_ocr.json.")
    parser.add_argument("--output-json", default="", help="Output JSON path with thumbnail paths.")
    parser.add_argument("--thumb-dir", default="", help="Thumbnail output directory.")
    parser.add_argument("--max-width", type=int, default=120, help="Thumbnail canvas width in pixels.")
    parser.add_argument("--max-height", type=int, default=160, help="Thumbnail canvas height in pixels.")
    return parser.parse_args()


def read_image(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def save_thumbnail(src: Path, dst: Path, max_w: int = 120, max_h: int = 160) -> bool:
    image = read_image(src)
    if image is None:
        return False
    h, w = image.shape[:2]
    scale = min(max_w / max(1, w), max_h / max(1, h))
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((max_h, max_w, 3), 250, dtype=np.uint8)
    x = (max_w - nw) // 2
    y = (max_h - nh) // 2
    canvas[y : y + nh, x : x + nw] = resized
    dst.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".jpg", canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
    if not ok:
        return False
    dst.write_bytes(buf.tobytes())
    return True


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    input_json = Path(args.input_json).resolve() if args.input_json else root / "output" / "video_shot_text_ocr.json"
    thumb_dir = Path(args.thumb_dir).resolve() if args.thumb_dir else root / "output" / "shot_text_excels" / "_thumbs"
    out_json = (
        Path(args.output_json).resolve()
        if args.output_json
        else root / "output" / "shot_text_excels" / "video_shot_text_ocr_with_thumbs.json"
    )

    rows = json.loads(input_json.read_text(encoding="utf-8"))
    created = 0
    for row in rows:
        video_id = str(row["视频编号"])
        shot_id = str(row["镜头编号"])
        src = Path(str(row["证据帧"]))
        dst = thumb_dir / video_id / f"{shot_id}.jpg"
        row["缩略图"] = str(dst)
        if src.exists() and save_thumbnail(src, dst, args.max_width, args.max_height):
            created += 1
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"created {created} thumbnails")
    print(out_json)


if __name__ == "__main__":
    main()
