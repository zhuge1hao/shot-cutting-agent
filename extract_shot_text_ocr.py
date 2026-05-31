import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR


def parse_video_ids(value: str, output_dir: Path) -> list[str]:
    if value.lower() == "all":
        ids = [p.name for p in output_dir.iterdir() if p.is_dir() and p.name.isdigit()]
        return sorted(ids, key=lambda item: int(item))
    result: list[str] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            result.extend(str(i) for i in range(int(start), int(end) + 1))
        else:
            result.append(str(int(part)))
    return result


def load_report(video_output_dir: Path, preferred_mode: str) -> tuple[str, Path, dict[str, Any]]:
    candidates = []
    if preferred_mode in {"reference", "auto"}:
        candidates.append(("reference_optimized", video_output_dir / "reference_optimized" / "optimized_shot_report.json"))
    if preferred_mode in {"model", "auto"}:
        candidates.append(("model_optimized", video_output_dir / "model_optimized" / "model_optimized_shot_report.json"))
    for mode, report_path in candidates:
        if report_path.exists():
            return mode, report_path, json.loads(report_path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"No shot report found under {video_output_dir}")


def read_image(path: Path, target_width: int) -> np.ndarray | None:
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        return None
    if target_width > 0 and image.shape[1] > target_width:
        height = int(image.shape[0] * target_width / image.shape[1])
        image = cv2.resize(image, (target_width, height), interpolation=cv2.INTER_AREA)
    return image


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", "", text.strip())
    text = text.replace("。.", "。")
    return text


def should_keep_text(text: str, score: float) -> bool:
    if score < 0.55:
        return False
    normalized = normalize_text(text)
    if not normalized:
        return False
    if len(normalized) <= 2 and re.fullmatch(r"[A-Za-z]+", normalized):
        return False
    return True


def ocr_image(ocr: RapidOCR, image_path: Path, target_width: int) -> tuple[str, str, float, int]:
    image = read_image(image_path, target_width)
    if image is None:
        return "", "", 0.0, 0
    result, _ = ocr(image)
    if not result:
        return "", "", 0.0, 0

    seen: set[str] = set()
    kept: list[tuple[str, float]] = []
    for item in result:
        text = normalize_text(str(item[1]))
        score = float(item[2])
        if not should_keep_text(text, score):
            continue
        if text in seen:
            continue
        seen.add(text)
        kept.append((text, score))

    if not kept:
        return "", "", 0.0, 0
    text = "\n".join(item[0] for item in kept)
    detail = "\n".join(f"{item[0]} ({item[1]:.3f})" for item in kept)
    avg_score = sum(item[1] for item in kept) / len(kept)
    return text, detail, avg_score, len(kept)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract OCR copy from shot evidence frames.")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--videos", default="all", help="all, 1-11, or comma list such as 1,3,11")
    parser.add_argument("--mode", choices=["auto", "reference", "model"], default="reference")
    parser.add_argument("--target-width", type=int, default=900)
    parser.add_argument("--csv-file", default="output/video_shot_text_ocr.csv")
    parser.add_argument("--json-file", default="output/video_shot_text_ocr.json")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    video_ids = parse_video_ids(args.videos, output_dir)
    ocr = RapidOCR()
    rows: list[dict[str, Any]] = []

    for video_id in video_ids:
        video_output_dir = output_dir / video_id
        mode, report_path, report = load_report(video_output_dir, args.mode)
        shots = report.get("shots", [])
        print(f"[OCR] video {video_id}: {mode}, {len(shots)} shots", flush=True)
        previous_text = ""
        for index, shot in enumerate(shots, start=1):
            evidence_frame = Path(str(shot.get("evidence_frame", "")))
            text = ""
            detail = ""
            avg_score = 0.0
            line_count = 0
            if evidence_frame.exists():
                text, detail, avg_score, line_count = ocr_image(ocr, evidence_frame, args.target_width)
            rows.append(
                {
                    "视频编号": video_id,
                    "切分来源": mode,
                    "镜头编号": shot.get("shot_id", f"Shot_{index:03d}"),
                    "起始时间": shot.get("start_time", ""),
                    "结束时间": shot.get("end_time", ""),
                    "起始帧": shot.get("start_frame", ""),
                    "结束帧": shot.get("end_frame", ""),
                    "关键动作标注": shot.get("action_label", ""),
                    "画面文案": text,
                    "是否与上一镜头文案相同": "是" if text and text == previous_text else "否",
                    "OCR平均置信度": round(avg_score, 4) if line_count else "",
                    "OCR行数": line_count,
                    "OCR明细": detail,
                    "证据帧": str(evidence_frame),
                    "参考图": shot.get("reference_image", ""),
                    "报告文件": str(report_path),
                }
            )
            if text:
                previous_text = text

    csv_path = Path(args.csv_file)
    json_path = Path(args.json_file)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "视频编号",
        "切分来源",
        "镜头编号",
        "起始时间",
        "结束时间",
        "起始帧",
        "结束帧",
        "关键动作标注",
        "画面文案",
        "是否与上一镜头文案相同",
        "OCR平均置信度",
        "OCR行数",
        "OCR明细",
        "证据帧",
        "参考图",
        "报告文件",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OCR] wrote {len(rows)} rows to {csv_path}", flush=True)


if __name__ == "__main__":
    main()
