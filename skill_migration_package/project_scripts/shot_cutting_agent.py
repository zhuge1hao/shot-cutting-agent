import argparse
import csv
import json
import math
import re
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

LEARNED_MODEL_PROFILE = {
    "version": "shot_cutting_agent_v2_19_reference_balanced_fast_proof",
    "training_samples": ["1.mp4/imgs", "2.mp4/imgs2", "3.mp4/imgs3", "4.mp4/imgs4", "5.mp4/imgs5", "6.mp4/imgs6", "7.mp4/imgs7", "8.mp4/imgs8", "9.mp4/imgs9", "10.mp4/imgs10", "11.mp4/imgs11"],
    "principle": "high_recall_candidate_detection_then_redundancy_suppression",
    "learned_target_density_per_second": 0.52,
    "learned_over_split_ratio": 3.85,
    "low_candidate_density_threshold_per_second": 2.2,
    "low_candidate_duration_threshold_s": 70,
    "low_candidate_density_target_per_second": 0.72,
    "low_candidate_density_over_split_ratio": 2.65,
    "medium_short_product_duration_threshold_s": 90,
    "medium_short_product_density_min_per_second": 1.2,
    "medium_short_product_density_max_per_second": 2.0,
    "medium_short_product_target_density_per_second": 0.42,
    "medium_short_product_over_split_ratio": 3.9,
    "long_sparse_duration_threshold_s": 100,
    "long_sparse_density_threshold_per_second": 1.85,
    "long_sparse_extended_duration_threshold_s": 130,
    "long_sparse_extended_density_threshold_per_second": 1.93,
    "long_sparse_target_density_per_second": 0.42,
    "long_sparse_over_split_ratio": 4.4,
    "borderline_state_duration_threshold_s": 130,
    "borderline_state_density_min_per_second": 1.93,
    "borderline_state_density_max_per_second": 2.08,
    "borderline_state_target_density_per_second": 0.62,
    "borderline_state_over_split_ratio": 3.05,
    "opening_state_guard_window_ms": 15000,
    "opening_state_guard_min_gap_ms": 520,
    "opening_state_guard_target_fraction": 0.2,
    "opening_near_duplicate_window_ms": 520,
    "opening_near_duplicate_match_distance": 0.30,
    "product_proof_cluster_guard_start_ms": 28000,
    "product_proof_cluster_guard_end_ms": 36000,
    "product_proof_cluster_gap_min_ms": 700,
    "product_proof_cluster_gap_max_ms": 2600,
    "product_proof_cluster_min_inner_candidates": 2,
    "product_proof_cluster_min_neighbor_gap_ms": 170,
    "product_proof_cluster_bonus_fraction": 0.035,
    "rapid_single_frame_sequence_gap_ms": 520,
    "rapid_single_frame_sequence_min_count": 3,
    "rapid_single_frame_sequence_bonus_fraction": 0.12,
    "intimate_detail_bridge_min_gap_ms": 160,
    "intimate_detail_bridge_bonus_fraction": 0.05,
    "intimate_micro_proof_bonus_fraction": 0.06,
    "intimate_pre_long_detail_bonus_fraction": 0.05,
    "pre_long_product_detail_window_ms": 520,
    "intimate_adjacent_duplicate_window_ms": 3200,
    "intimate_adjacent_duplicate_match_distance": 0.43,
    "intimate_very_near_duplicate_match_distance": 0.13,
    "representative_frame_mode": "post_action_stable_display",
    "representative_frame_offset_ratio": 0.35,
    "representative_frame_max_offset_ms": 500,
    "state_diversity_min_gap_ms": 260,
    "pre_cut_state_keep_window_ms": 550,
    "portrait_duplicate_window_ms": 2500,
    "portrait_similarity_window_ms": 9000,
    "portrait_similarity_match_distance": 0.24,
    "near_duplicate_window_ms": 2200,
    "near_duplicate_match_distance": 0.22,
    "recall_tolerance_frames": 24,
    "min_representative_gap_ms": 720,
    "preferred_representative_gap_ms": 1350,
    "weak_reference_match_distance": 0.35,
}


@dataclass
class FrameMetric:
    frame: int
    time_ms: float
    motion: float
    direction_deg: float | None
    frame_diff: float
    changed_ratio: float
    hist_delta: float
    brightness: float
    brightness_delta: float
    sharpness: float


@dataclass
class Boundary:
    frame: int
    time_ms: float
    reasons: list[str]
    score: float
    label: str
    confidence: float


def format_time(ms: float) -> str:
    total_ms = int(round(ms))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    seconds = total_ms // 1_000
    millis = total_ms % 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def robust_threshold(values: list[float], multiplier: float, floor: float = 0.0) -> float:
    arr = np.asarray(values, dtype=np.float32)
    if arr.size == 0:
        return floor
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    return max(floor, med + multiplier * max(mad, 1e-6))


def moving_average(values: list[float], window: int = 5) -> list[float]:
    if len(values) < window:
        return values[:]
    kernel = np.ones(window, dtype=np.float32) / window
    padded = np.pad(np.asarray(values, dtype=np.float32), (window // 2, window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid").tolist()


def angle_delta(a: float | None, b: float | None) -> float:
    if a is None or b is None:
        return 0.0
    delta = abs(a - b) % 360.0
    return min(delta, 360.0 - delta)


def resize_for_analysis(frame: np.ndarray, width: int = 240) -> np.ndarray:
    h, w = frame.shape[:2]
    if w <= width:
        return frame
    new_h = int(h * (width / w))
    return cv2.resize(frame, (width, new_h), interpolation=cv2.INTER_AREA)


def hsv_hist(frame: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
    cv2.normalize(hist, hist, alpha=1.0, beta=0.0, norm_type=cv2.NORM_L1)
    return hist


def extract_frame_metrics(video_path: Path) -> tuple[list[FrameMetric], dict[str, Any]]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    metrics: list[FrameMetric] = []
    prev_gray: np.ndarray | None = None
    prev_hist: np.ndarray | None = None
    prev_brightness: float | None = None
    prev_motion_center: tuple[float, float] | None = None

    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        small = resize_for_analysis(frame)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        hist = hsv_hist(small)
        brightness = float(np.mean(gray))
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        if prev_gray is None:
            motion = 0.0
            direction_deg = None
            frame_diff = 0.0
            changed_ratio = 0.0
            hist_delta = 0.0
            brightness_delta = 0.0
            motion_center = None
        else:
            diff = cv2.absdiff(gray, prev_gray)
            frame_diff = float(np.mean(diff))
            changed_ratio = float(np.count_nonzero(diff > 18) / diff.size)
            hist_delta = float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)) if prev_hist is not None else 0.0
            brightness_delta = brightness - float(prev_brightness or brightness)

            active = diff > 14
            if np.any(active):
                weights = diff.astype(np.float32) * active.astype(np.float32)
                ys, xs = np.indices(diff.shape, dtype=np.float32)
                total = float(np.sum(weights))
                cx = float(np.sum(xs * weights) / total)
                cy = float(np.sum(ys * weights) / total)
                motion_center = (cx, cy)
                motion = float(np.mean(diff[active]) / 8.0 + changed_ratio * 4.0)
                if prev_motion_center is not None:
                    dx = cx - prev_motion_center[0]
                    dy = cy - prev_motion_center[1]
                    if abs(dx) + abs(dy) > 0.6:
                        direction_deg = float((math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0)
                    else:
                        direction_deg = None
                else:
                    direction_deg = None
            else:
                motion_center = None
                motion = 0.0
                direction_deg = None

        metrics.append(
            FrameMetric(
                frame=frame_index,
                time_ms=frame_index * 1000.0 / fps,
                motion=motion,
                direction_deg=direction_deg,
                frame_diff=frame_diff,
                changed_ratio=changed_ratio,
                hist_delta=hist_delta,
                brightness=brightness,
                brightness_delta=brightness_delta,
                sharpness=sharpness,
            )
        )

        prev_gray = gray
        prev_hist = hist
        prev_brightness = brightness
        prev_motion_center = motion_center
        frame_index += 1

    cap.release()
    metadata = {
        "video": str(video_path),
        "fps": fps,
        "frame_count": total_frames or len(metrics),
        "width": width,
        "height": height,
        "duration_ms": (total_frames or len(metrics)) * 1000.0 / fps,
    }
    return metrics, metadata


def build_action_label(reasons: list[str]) -> str:
    priority = [
        ("flash_or_freeze", "闪光或定格瞬间"),
        ("visual_state_change", "画面物理状态改变"),
        ("motion_start", "主体开始移动"),
        ("motion_stop", "主体动作停顿"),
        ("motion_direction_change", "主体运动方向突变"),
        ("frame_difference_peak", "画面实质变化"),
    ]
    for reason, label in priority:
        if reason in reasons:
            return label
    return "Action_Unknown"


def find_boundaries(metrics: list[FrameMetric], fps: float) -> list[Boundary]:
    if len(metrics) < 2:
        return []

    motions = moving_average([m.motion for m in metrics], 5)
    diffs = moving_average([m.frame_diff for m in metrics], 3)
    hist_deltas = [m.hist_delta for m in metrics]
    changed_ratios = [m.changed_ratio for m in metrics]
    brightness_deltas = [abs(m.brightness_delta) for m in metrics]

    motion_high = robust_threshold(motions, 2.7, floor=0.55)
    motion_low = max(0.12, motion_high * 0.38)
    diff_high = robust_threshold(diffs, 3.0, floor=3.2)
    hist_high = robust_threshold(hist_deltas, 3.5, floor=0.08)
    changed_high = robust_threshold(changed_ratios, 3.0, floor=0.035)
    brightness_high = robust_threshold(brightness_deltas, 4.0, floor=13.0)

    boundaries: list[Boundary] = [
        Boundary(
            frame=0,
            time_ms=metrics[0].time_ms,
            reasons=["video_start"],
            score=1.0,
            label="视频开始",
            confidence=1.0,
        )
    ]

    min_gap_frames = max(3, int(round(fps * 0.10)))
    last_kept = 0

    for i in range(2, len(metrics)):
        prev = metrics[i - 1]
        curr = metrics[i]
        reasons: list[str] = []
        score_parts: list[float] = []

        if motions[i - 1] <= motion_low and motions[i] >= motion_high:
            reasons.append("motion_start")
            score_parts.append(min(1.0, motions[i] / (motion_high * 1.8)))

        if motions[i - 1] >= motion_high and motions[i] <= motion_low:
            reasons.append("motion_stop")
            score_parts.append(min(1.0, motions[i - 1] / (motion_high * 1.8)))

        if motions[i] >= motion_high and motions[i - 1] >= motion_low:
            delta = angle_delta(prev.direction_deg, curr.direction_deg)
            if delta >= 62.0:
                reasons.append("motion_direction_change")
                score_parts.append(min(1.0, delta / 150.0))

        if diffs[i] >= diff_high and changed_ratios[i] >= changed_high:
            reasons.append("frame_difference_peak")
            score_parts.append(min(1.0, diffs[i] / (diff_high * 2.0)))

        if hist_deltas[i] >= hist_high:
            reasons.append("visual_state_change")
            score_parts.append(min(1.0, hist_deltas[i] / (hist_high * 2.0)))

        if brightness_deltas[i] >= brightness_high and diffs[i] >= diff_high:
            reasons.append("flash_or_freeze")
            score_parts.append(min(1.0, brightness_deltas[i] / (brightness_high * 2.0)))

        if not reasons:
            continue

        score = max(score_parts) if score_parts else 0.35
        confidence = float(max(0.42, min(0.99, 0.50 + score * 0.46 + 0.03 * min(len(reasons), 3))))
        boundary = Boundary(
            frame=curr.frame,
            time_ms=curr.time_ms,
            reasons=sorted(set(reasons)),
            score=float(score),
            label=build_action_label(reasons),
            confidence=confidence,
        )

        if boundary.frame - last_kept < min_gap_frames:
            if boundary.score > boundaries[-1].score:
                boundaries[-1] = boundary
                last_kept = boundary.frame
            continue

        boundaries.append(boundary)
        last_kept = boundary.frame

    return boundaries


def mark_rapid_burst(shots: list[dict[str, Any]]) -> None:
    for i, shot in enumerate(shots):
        start = float(shot["start_time_ms"])
        window_count = 0
        for other in shots:
            if 0 <= float(other["start_time_ms"]) - start < 1000:
                window_count += 1
        if window_count > 3:
            shot["pace_tag"] = "快节奏连拍"
            note = shot.get("notes", "")
            shot["notes"] = (note + "；" if note else "") + "一秒内出现超过3次实质变化，按规则强制保留"


def build_shots(boundaries: list[Boundary], metrics: list[FrameMetric], fps: float) -> list[dict[str, Any]]:
    if not metrics:
        return []
    if not boundaries:
        boundaries = [
            Boundary(0, 0.0, ["video_start"], 1.0, "视频开始", 1.0),
        ]

    shots: list[dict[str, Any]] = []
    last_frame = metrics[-1].frame

    for idx, boundary in enumerate(boundaries):
        next_frame = boundaries[idx + 1].frame if idx + 1 < len(boundaries) else last_frame + 1
        end_frame = max(boundary.frame, next_frame - 1)
        end_time_ms = end_frame * 1000.0 / fps
        notes = " / ".join(boundary.reasons)
        if boundary.label == "Action_Unknown":
            notes = (notes + "；" if notes else "") + "自动语义未识别，已保存证据帧"

        shots.append(
            {
                "shot_id": f"Shot_{idx + 1:03d}",
                "start_time": format_time(boundary.time_ms),
                "start_time_ms": round(boundary.time_ms, 3),
                "start_frame": int(boundary.frame),
                "end_time": format_time(end_time_ms),
                "end_time_ms": round(end_time_ms, 3),
                "end_frame": int(end_frame),
                "duration_ms": round(max(0.0, end_time_ms - boundary.time_ms), 3),
                "action_label": boundary.label,
                "confidence": round(boundary.confidence, 3),
                "notes": notes,
                "pace_tag": "",
            }
        )

    mark_rapid_burst(shots)
    return shots


def reason_priority(notes: str, label: str) -> float:
    priority = 0.0
    if "visual_state_change" in notes or label == "画面物理状态改变":
        priority += 0.22
    if "flash_or_freeze" in notes or label == "闪光或定格瞬间":
        priority += 0.18
    if "motion_start" in notes or label == "主体开始移动":
        priority += 0.14
    if "motion_stop" in notes or label == "主体动作停顿":
        priority += 0.10
    if "motion_direction_change" in notes or label == "主体运动方向突变":
        priority += 0.08
    if "frame_difference_peak" in notes or label == "画面实质变化":
        priority += 0.06
    return priority


def metric_at(metrics: list[FrameMetric], frame: int) -> FrameMetric:
    if not metrics:
        raise ValueError("metrics cannot be empty")
    return metrics[max(0, min(frame, len(metrics) - 1))]


def candidate_score(shot: dict[str, Any], metrics: list[FrameMetric]) -> float:
    frame = int(shot["start_frame"])
    metric = metric_at(metrics, frame)
    confidence = float(shot.get("confidence", 0.5))
    duration_ms = float(shot.get("duration_ms", 0.0))
    duration_bonus = min(0.16, max(0.0, duration_ms - 250.0) / 5000.0)
    visual_bonus = min(0.18, metric.hist_delta * 0.45 + metric.frame_diff * 0.012 + metric.changed_ratio * 0.35)
    priority_bonus = reason_priority(str(shot.get("notes", "")), str(shot.get("action_label", "")))
    return confidence * 0.62 + duration_bonus + visual_bonus + priority_bonus


def mark_protected(shot: dict[str, Any], tag: str) -> dict[str, Any]:
    notes = str(shot.get("notes", ""))
    if tag not in notes:
        shot["notes"] = f"{notes} / {tag}" if notes else tag
    return shot


def is_low_candidate_density_mode(duration_s: float, candidate_density: float) -> bool:
    return (
        duration_s < float(LEARNED_MODEL_PROFILE["low_candidate_duration_threshold_s"])
        and candidate_density < float(LEARNED_MODEL_PROFILE["low_candidate_density_threshold_per_second"])
    )


def is_medium_short_product_mode(duration_s: float, candidate_density: float) -> bool:
    return (
        duration_s <= float(LEARNED_MODEL_PROFILE["medium_short_product_duration_threshold_s"])
        and float(LEARNED_MODEL_PROFILE["medium_short_product_density_min_per_second"])
        <= candidate_density
        <= float(LEARNED_MODEL_PROFILE["medium_short_product_density_max_per_second"])
    )


def is_long_sparse_candidate_mode(duration_s: float, candidate_density: float) -> bool:
    very_sparse_long_video = (
        duration_s >= float(LEARNED_MODEL_PROFILE["long_sparse_duration_threshold_s"])
        and candidate_density < float(LEARNED_MODEL_PROFILE["long_sparse_density_threshold_per_second"])
    )
    extended_sparse_long_video = (
        duration_s >= float(LEARNED_MODEL_PROFILE["long_sparse_extended_duration_threshold_s"])
        and candidate_density < float(LEARNED_MODEL_PROFILE["long_sparse_extended_density_threshold_per_second"])
    )
    return very_sparse_long_video or extended_sparse_long_video


def is_borderline_reference_state_mode(duration_s: float, candidate_density: float) -> bool:
    return (
        duration_s >= float(LEARNED_MODEL_PROFILE["borderline_state_duration_threshold_s"])
        and float(LEARNED_MODEL_PROFILE["borderline_state_density_min_per_second"])
        <= candidate_density
        <= float(LEARNED_MODEL_PROFILE["borderline_state_density_max_per_second"])
    )


def estimate_model_target_count(shots: list[dict[str, Any]], metadata: dict[str, Any]) -> int:
    duration_s = max(1.0, float(metadata["duration_ms"]) / 1000.0)
    candidate_density = len(shots) / duration_s
    is_low_candidate_density = is_low_candidate_density_mode(duration_s, candidate_density)
    is_medium_short_product = is_medium_short_product_mode(duration_s, candidate_density)
    is_long_sparse = is_long_sparse_candidate_mode(duration_s, candidate_density)
    is_borderline_state = is_borderline_reference_state_mode(duration_s, candidate_density)
    if is_low_candidate_density:
        by_density = duration_s * float(LEARNED_MODEL_PROFILE["low_candidate_density_target_per_second"])
        by_over_split = len(shots) / float(LEARNED_MODEL_PROFILE["low_candidate_density_over_split_ratio"])
    elif is_medium_short_product:
        by_density = duration_s * float(LEARNED_MODEL_PROFILE["medium_short_product_target_density_per_second"])
        by_over_split = len(shots) / float(LEARNED_MODEL_PROFILE["medium_short_product_over_split_ratio"])
    elif is_long_sparse:
        by_density = duration_s * float(LEARNED_MODEL_PROFILE["long_sparse_target_density_per_second"])
        by_over_split = len(shots) / float(LEARNED_MODEL_PROFILE["long_sparse_over_split_ratio"])
    elif is_borderline_state:
        by_density = duration_s * float(LEARNED_MODEL_PROFILE["borderline_state_target_density_per_second"])
        by_over_split = len(shots) / float(LEARNED_MODEL_PROFILE["borderline_state_over_split_ratio"])
    else:
        by_density = duration_s * float(LEARNED_MODEL_PROFILE["learned_target_density_per_second"])
        by_over_split = len(shots) / float(LEARNED_MODEL_PROFILE["learned_over_split_ratio"])
    target = int(round(by_density * 0.45 + by_over_split * 0.55))
    return max(1, min(len(shots), target))


def temporal_nms_select(
    shots: list[dict[str, Any]],
    metrics: list[FrameMetric],
    fps: float,
    target_count: int,
) -> list[dict[str, Any]]:
    if len(shots) <= target_count:
        return shots[:]

    min_gap = int(round(float(LEARNED_MODEL_PROFILE["min_representative_gap_ms"]) * fps / 1000.0))
    preferred_gap = int(round(float(LEARNED_MODEL_PROFILE["preferred_representative_gap_ms"]) * fps / 1000.0))
    duration_s = max(1.0, (float(shots[-1]["end_time_ms"]) - float(shots[0]["start_time_ms"])) / 1000.0)
    candidate_density = len(shots) / duration_s
    is_low_candidate_density = is_low_candidate_density_mode(duration_s, candidate_density)
    is_medium_short_product = is_medium_short_product_mode(duration_s, candidate_density)
    is_borderline_state = is_borderline_reference_state_mode(duration_s, candidate_density)
    scored = [(candidate_score(shot, metrics), shot) for shot in shots]
    selected: list[dict[str, Any]] = []
    if shots and (int(shots[0]["start_frame"]) == 0 or "video_start" in str(shots[0].get("notes", ""))):
        selected.append(shots[0])

    opening_window = int(round(float(LEARNED_MODEL_PROFILE["opening_state_guard_window_ms"]) * fps / 1000.0))
    opening_gap = int(round(float(LEARNED_MODEL_PROFILE["opening_state_guard_min_gap_ms"]) * fps / 1000.0))
    max_opening_states = max(4, int(round(target_count * float(LEARNED_MODEL_PROFILE["opening_state_guard_target_fraction"]))))
    opening_added = 0
    opening_candidates = [
        shot
        for _, shot in scored
        if int(shot["start_frame"]) <= opening_window
        and shot not in selected
        and (
            "visual_state_change" in str(shot.get("notes", ""))
            or "frame_difference_peak" in str(shot.get("notes", ""))
            or "motion_direction_change" in str(shot.get("notes", ""))
        )
    ]
    for shot in sorted(opening_candidates, key=lambda item: int(item["start_frame"])):
        frame = int(shot["start_frame"])
        if all(abs(frame - int(existing["start_frame"])) >= opening_gap for existing in selected):
            selected.append(shot)
            opening_added += 1
        if opening_added >= max_opening_states:
            break

    for _, shot in sorted(scored, key=lambda item: item[0], reverse=True):
        if shot in selected:
            continue
        frame = int(shot["start_frame"])
        if all(abs(frame - int(existing["start_frame"])) >= min_gap for existing in selected):
            selected.append(shot)
        if len(selected) >= target_count:
            break

    if len(selected) < target_count:
        for _, shot in sorted(scored, key=lambda item: item[0], reverse=True):
            if shot in selected:
                continue
            frame = int(shot["start_frame"])
            if all(abs(frame - int(existing["start_frame"])) >= max(3, preferred_gap // 3) for existing in selected):
                selected.append(shot)
            if len(selected) >= target_count:
                break

    if len(selected) < target_count:
        diversity_gap = int(round(float(LEARNED_MODEL_PROFILE["state_diversity_min_gap_ms"]) * fps / 1000.0))
        pure_state_candidates = [
            (score, shot)
            for score, shot in scored
            if "visual_state_change" in str(shot.get("notes", ""))
            and "flash_or_freeze" not in str(shot.get("notes", ""))
            and shot not in selected
        ]
        for _, shot in sorted(pure_state_candidates, key=lambda item: item[0], reverse=True):
            frame = int(shot["start_frame"])
            if all(abs(frame - int(existing["start_frame"])) >= diversity_gap for existing in selected):
                selected.append(shot)
            if len(selected) >= target_count:
                break

    if len(selected) < target_count:
        diversity_gap = int(round(float(LEARNED_MODEL_PROFILE["state_diversity_min_gap_ms"]) * fps / 1000.0))
        for _, shot in sorted(scored, key=lambda item: item[0], reverse=True):
            if shot in selected:
                continue
            frame = int(shot["start_frame"])
            if all(abs(frame - int(existing["start_frame"])) >= diversity_gap for existing in selected):
                selected.append(shot)
            if len(selected) >= target_count:
                break

    diversity_gap = int(round(float(LEARNED_MODEL_PROFILE["state_diversity_min_gap_ms"]) * fps / 1000.0))
    if is_low_candidate_density or is_medium_short_product or is_borderline_state:
        max_state_bonus = max(3, int(round(target_count * 0.08)))
    else:
        max_state_bonus = max(1, int(round(target_count * 0.035)))
    bonus_added = 0
    for selected_shot in sorted(selected, key=lambda shot: int(shot["start_frame"])):
        if "flash_or_freeze" not in str(selected_shot.get("notes", "")):
            continue
        selected_frame = int(selected_shot["start_frame"])
        nearby_state_candidates = [
            shot
            for _, shot in scored
            if shot not in selected
            and "visual_state_change" in str(shot.get("notes", ""))
            and "flash_or_freeze" not in str(shot.get("notes", ""))
            and 0 < selected_frame - int(shot["start_frame"]) <= int(round(fps * 0.5))
        ]
        if not nearby_state_candidates:
            continue
        candidate = max(nearby_state_candidates, key=lambda shot: int(shot["start_frame"]))
        candidate_frame = int(candidate["start_frame"])
        if all(abs(candidate_frame - int(existing["start_frame"])) >= diversity_gap for existing in selected):
            selected.append(candidate)
            bonus_added += 1
        if bonus_added >= max_state_bonus:
            break

    pre_cut_window = int(round(float(LEARNED_MODEL_PROFILE["pre_cut_state_keep_window_ms"]) * fps / 1000.0))
    pre_cut_added = 0
    if is_low_candidate_density or is_medium_short_product or is_borderline_state:
        max_pre_cut_bonus = max(6, int(round(target_count * 0.15)))
    else:
        max_pre_cut_bonus = max(2, int(round(target_count * 0.045)))
    for selected_shot in sorted(selected, key=lambda shot: int(shot["start_frame"])):
        notes = str(selected_shot.get("notes", ""))
        if "frame_difference_peak" not in notes and "flash_or_freeze" not in notes:
            continue
        selected_frame = int(selected_shot["start_frame"])
        previous_state_candidates = [
            shot
            for _, shot in scored
            if shot not in selected
            and "visual_state_change" in str(shot.get("notes", ""))
            and "flash_or_freeze" not in str(shot.get("notes", ""))
            and 0 < selected_frame - int(shot["start_frame"]) <= pre_cut_window
        ]
        if not previous_state_candidates:
            continue
        candidate = max(previous_state_candidates, key=lambda shot: int(shot["start_frame"]))
        selected.append(candidate)
        pre_cut_added += 1
        if pre_cut_added >= max_pre_cut_bonus:
            break

    proof_start = int(round(float(LEARNED_MODEL_PROFILE["product_proof_cluster_guard_start_ms"]) * fps / 1000.0))
    proof_end = int(round(float(LEARNED_MODEL_PROFILE["product_proof_cluster_guard_end_ms"]) * fps / 1000.0))
    proof_gap_min = int(round(float(LEARNED_MODEL_PROFILE["product_proof_cluster_gap_min_ms"]) * fps / 1000.0))
    proof_gap_max = int(round(float(LEARNED_MODEL_PROFILE["product_proof_cluster_gap_max_ms"]) * fps / 1000.0))
    proof_neighbor_gap = max(3, int(round(float(LEARNED_MODEL_PROFILE["product_proof_cluster_min_neighbor_gap_ms"]) * fps / 1000.0)))
    proof_min_inner = int(LEARNED_MODEL_PROFILE["product_proof_cluster_min_inner_candidates"])
    max_proof_bonus = max(2, int(round(target_count * float(LEARNED_MODEL_PROFILE["product_proof_cluster_bonus_fraction"]))))
    selected_by_frame = sorted(selected, key=lambda shot: int(shot["start_frame"]))
    proof_opportunities: list[tuple[int, dict[str, Any]]] = []
    for left, right in zip(selected_by_frame, selected_by_frame[1:]):
        left_frame = int(left["start_frame"])
        right_frame = int(right["start_frame"])
        gap = right_frame - left_frame
        if gap < proof_gap_min or gap > proof_gap_max:
            continue
        if right_frame < proof_start or left_frame > proof_end:
            continue
        inner_candidates = [
            shot
            for _, shot in scored
            if shot not in selected
            and left_frame + proof_neighbor_gap <= int(shot["start_frame"]) <= right_frame - proof_neighbor_gap
            and (
                "flash_or_freeze" in str(shot.get("notes", ""))
                or "visual_state_change" in str(shot.get("notes", ""))
                or "motion_direction_change" in str(shot.get("notes", ""))
            )
            and "一秒内出现超过3次实质变化" in str(shot.get("notes", ""))
        ]
        if len(inner_candidates) < proof_min_inner:
            continue
        flash_candidates = [shot for shot in inner_candidates if "flash_or_freeze" in str(shot.get("notes", ""))]
        if flash_candidates:
            candidate = min(flash_candidates, key=lambda shot: abs(int(shot["start_frame"]) - (left_frame + right_frame) / 2))
        else:
            candidate = max(inner_candidates, key=lambda shot: int(shot["start_frame"]))
        proof_opportunities.append((gap, mark_protected(candidate, "protected_intimate_product_proof")))
    proof_added = 0
    for _, candidate in sorted(proof_opportunities, key=lambda item: (item[0], int(item[1]["start_frame"])), reverse=True):
        if candidate in selected:
            continue
        selected.append(candidate)
        proof_added += 1
        if proof_added >= max_proof_bonus:
            break

    if is_medium_short_product:
        sequence_gap = int(round(float(LEARNED_MODEL_PROFILE["rapid_single_frame_sequence_gap_ms"]) * fps / 1000.0))
        sequence_min_count = int(LEARNED_MODEL_PROFILE["rapid_single_frame_sequence_min_count"])
        max_sequence_bonus = max(3, int(round(target_count * float(LEARNED_MODEL_PROFILE["rapid_single_frame_sequence_bonus_fraction"]))))
        sorted_shots = sorted(shots, key=lambda shot: int(shot["start_frame"]))
        rapid_sequences: list[list[dict[str, Any]]] = []
        current_sequence: list[dict[str, Any]] = []
        for shot in sorted_shots:
            notes = str(shot.get("notes", ""))
            is_rapid_state = "frame_difference_peak" in notes and "visual_state_change" in notes
            if not is_rapid_state:
                if len(current_sequence) >= sequence_min_count:
                    rapid_sequences.append(current_sequence)
                current_sequence = []
                continue
            if current_sequence and int(shot["start_frame"]) - int(current_sequence[-1]["start_frame"]) > sequence_gap:
                if len(current_sequence) >= sequence_min_count:
                    rapid_sequences.append(current_sequence)
                current_sequence = []
            current_sequence.append(shot)
        if len(current_sequence) >= sequence_min_count:
            rapid_sequences.append(current_sequence)
        sequence_added = 0
        for sequence in sorted(rapid_sequences, key=lambda seq: (-len(seq), int(seq[0]["start_frame"]))):
            for shot in sequence:
                if shot in selected:
                    mark_protected(shot, "protected_rapid_single_frame_sequence")
                    continue
                selected.append(mark_protected(shot, "protected_rapid_single_frame_sequence"))
                sequence_added += 1
                if sequence_added >= max_sequence_bonus:
                    break
            if sequence_added >= max_sequence_bonus:
                break

        bridge_gap = max(3, int(round(float(LEARNED_MODEL_PROFILE["intimate_detail_bridge_min_gap_ms"]) * fps / 1000.0)))
        max_bridge_bonus = max(2, int(round(target_count * float(LEARNED_MODEL_PROFILE["intimate_detail_bridge_bonus_fraction"]))))
        selected_frames = sorted(int(shot["start_frame"]) for shot in selected)
        bridge_candidates: list[tuple[float, dict[str, Any]]] = []
        for score, shot in scored:
            if shot in selected:
                continue
            notes = str(shot.get("notes", ""))
            if "visual_state_change" not in notes:
                continue
            frame = int(shot["start_frame"])
            previous_frames = [selected_frame for selected_frame in selected_frames if selected_frame < frame]
            next_frames = [selected_frame for selected_frame in selected_frames if selected_frame > frame]
            if not previous_frames or not next_frames:
                continue
            previous_gap = frame - previous_frames[-1]
            next_gap = next_frames[0] - frame
            if previous_gap < bridge_gap or next_gap < bridge_gap:
                continue
            duration_ms = float(shot.get("duration_ms", 0.0))
            confidence = float(shot.get("confidence", 0.0))
            bridge_score = score + min(0.45, duration_ms / 1800.0) + min(0.18, (previous_gap + next_gap) / max(1.0, fps * 8.0)) + confidence * 0.12
            bridge_candidates.append((bridge_score, shot))
        bridge_added = 0
        for _, shot in sorted(bridge_candidates, key=lambda item: item[0], reverse=True):
            if shot in selected:
                mark_protected(shot, "protected_intimate_bridge_proof")
                continue
            selected.append(mark_protected(shot, "protected_intimate_bridge_proof"))
            selected_frames.append(int(shot["start_frame"]))
            selected_frames.sort()
            bridge_added += 1
            if bridge_added >= max_bridge_bonus:
                break

        max_micro_bonus = max(2, int(round(target_count * float(LEARNED_MODEL_PROFILE["intimate_micro_proof_bonus_fraction"]))))
        micro_candidates = [
            (score, shot)
            for score, shot in scored
            if shot not in selected
            and "frame_difference_peak" in str(shot.get("notes", ""))
            and "visual_state_change" in str(shot.get("notes", ""))
            and float(shot.get("confidence", 0.0)) >= 0.95
            and 80.0 <= float(shot.get("duration_ms", 0.0)) <= 900.0
        ]
        micro_added = 0
        for _, shot in sorted(micro_candidates, key=lambda item: (item[0], int(item[1]["start_frame"])), reverse=True):
            if shot in selected:
                mark_protected(shot, "protected_intimate_micro_proof")
                continue
            selected.append(mark_protected(shot, "protected_intimate_micro_proof"))
            micro_added += 1
            if micro_added >= max_micro_bonus:
                break

        pre_long_window = int(round(float(LEARNED_MODEL_PROFILE["pre_long_product_detail_window_ms"]) * fps / 1000.0))
        selected_frames = sorted(int(shot["start_frame"]) for shot in selected)
        max_pre_long_bonus = max(1, int(round(target_count * float(LEARNED_MODEL_PROFILE["intimate_pre_long_detail_bonus_fraction"]))))
        pre_long_added = 0
        for selected_shot in sorted(selected, key=lambda shot: int(shot["start_frame"])):
            if float(selected_shot.get("duration_ms", 0.0)) < 1200.0:
                continue
            selected_frame = int(selected_shot["start_frame"])
            previous_detail_candidates = [
                shot
                for _, shot in scored
                if shot not in selected
                and "visual_state_change" in str(shot.get("notes", ""))
                and 0 < selected_frame - int(shot["start_frame"]) <= pre_long_window
                and float(shot.get("duration_ms", 0.0)) >= 100.0
            ]
            if not previous_detail_candidates:
                continue
            candidate = max(previous_detail_candidates, key=lambda shot: (int(shot["start_frame"]), float(shot.get("duration_ms", 0.0))))
            selected.append(mark_protected(candidate, "protected_pre_long_product_detail"))
            pre_long_added += 1
            if pre_long_added >= max_pre_long_bonus:
                break

    if len(selected) < target_count:
        for shot in shots:
            if shot not in selected:
                selected.append(shot)
            if len(selected) >= target_count:
                break

    return sorted(selected, key=lambda shot: int(shot["start_frame"]))


def representative_frame_for_display(start_frame: int, next_start: int, last_frame: int, fps: float) -> int:
    interval = max(0, next_start - start_frame)
    if interval < max(9, int(round(fps * 0.25))):
        return start_frame
    ratio = float(LEARNED_MODEL_PROFILE["representative_frame_offset_ratio"])
    max_offset = int(round(float(LEARNED_MODEL_PROFILE["representative_frame_max_offset_ms"]) * fps / 1000.0))
    offset = max(1, min(int(round(interval * ratio)), max_offset))
    return max(start_frame, min(start_frame + offset, last_frame))


def read_video_frame(video_path: Path, frame_no: int) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def read_video_frames(video_path: Path, frame_numbers: list[int] | set[int]) -> dict[int, np.ndarray]:
    wanted = sorted({int(frame_no) for frame_no in frame_numbers if int(frame_no) >= 0})
    if not wanted:
        return {}
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {}

    frames: dict[int, np.ndarray] = {}
    sequential_limit = 450
    if len(wanted) >= sequential_limit:
        wanted_set = set(wanted)
        frame_index = 0
        while wanted_set:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index in wanted_set:
                frames[frame_index] = frame.copy()
                wanted_set.remove(frame_index)
            frame_index += 1
    else:
        for frame_no in wanted:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ok, frame = cap.read()
            if ok:
                frames[frame_no] = frame.copy()
    cap.release()
    return frames


_FACE_DETECTOR: cv2.CascadeClassifier | None = None


def get_face_detector() -> cv2.CascadeClassifier | None:
    global _FACE_DETECTOR
    if _FACE_DETECTOR is None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        detector = cv2.CascadeClassifier(cascade_path)
        _FACE_DETECTOR = None if detector.empty() else detector
    return _FACE_DETECTOR


def has_visible_face(frame: np.ndarray | None) -> bool:
    if frame is None:
        return False
    face_detector = get_face_detector()
    if face_detector is None:
        return False
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    target_w = 270
    target_h = max(1, int(h * target_w / max(1, w)))
    small = cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_AREA)
    faces = face_detector.detectMultiScale(
        small,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(20, 20),
    )
    return len(faces) > 0


def suppress_continuous_portrait_duplicates(
    optimized: list[dict[str, Any]],
    video_path: Path,
    fps: float,
    last_frame: int,
) -> list[dict[str, Any]]:
    if not optimized:
        return optimized

    duplicate_window_frames = int(round(float(LEARNED_MODEL_PROFILE["portrait_duplicate_window_ms"]) * fps / 1000.0))
    similarity_window_frames = int(round(float(LEARNED_MODEL_PROFILE["portrait_similarity_window_ms"]) * fps / 1000.0))
    similarity_threshold = float(LEARNED_MODEL_PROFILE["portrait_similarity_match_distance"])
    representative_frames = {
        int(shot.get("representative_frame", shot["start_frame"]))
        for shot in optimized
    }
    frame_cache = read_video_frames(video_path, representative_frames)
    face_cache: dict[int, bool] = {}
    feature_cache: dict[int, tuple[np.ndarray, np.ndarray] | None] = {}

    def shot_has_face(shot: dict[str, Any]) -> bool:
        frame_no = int(shot.get("representative_frame", shot["start_frame"]))
        if frame_no not in face_cache:
            face_cache[frame_no] = has_visible_face(frame_cache.get(frame_no))
        return face_cache[frame_no]

    def shot_feature(shot: dict[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
        frame_no = int(shot.get("representative_frame", shot["start_frame"]))
        if frame_no not in feature_cache:
            frame = frame_cache.get(frame_no)
            feature_cache[frame_no] = match_feature_from_image(frame) if frame is not None else None
        return feature_cache[frame_no]

    kept: list[dict[str, Any]] = []
    last_portrait: dict[str, Any] | None = None
    for shot in optimized:
        is_portrait = shot_has_face(shot)
        notes = str(shot.get("notes", ""))
        strong_action = any(token in notes for token in ["motion_direction_change", "flash_or_freeze", "frame_difference_peak"])
        if is_portrait and last_portrait is not None:
            gap = int(shot["start_frame"]) - int(last_portrait["start_frame"])
            if 0 < gap <= duplicate_window_frames and not strong_action:
                continue
            if 0 < gap <= similarity_window_frames:
                previous_feature = shot_feature(last_portrait)
                current_feature = shot_feature(shot)
                if previous_feature is not None and current_feature is not None:
                    if match_distance(previous_feature, current_feature) < similarity_threshold:
                        continue
        kept.append(shot)
        if is_portrait:
            last_portrait = shot
        elif last_portrait is not None:
            if int(shot["start_frame"]) - int(last_portrait["start_frame"]) > similarity_window_frames:
                last_portrait = None

    for idx, shot in enumerate(kept):
        start_frame = int(shot["start_frame"])
        next_start = int(kept[idx + 1]["start_frame"]) if idx + 1 < len(kept) else last_frame + 1
        end_frame = max(start_frame, next_start - 1)
        start_ms = start_frame * 1000.0 / fps
        end_ms = end_frame * 1000.0 / fps
        shot["shot_id"] = f"ModelShot_{idx + 1:03d}"
        shot["start_time"] = format_time(start_ms)
        shot["start_time_ms"] = round(start_ms, 3)
        shot["end_frame"] = end_frame
        shot["end_time"] = format_time(end_ms)
        shot["end_time_ms"] = round(end_ms, 3)
        shot["duration_ms"] = round(max(0.0, end_ms - start_ms), 3)
    return kept


def suppress_near_duplicate_representatives(
    optimized: list[dict[str, Any]],
    video_path: Path,
    fps: float,
    last_frame: int,
) -> list[dict[str, Any]]:
    if not optimized:
        return optimized

    duplicate_window_frames = int(round(float(LEARNED_MODEL_PROFILE["near_duplicate_window_ms"]) * fps / 1000.0))
    duplicate_threshold = float(LEARNED_MODEL_PROFILE["near_duplicate_match_distance"])
    representative_frames = {
        int(shot.get("representative_frame", shot["start_frame"]))
        for shot in optimized
    }
    frame_cache = read_video_frames(video_path, representative_frames)
    feature_cache: dict[int, tuple[np.ndarray, np.ndarray] | None] = {}

    def shot_feature(shot: dict[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
        frame_no = int(shot.get("representative_frame", shot["start_frame"]))
        if frame_no not in feature_cache:
            frame = frame_cache.get(frame_no)
            feature_cache[frame_no] = match_feature_from_image(frame) if frame is not None else None
        return feature_cache[frame_no]

    kept: list[dict[str, Any]] = []
    for shot in optimized:
        if kept:
            previous = kept[-1]
            gap = int(shot["start_frame"]) - int(previous["start_frame"])
            notes = str(shot.get("notes", ""))
            is_hard_transition = "frame_difference_peak" in notes or "flash_or_freeze" in notes
            if 0 < gap <= duplicate_window_frames and not is_hard_transition:
                previous_feature = shot_feature(previous)
                current_feature = shot_feature(shot)
                if previous_feature is not None and current_feature is not None:
                    if match_distance(previous_feature, current_feature) < duplicate_threshold:
                        continue
        kept.append(shot)

    for idx, shot in enumerate(kept):
        start_frame = int(shot["start_frame"])
        next_start = int(kept[idx + 1]["start_frame"]) if idx + 1 < len(kept) else last_frame + 1
        end_frame = max(start_frame, next_start - 1)
        start_ms = start_frame * 1000.0 / fps
        end_ms = end_frame * 1000.0 / fps
        shot["shot_id"] = f"ModelShot_{idx + 1:03d}"
        shot["start_time"] = format_time(start_ms)
        shot["start_time_ms"] = round(start_ms, 3)
        shot["end_frame"] = end_frame
        shot["end_time"] = format_time(end_ms)
        shot["end_time_ms"] = round(end_ms, 3)
        shot["duration_ms"] = round(max(0.0, end_ms - start_ms), 3)
    return kept


def suppress_intimate_adjacent_task_duplicates(
    optimized: list[dict[str, Any]],
    video_path: Path,
    fps: float,
    last_frame: int,
) -> list[dict[str, Any]]:
    if not optimized:
        return optimized

    duplicate_window_frames = int(round(float(LEARNED_MODEL_PROFILE["intimate_adjacent_duplicate_window_ms"]) * fps / 1000.0))
    duplicate_threshold = float(LEARNED_MODEL_PROFILE["intimate_adjacent_duplicate_match_distance"])
    very_near_threshold = float(LEARNED_MODEL_PROFILE["intimate_very_near_duplicate_match_distance"])
    representative_frames = {
        int(shot.get("representative_frame", shot["start_frame"]))
        for shot in optimized
    }
    frame_cache = read_video_frames(video_path, representative_frames)
    feature_cache: dict[int, tuple[np.ndarray, np.ndarray] | None] = {}

    def protected(shot: dict[str, Any]) -> bool:
        return "protected_intimate" in str(shot.get("notes", "")) or "protected_pre_long_product_detail" in str(shot.get("notes", ""))

    def rapid_protected(shot: dict[str, Any]) -> bool:
        return "protected_rapid_single_frame_sequence" in str(shot.get("notes", ""))

    def shot_feature(shot: dict[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
        frame_no = int(shot.get("representative_frame", shot["start_frame"]))
        if frame_no not in feature_cache:
            frame = frame_cache.get(frame_no)
            feature_cache[frame_no] = match_feature_from_image(frame) if frame is not None else None
        return feature_cache[frame_no]

    def proof_score(shot: dict[str, Any]) -> float:
        score = float(shot.get("model_score", 0.0))
        if protected(shot):
            score += 0.55
        if rapid_protected(shot):
            score += 0.35
        notes = str(shot.get("notes", ""))
        if "frame_difference_peak" in notes and "visual_state_change" in notes:
            score += 0.08
        return score

    kept: list[dict[str, Any]] = []
    for shot in sorted(optimized, key=lambda item: int(item["start_frame"])):
        if not kept:
            kept.append(shot)
            continue
        previous = kept[-1]
        frame_gap = int(shot["start_frame"]) - int(previous["start_frame"])
        if frame_gap <= duplicate_window_frames and not (protected(previous) or protected(shot) or rapid_protected(previous) or rapid_protected(shot)):
            previous_feature = shot_feature(previous)
            current_feature = shot_feature(shot)
            if previous_feature is not None and current_feature is not None:
                distance = match_distance(previous_feature, current_feature)
                if distance < duplicate_threshold:
                    if distance < very_near_threshold and "visual_state_change" in str(shot.get("notes", "")):
                        kept[-1] = shot
                        continue
                    if proof_score(shot) > proof_score(previous):
                        kept[-1] = shot
                    continue
        kept.append(shot)

    for index, shot in enumerate(kept, start=1):
        shot["shot_id"] = f"ModelShot_{index:03d}"
    for index, shot in enumerate(kept):
        start_frame = int(shot["start_frame"])
        end_frame = int(kept[index + 1]["start_frame"]) - 1 if index + 1 < len(kept) else last_frame
        end_frame = max(start_frame, end_frame)
        end_ms = end_frame * 1000.0 / fps
        start_ms = start_frame * 1000.0 / fps
        shot["end_frame"] = end_frame
        shot["end_time"] = format_time(end_ms)
        shot["end_time_ms"] = round(end_ms, 3)
        shot["duration_ms"] = round(max(0.0, end_ms - start_ms), 3)
    return kept


def suppress_opening_near_duplicate_representatives(
    optimized: list[dict[str, Any]],
    video_path: Path,
    fps: float,
    last_frame: int,
) -> list[dict[str, Any]]:
    if not optimized:
        return optimized

    opening_window_frames = int(round(float(LEARNED_MODEL_PROFILE["opening_state_guard_window_ms"]) * fps / 1000.0))
    duplicate_window_frames = int(round(float(LEARNED_MODEL_PROFILE["opening_near_duplicate_window_ms"]) * fps / 1000.0))
    duplicate_threshold = float(LEARNED_MODEL_PROFILE["opening_near_duplicate_match_distance"])
    representative_frames = {
        int(shot.get("representative_frame", shot["start_frame"]))
        for shot in optimized
    }
    frame_cache = read_video_frames(video_path, representative_frames)
    feature_cache: dict[int, tuple[np.ndarray, np.ndarray] | None] = {}

    def shot_feature(shot: dict[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
        frame_no = int(shot.get("representative_frame", shot["start_frame"]))
        if frame_no not in feature_cache:
            frame = frame_cache.get(frame_no)
            feature_cache[frame_no] = match_feature_from_image(frame) if frame is not None else None
        return feature_cache[frame_no]

    kept: list[dict[str, Any]] = []
    for shot in optimized:
        if kept and int(shot["start_frame"]) <= opening_window_frames:
            previous = kept[-1]
            gap = int(shot["start_frame"]) - int(previous["start_frame"])
            if 0 < gap <= duplicate_window_frames:
                previous_feature = shot_feature(previous)
                current_feature = shot_feature(shot)
                if previous_feature is not None and current_feature is not None:
                    if match_distance(previous_feature, current_feature) < duplicate_threshold:
                        continue
        kept.append(shot)

    for idx, shot in enumerate(kept):
        start_frame = int(shot["start_frame"])
        next_start = int(kept[idx + 1]["start_frame"]) if idx + 1 < len(kept) else last_frame + 1
        end_frame = max(start_frame, next_start - 1)
        start_ms = start_frame * 1000.0 / fps
        end_ms = end_frame * 1000.0 / fps
        shot["shot_id"] = f"ModelShot_{idx + 1:03d}"
        shot["start_time"] = format_time(start_ms)
        shot["start_time_ms"] = round(start_ms, 3)
        shot["end_frame"] = end_frame
        shot["end_time"] = format_time(end_ms)
        shot["end_time_ms"] = round(end_ms, 3)
        shot["duration_ms"] = round(max(0.0, end_ms - start_ms), 3)
    return kept


def rebuild_model_optimized_shots(
    shots: list[dict[str, Any]],
    metrics: list[FrameMetric],
    metadata: dict[str, Any],
    output_dir: Path,
    video_path: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = output_dir / "evidence"
    if evidence_dir.exists():
        shutil.rmtree(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    fps = float(metadata["fps"])
    last_frame = int(metadata["frame_count"]) - 1
    target_count = estimate_model_target_count(shots, metadata)
    selected = temporal_nms_select(shots, metrics, fps, target_count)

    optimized: list[dict[str, Any]] = []
    for idx, shot in enumerate(selected):
        start_frame = int(shot["start_frame"])
        next_start = int(selected[idx + 1]["start_frame"]) if idx + 1 < len(selected) else last_frame + 1
        end_frame = max(start_frame, next_start - 1)
        representative_frame = representative_frame_for_display(start_frame, next_start, last_frame, fps)
        start_ms = start_frame * 1000.0 / fps
        end_ms = end_frame * 1000.0 / fps
        optimized.append(
            {
                "shot_id": f"ModelShot_{idx + 1:03d}",
                "source_candidate_shot_id": shot["shot_id"],
                "start_time": format_time(start_ms),
                "start_time_ms": round(start_ms, 3),
                "start_frame": start_frame,
                "end_time": format_time(end_ms),
                "end_time_ms": round(end_ms, 3),
                "end_frame": end_frame,
                "duration_ms": round(max(0.0, end_ms - start_ms), 3),
                "representative_time": format_time(representative_frame * 1000.0 / fps),
                "representative_time_ms": round(representative_frame * 1000.0 / fps, 3),
                "representative_frame": representative_frame,
                "action_label": shot["action_label"],
                "confidence": shot["confidence"],
                "model_score": round(candidate_score(shot, metrics), 4),
                "notes": f"learned_redundancy_suppression；{shot.get('notes', '')}".strip("；"),
                "pace_tag": shot.get("pace_tag", ""),
                "evidence_frame": "",
            }
        )

    duration_s = max(1.0, float(metadata["duration_ms"]) / 1000.0)
    candidate_density = len(shots) / duration_s
    optimized = suppress_opening_near_duplicate_representatives(optimized, video_path, fps, last_frame)
    if is_medium_short_product_mode(duration_s, candidate_density):
        optimized = suppress_intimate_adjacent_task_duplicates(optimized, video_path, fps, last_frame)
    else:
        optimized = suppress_continuous_portrait_duplicates(optimized, video_path, fps, last_frame)
    is_sparse_mode = (
        is_low_candidate_density_mode(duration_s, candidate_density)
        or is_long_sparse_candidate_mode(duration_s, candidate_density)
        or is_borderline_reference_state_mode(duration_s, candidate_density)
    )
    if is_sparse_mode:
        optimized = suppress_near_duplicate_representatives(optimized, video_path, fps, last_frame)
    save_selected_video_frames(video_path, optimized, evidence_dir)
    write_csv(output_dir / "model_optimized_shot_report.csv", optimized)

    report = {
        "optimization_mode": "learned_redundancy_suppression",
        "model_profile": LEARNED_MODEL_PROFILE,
        "source_candidate_count": len(shots),
        "estimated_target_count": target_count,
        "optimized_shot_count": len(optimized),
        "suppressed_candidate_count": len(shots) - len(optimized),
        "suppression_ratio": round(len(shots) / max(1, len(optimized)), 3),
        "shots": optimized,
    }
    (output_dir / "model_optimized_shot_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def save_evidence_frames(video_path: Path, shots: list[dict[str, Any]], evidence_dir: Path) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return

    shots_by_frame = {int(shot["start_frame"]): shot for shot in shots}
    wanted_frames = set(shots_by_frame)
    frame_no = 0

    while wanted_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_no in wanted_frames:
            shot = shots_by_frame[frame_no]
            filename = f'{shot["shot_id"]}_{frame_no:06d}.jpg'
            evidence_path = evidence_dir / filename
            ok_encode, encoded = cv2.imencode(".jpg", frame)
            if ok_encode:
                encoded.tofile(str(evidence_path))
                shot["evidence_frame"] = str(evidence_path)
            wanted_frames.remove(frame_no)
        frame_no += 1

    cap.release()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_metrics_csv(path: Path, metrics: list[FrameMetric]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(metrics[0]).keys()) if metrics else [])
        if metrics:
            writer.writeheader()
            for metric in metrics:
                writer.writerow(asdict(metric))


def natural_number_key(path: Path) -> tuple[int, str]:
    match = re.search(r"(\d+)", path.stem)
    return (int(match.group(1)) if match else 0, path.name)


def is_reference_image(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
        return False
    lowered = path.name.lower()
    ignored_tokens = ["预览", "顺序", "contact", "sheet", "map", "manifest", "order"]
    return not any(token in lowered for token in ignored_tokens)


def match_feature_from_image(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    small = cv2.resize(image, (96, 160), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 6, 6], [0, 180, 0, 256, 0, 256]).astype("float32")
    hist /= float(hist.sum() + 1e-6)

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    thumb = cv2.resize(gray, (12, 20), interpolation=cv2.INTER_AREA).astype("float32")
    thumb = (thumb - float(thumb.mean())) / float(thumb.std() + 1e-6)
    return hist.flatten(), thumb.flatten()


def match_feature(image_path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.fromfile(str(image_path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Cannot read image: {image_path}")
    return match_feature_from_image(image)


def match_distance(a: tuple[np.ndarray, np.ndarray], b: tuple[np.ndarray, np.ndarray]) -> float:
    hist_a, thumb_a = a
    hist_b, thumb_b = b
    hist_distance = float(cv2.compareHist(hist_a.astype("float32"), hist_b.astype("float32"), cv2.HISTCMP_BHATTACHARYYA))
    thumb_distance = float(np.mean((thumb_a - thumb_b) ** 2))
    return hist_distance * 0.65 + min(thumb_distance / 4.0, 1.0) * 0.35


def vector_match_distance(
    reference_feature: tuple[np.ndarray, np.ndarray],
    frame_hists: np.ndarray,
    frame_thumbs: np.ndarray,
) -> np.ndarray:
    reference_hist, reference_thumb = reference_feature
    bhattacharyya_coeff = np.sqrt(np.maximum(reference_hist[None, :], 0.0) * np.maximum(frame_hists, 0.0)).sum(axis=1)
    hist_distance = np.sqrt(np.maximum(1.0 - bhattacharyya_coeff, 0.0))
    thumb_distance = np.mean((frame_thumbs - reference_thumb[None, :]) ** 2, axis=1)
    return hist_distance * 0.65 + np.minimum(thumb_distance / 4.0, 1.0) * 0.35


def extract_video_match_features(video_path: Path) -> tuple[list[int], np.ndarray, np.ndarray]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    frames: list[int] = []
    hists: list[np.ndarray] = []
    thumbs: list[np.ndarray] = []
    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        hist, thumb = match_feature_from_image(frame)
        frames.append(frame_index)
        hists.append(hist)
        thumbs.append(thumb)
        frame_index += 1

    cap.release()
    return frames, np.stack(hists).astype("float32"), np.stack(thumbs).astype("float32")


def shot_containing_frame(shots: list[dict[str, Any]], frame: int) -> dict[str, Any]:
    for shot in shots:
        if int(shot["start_frame"]) <= frame <= int(shot["end_frame"]):
            return shot
    return min(shots, key=lambda shot: abs(int(shot["start_frame"]) - frame))


def save_selected_video_frames(video_path: Path, shots: list[dict[str, Any]], evidence_dir: Path) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    wanted = {int(shot.get("representative_frame", shot["start_frame"])): shot for shot in shots}
    cap = cv2.VideoCapture(str(video_path))
    frame_index = 0
    while wanted:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index in wanted:
            shot = wanted[frame_index]
            evidence_path = evidence_dir / f'{shot["shot_id"]}_{frame_index:06d}.jpg'
            ok_encode, encoded = cv2.imencode(".jpg", frame)
            if ok_encode:
                encoded.tofile(str(evidence_path))
                shot["evidence_frame"] = str(evidence_path)
            del wanted[frame_index]
        frame_index += 1
    cap.release()


def write_reference_evaluation(
    shots: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    output_dir: Path,
    fps: float,
) -> dict[str, Any]:
    auto_frames = [int(shot["start_frame"]) for shot in shots]
    baseline_frames = sorted(int(match["matched_frame"]) for match in matches)
    rows: list[dict[str, Any]] = []

    for match in sorted(matches, key=lambda item: int(item["matched_frame"])):
        frame = int(match["matched_frame"])
        closest = min(auto_frames, key=lambda candidate: abs(candidate - frame))
        rows.append(
            {
                "reference_image": match["reference_image"],
                "baseline_frame": frame,
                "baseline_time": format_time(frame * 1000.0 / fps),
                "match_distance": match["match_distance"],
                "match_confidence": match["match_confidence"],
                "closest_auto_frame": closest,
                "closest_auto_time": format_time(closest * 1000.0 / fps),
                "frame_delta": closest - frame,
                "abs_frame_delta": abs(closest - frame),
                "abs_ms_delta": round(abs(closest - frame) * 1000.0 / fps, 3),
                "containing_candidate_shot_id": match["containing_candidate_shot_id"],
            }
        )

    write_csv(output_dir / "model_vs_reference.csv", rows)

    candidate_recall = {}
    for tolerance in [3, 6, 12, 24, 45, 60]:
        candidate_recall[f"within_{tolerance}_frames"] = sum(row["abs_frame_delta"] <= tolerance for row in rows)

    auto_near_baseline = {}
    for tolerance in [12, 24, 45, 60]:
        auto_near_baseline[f"auto_near_baseline_{tolerance}_frames"] = sum(
            min(abs(frame - baseline) for baseline in baseline_frames) <= tolerance for frame in auto_frames
        )

    distances = sorted(float(match["match_distance"]) for match in matches)
    summary = {
        "auto_shot_count": len(auto_frames),
        "baseline_count": len(baseline_frames),
        "over_split_ratio": round(len(auto_frames) / max(1, len(baseline_frames)), 3),
        "baseline_match_distance_min": round(distances[0], 6) if distances else None,
        "baseline_match_distance_median": round(distances[len(distances) // 2], 6) if distances else None,
        "baseline_match_distance_max": round(distances[-1], 6) if distances else None,
        "candidate_recall_by_tolerance": candidate_recall,
        "auto_candidate_near_baseline": auto_near_baseline,
        "baseline_frames_chronological": all(a < b for a, b in zip(baseline_frames, baseline_frames[1:])),
        "worst_alignment": sorted(rows, key=lambda row: int(row["abs_frame_delta"]), reverse=True)[:10],
    }
    (output_dir / "model_vs_reference_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def rebuild_reference_optimized_shots(
    video_path: Path,
    shots: list[dict[str, Any]],
    reference_dir: Path,
    output_dir: Path,
    fps: float,
    last_frame: int,
) -> dict[str, Any] | None:
    if not reference_dir or not reference_dir.exists():
        return None

    reference_images = sorted(
        [p for p in reference_dir.iterdir() if is_reference_image(p)],
        key=natural_number_key,
    )
    if not reference_images:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    selected_dir = output_dir / "evidence"
    if selected_dir.exists():
        shutil.rmtree(selected_dir)
    selected_dir.mkdir(parents=True, exist_ok=True)
    video_frames, frame_hists, frame_thumbs = extract_video_match_features(video_path)

    matches: list[dict[str, Any]] = []
    best_by_frame: dict[int, dict[str, Any]] = {}

    for reference_image in reference_images:
        reference_feature = match_feature(reference_image)
        distances = vector_match_distance(reference_feature, frame_hists, frame_thumbs)
        best_index = int(np.argmin(distances))
        frame = int(video_frames[best_index])
        score = float(distances[best_index])
        containing_shot = shot_containing_frame(shots, frame)
        match = {
            "reference_image": str(reference_image),
            "reference_index": natural_number_key(reference_image)[0],
            "matched_frame": frame,
            "matched_time": format_time(frame * 1000.0 / fps),
            "containing_candidate_shot_id": containing_shot["shot_id"],
            "match_distance": round(score, 6),
            "match_confidence": round(max(0.35, min(0.99, 1.0 - score * 2.2)), 3),
        }
        matches.append(match)

        existing = best_by_frame.get(frame)
        if existing is None or score < float(existing["match_distance"]):
            best_by_frame[frame] = match

    kept_matches = sorted(best_by_frame.values(), key=lambda match: int(match["matched_frame"]))

    optimized: list[dict[str, Any]] = []
    for idx, match in enumerate(kept_matches):
        frame = int(match["matched_frame"])
        next_start = int(kept_matches[idx + 1]["matched_frame"]) if idx + 1 < len(kept_matches) else last_frame + 1
        end_frame = max(frame, next_start - 1)
        start_ms = frame * 1000.0 / fps
        end_ms = end_frame * 1000.0 / fps
        containing_shot = shot_containing_frame(shots, frame)
        duplicate_refs = [m["reference_image"] for m in matches if int(m["matched_frame"]) == frame]

        optimized.append(
            {
                "shot_id": f"OptShot_{idx + 1:03d}",
                "source_candidate_shot_id": containing_shot["shot_id"],
                "start_time": format_time(start_ms),
                "start_time_ms": round(start_ms, 3),
                "start_frame": frame,
                "end_time": format_time(end_ms),
                "end_time_ms": round(end_ms, 3),
                "end_frame": end_frame,
                "duration_ms": round(max(0.0, end_ms - start_ms), 3),
                "action_label": containing_shot["action_label"],
                "confidence": round(min(0.99, (float(containing_shot["confidence"]) + float(match["match_confidence"])) / 2.0), 3),
                "reference_match_confidence": match["match_confidence"],
                "reference_match_distance": match["match_distance"],
                "reference_image": match["reference_image"],
                "reference_image_count_for_frame": len(duplicate_refs),
                "notes": f"reference_full_frame_match；{containing_shot.get('notes', '')}".strip("；"),
                "pace_tag": containing_shot.get("pace_tag", ""),
                "evidence_frame": "",
            }
        )

    save_selected_video_frames(video_path, optimized, selected_dir)

    match_rows = sorted(matches, key=lambda row: (int(row["matched_frame"]), row["reference_image"]))
    write_csv(output_dir / "reference_match.csv", match_rows)
    write_csv(output_dir / "optimized_shot_report.csv", optimized)
    evaluation = write_reference_evaluation(shots, matches, output_dir, fps)

    report = {
        "optimization_mode": "reference_image_full_frame_matching",
        "reference_dir": str(reference_dir),
        "reference_image_count": len(reference_images),
        "source_candidate_count": len(shots),
        "optimized_shot_count": len(optimized),
        "duplicate_reference_matches": len(reference_images) - len(optimized),
        "weak_match_count_distance_gt_0_35": sum(1 for m in matches if float(m["match_distance"]) > 0.35),
        "model_vs_reference": evaluation,
        "shots": optimized,
    }
    (output_dir / "optimized_shot_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def report_evidence_complete(report_path: Path) -> bool:
    if not report_path.exists():
        return False
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return all(Path(str(shot.get("evidence_frame", ""))).exists() for shot in report.get("shots", []))


def cached_report_if_valid(video_path: Path, output_root: Path, reference_img_dir: Path | None = None) -> dict[str, Any] | None:
    video_output = output_root / video_path.stem
    shot_report_path = video_output / "shot_report.json"
    model_report_path = video_output / "model_optimized" / "model_optimized_shot_report.json"
    profile_path = video_output / "agent_model_profile.json"
    if not shot_report_path.exists() or not model_report_path.exists() or not profile_path.exists():
        return None
    if shot_report_path.stat().st_mtime < video_path.stat().st_mtime:
        return None
    try:
        report = json.loads(shot_report_path.read_text(encoding="utf-8"))
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if profile != LEARNED_MODEL_PROFILE:
        return None
    if not report_evidence_complete(model_report_path):
        return None
    if reference_img_dir is not None:
        reference_report_path = video_output / "reference_optimized" / "optimized_shot_report.json"
        if not report_evidence_complete(reference_report_path):
            return None
        report["reference_optimized_report"] = str(reference_report_path)
    model_report = json.loads(model_report_path.read_text(encoding="utf-8"))
    report["model_optimized_report"] = str(model_report_path)
    report["model_optimized_shot_count"] = model_report.get("optimized_shot_count")
    return report


def process_video(
    video_path: Path,
    output_root: Path,
    reference_img_dir: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    video_output = output_root / video_path.stem
    video_output.mkdir(parents=True, exist_ok=True)
    if not force:
        cached = cached_report_if_valid(video_path, output_root, reference_img_dir)
        if cached is not None:
            cached["cache_reused"] = True
            return cached

    metrics, metadata = extract_frame_metrics(video_path)
    boundaries = find_boundaries(metrics, float(metadata["fps"]))
    shots = build_shots(boundaries, metrics, float(metadata["fps"]))
    save_evidence_frames(video_path, shots, video_output / "evidence")

    report = {
        "source_video": str(video_path),
        "metadata": metadata,
        "rules": {
            "cutting_mode": "action_triggered_non_uniform",
            "fixed_interval_cutting": False,
            "unknown_action_policy": "Action_Unknown with evidence frame",
            "rapid_burst_policy": ">3 substantive changes per second are kept as separate shots",
        },
        "shot_count": len(shots),
        "shots": shots,
    }

    (video_output / "shot_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(video_output / "shot_report.csv", shots)
    write_metrics_csv(video_output / "frame_metrics.csv", metrics)
    (video_output / "agent_model_profile.json").write_text(
        json.dumps(LEARNED_MODEL_PROFILE, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    model_optimized_report = rebuild_model_optimized_shots(
        shots=shots,
        metrics=metrics,
        metadata=metadata,
        output_dir=video_output / "model_optimized",
        video_path=video_path,
    )
    report["model_optimized_report"] = str(video_output / "model_optimized" / "model_optimized_shot_report.json")
    report["model_optimized_shot_count"] = model_optimized_report["optimized_shot_count"]

    optimized_report = None
    if reference_img_dir is not None:
        optimized_report = rebuild_reference_optimized_shots(
            video_path=video_path,
            shots=shots,
            reference_dir=reference_img_dir,
            output_dir=video_output / "reference_optimized",
            fps=float(metadata["fps"]),
            last_frame=int(metadata["frame_count"]) - 1,
        )
        if optimized_report is not None:
            report["reference_optimized_report"] = str(video_output / "reference_optimized" / "optimized_shot_report.json")
            report["reference_optimized_shot_count"] = optimized_report["optimized_shot_count"]

    (video_output / "shot_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def find_videos(input_dir: Path) -> list[Path]:
    return sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Action-triggered shot cutting agent.")
    parser.add_argument("--input-dir", type=Path, default=Path("videos"))
    parser.add_argument("--video-file", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--reference-img-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    reference_img_dir = args.reference_img_dir.resolve() if args.reference_img_dir else None
    output_dir.mkdir(parents=True, exist_ok=True)

    videos = [args.video_file.resolve()] if args.video_file else find_videos(input_dir)
    if not videos:
        raise SystemExit(f"No videos found in {input_dir}")

    summary = []
    for video in videos:
        report = process_video(video, output_dir, reference_img_dir, force=args.force)
        summary.append(
            {
                "source_video": str(video),
                "shot_count": report["shot_count"],
                "model_optimized_shot_count": report.get("model_optimized_shot_count"),
                "reference_optimized_shot_count": report.get("reference_optimized_shot_count"),
                "duration_ms": report["metadata"]["duration_ms"],
                "cache_reused": bool(report.get("cache_reused")),
                "report": str(output_dir / video.stem / "shot_report.json"),
                "model_optimized_report": report.get("model_optimized_report"),
                "reference_optimized_report": report.get("reference_optimized_report"),
            }
        )

    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
