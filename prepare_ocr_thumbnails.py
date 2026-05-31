import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path("E:/USE/codexhome/fenge")
INPUT_JSON = ROOT / "output" / "video_shot_text_ocr.json"
THUMB_DIR = ROOT / "output" / "shot_text_excels" / "_thumbs"


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
    rows = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    created = 0
    for row in rows:
        video_id = str(row["视频编号"])
        shot_id = str(row["镜头编号"])
        src = Path(str(row["证据帧"]))
        dst = THUMB_DIR / video_id / f"{shot_id}.jpg"
        row["缩略图"] = str(dst)
        if src.exists() and save_thumbnail(src, dst):
            created += 1
    out_json = ROOT / "output" / "shot_text_excels" / "video_shot_text_ocr_with_thumbs.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"created {created} thumbnails")
    print(out_json)


if __name__ == "__main__":
    main()
