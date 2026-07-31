#!/usr/bin/env python3
"""把冻结 SFT 模型预测转换为 DriveVLA 多模态 DPO 偏好数据。

chosen 使用训练集中的真实结构化答案，rejected 使用冻结 SFT 模型输出。脚本会
自动计算格式、动作、ADE/FDE 和转弯几何误差，只保留具有明确质量差距的样本。

重要边界：
    这个脚本必须处理 SFT train split 的预测。传入最终验证集后，脚本会按
    sample ID 和 scene token 双重检查，发现泄漏立即停止。
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from evaluate_drivevla import displacement_errors
from parse_outputs import parse_model_output
from sample_dpo_candidates import (
    action_name,
    assert_no_final_validation_leakage,
    load_jsonl,
    sample_id,
    scene_id,
)


TURN_ACTIONS = {"TURN_LEFT", "TURN_RIGHT"}
ACTION_ERROR_CATEGORIES = {
    "slow_keep_confusion",
    "stop_confusion",
    "turn_action_error",
    "other_action_error",
}


def save_json(path: Path, data: Any) -> None:
    """保存 UTF-8 格式化 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def endpoint_heading_error(
    ground_truth: list[list[float]],
    prediction: list[list[float]],
) -> float:
    """计算终点方向角绝对误差，单位为度。"""
    gt_forward, gt_lateral = ground_truth[-1]
    pred_forward, pred_lateral = prediction[-1]
    gt_heading = math.degrees(math.atan2(gt_lateral, gt_forward))
    pred_heading = math.degrees(math.atan2(pred_lateral, pred_forward))
    delta = (pred_heading - gt_heading + 180.0) % 360.0 - 180.0
    return abs(delta)


def score_prediction(
    ground_truth: dict[str, Any],
    prediction_text: str,
) -> dict[str, Any]:
    """给一条 rejected 候选打确定性质量分，并返回筛选所需诊断字段。

    分数只用于选择偏好对，不直接作为 DPO loss。轨迹和动作占主要权重，Risk
    只有 0.05 权重，因为它来自启发式弱标签。
    """
    parsed = parse_model_output(prediction_text)
    action_correct = parsed.get("action") == ground_truth.get("action")
    risk_correct = parsed.get("risk") == ground_truth.get("risk")
    trajectory_valid = bool(parsed.get("trajectory_valid"))

    ade: float | None = None
    fde: float | None = None
    heading_error: float | None = None
    lateral_error: float | None = None
    gt_trajectory = ground_truth.get("trajectory")
    pred_trajectory = parsed.get("trajectory")
    if (
        isinstance(gt_trajectory, list)
        and isinstance(pred_trajectory, list)
        and len(gt_trajectory) == len(pred_trajectory) == 6
    ):
        ade, fde = displacement_errors(gt_trajectory, pred_trajectory)
        lateral_error = abs(pred_trajectory[-1][1] - gt_trajectory[-1][1])
        if ground_truth.get("action") in TURN_ACTIONS:
            heading_error = endpoint_heading_error(gt_trajectory, pred_trajectory)

    format_score = 1.0 if parsed.get("parse_success") else 0.0
    action_score = 1.0 if action_correct else 0.0
    risk_score = 1.0 if risk_correct else 0.0
    ade_score = math.exp(-ade / 1.5) if ade is not None else 0.0
    fde_score = math.exp(-fde / 3.0) if fde is not None else 0.0
    if heading_error is not None:
        geometry_score = math.exp(-heading_error / 5.0)
    elif lateral_error is not None:
        geometry_score = math.exp(-lateral_error / 1.0)
    else:
        geometry_score = 0.0

    score = (
        0.10 * format_score
        + 0.25 * action_score
        + 0.05 * risk_score
        + 0.25 * ade_score
        + 0.20 * fde_score
        + 0.15 * geometry_score
    )
    return {
        "score": score,
        "margin": 1.0 - score,
        "parsed": parsed,
        "action_correct": action_correct,
        "risk_correct": risk_correct,
        "trajectory_valid": trajectory_valid,
        "ade": ade,
        "fde": fde,
        "heading_error_deg": heading_error,
        "final_lateral_error_m": lateral_error,
    }


def classify_pair(ground_truth: dict[str, Any], diagnostics: dict[str, Any]) -> str | None:
    """把偏好对归入主要失败类型，便于分层统计与限额。"""
    parsed = diagnostics["parsed"]
    gt_action = str(ground_truth.get("action", "UNKNOWN"))
    pred_action = str(parsed.get("action", "UNKNOWN"))

    if not parsed.get("parse_success"):
        return "invalid_output"
    if {gt_action, pred_action} == {"KEEP_LANE", "SLOW_DOWN"}:
        return "slow_keep_confusion"
    if (gt_action == "STOP") != (pred_action == "STOP"):
        return "stop_confusion"
    if gt_action in TURN_ACTIONS and not diagnostics["action_correct"]:
        return "turn_action_error"
    if not diagnostics["action_correct"]:
        return "other_action_error"
    if gt_action in TURN_ACTIONS and (
        (diagnostics["heading_error_deg"] or 0.0) >= 2.0
        or (diagnostics["final_lateral_error_m"] or 0.0) >= 0.5
    ):
        return "turn_geometry"
    if (diagnostics["ade"] or 0.0) >= 0.5 or (diagnostics["fde"] or 0.0) >= 1.0:
        return "trajectory_error"
    if not diagnostics["risk_correct"]:
        return "risk_only"
    return None


def get_chosen_text(source_row: dict[str, Any]) -> str:
    """优先复用原 assistant JSON，确保 chosen 与 SFT 数据格式一致。"""
    messages = source_row.get("messages", [])
    if len(messages) >= 2:
        content = messages[1].get("content")
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    return str(item.get("text", ""))
        if isinstance(content, str):
            return content
    return json.dumps(source_row.get("ground_truth", {}), ensure_ascii=False)


def get_prompt_text(source_row: dict[str, Any]) -> str:
    """把项目原始多模态消息转换为 LLaMA-Factory 的 <image> 文本格式。"""
    messages = source_row.get("messages", [])
    if not messages:
        raise ValueError(f"样本 {sample_id(source_row)} 缺少 messages")
    content = messages[0].get("content")
    if isinstance(content, str):
        return content if "<image>" in content else f"<image>{content}"
    if isinstance(content, list):
        text = next(
            (str(item.get("text", "")) for item in content if item.get("type") == "text"),
            "",
        )
        return f"<image>{text}"
    raise ValueError(f"样本 {sample_id(source_row)} 的 user content 格式不支持")


def build_rejected_text(
    ground_truth: dict[str, Any],
    prediction_row: dict[str, Any],
    diagnostics: dict[str, Any],
    category: str,
    rejected_mode: str,
) -> tuple[str, str]:
    """构造 rejected，并返回本条 pair 被隔离修改的字段。

    ``model_output`` 完整保留冻结 SFT 的原始输出，用于复现第一轮 pilot。
    ``isolated_error`` 只把当前失败类别对应的字段替换为 SFT 错误预测。这样
    chosen/rejected 的差异更局部，DPO 更容易判断应该修正 action 还是 trajectory。
    """
    raw_prediction = str(prediction_row.get("prediction", ""))
    if rejected_mode == "model_output" or category == "invalid_output":
        return raw_prediction, "full_output"

    rejected = dict(ground_truth)
    parsed = diagnostics["parsed"]
    if category in ACTION_ERROR_CATEGORIES:
        predicted_action = parsed.get("action")
        if isinstance(predicted_action, str) and predicted_action:
            rejected["action"] = predicted_action
            return json.dumps(rejected, ensure_ascii=False), "action"
    elif category in {"turn_geometry", "trajectory_error"}:
        predicted_trajectory = parsed.get("trajectory")
        if (
            isinstance(predicted_trajectory, list)
            and len(predicted_trajectory) == 6
        ):
            rejected["trajectory"] = predicted_trajectory
            return json.dumps(rejected, ensure_ascii=False), "trajectory"
    elif category == "risk_only":
        predicted_risk = parsed.get("risk")
        if isinstance(predicted_risk, str) and predicted_risk:
            rejected["risk"] = predicted_risk
            return json.dumps(rejected, ensure_ascii=False), "risk"

    # 理论上分类条件已经保证对应字段存在；保留回退可避免脏数据中断全量构建。
    return raw_prediction, "full_output_fallback"


def make_preference_row(
    source_row: dict[str, Any],
    prediction_row: dict[str, Any],
    diagnostics: dict[str, Any],
    category: str,
    rejected_mode: str,
) -> dict[str, Any]:
    """构造 LLaMA-Factory ShareGPT 多模态 preference 样本。"""
    image = str(source_row.get("image") or prediction_row.get("image") or "")
    ground_truth = source_row.get("ground_truth", {})
    rejected_text, isolated_field = build_rejected_text(
        ground_truth,
        prediction_row,
        diagnostics,
        category,
        rejected_mode,
    )
    return {
        "id": sample_id(source_row),
        "messages": [{"role": "user", "content": get_prompt_text(source_row)}],
        "chosen": {"role": "assistant", "content": get_chosen_text(source_row)},
        "rejected": {
            "role": "assistant",
            "content": rejected_text,
        },
        "images": [image],
        "metadata": {
            "scene_token": scene_id(source_row),
            "ground_truth_action": action_name(source_row),
            "predicted_action": diagnostics["parsed"].get("action"),
            "category": category,
            "rejected_score": round(diagnostics["score"], 6),
            "preference_margin": round(diagnostics["margin"], 6),
            "ade": diagnostics["ade"],
            "fde": diagnostics["fde"],
            "heading_error_deg": diagnostics["heading_error_deg"],
            "final_lateral_error_m": diagnostics["final_lateral_error_m"],
            "rejected_mode": rejected_mode,
            "isolated_field": isolated_field,
        },
    }


def select_with_category_caps(
    rows: list[dict[str, Any]],
    max_pairs: int,
    max_per_category: dict[str, int],
    seed: int,
) -> list[dict[str, Any]]:
    """按类别限额选择困难样本，类别内部优先保留质量差距更大的 pair。"""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["metadata"]["category"]].append(row)
    for category_rows in grouped.values():
        category_rows.sort(
            key=lambda row: row["metadata"]["preference_margin"],
            reverse=True,
        )

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for category, category_rows in grouped.items():
        cap = max_per_category.get(category, len(category_rows))
        for row in category_rows[:cap]:
            selected.append(row)
            selected_ids.add(row["id"])

    if len(selected) > max_pairs > 0:
        selected.sort(
            key=lambda row: row["metadata"]["preference_margin"],
            reverse=True,
        )
        selected = selected[:max_pairs]
    elif not max_per_category and max_pairs > 0 and len(selected) < max_pairs:
        remaining = [
            row
            for category_rows in grouped.values()
            for row in category_rows
            if row["id"] not in selected_ids
        ]
        remaining.sort(
            key=lambda row: row["metadata"]["preference_margin"],
            reverse=True,
        )
        selected.extend(remaining[: max_pairs - len(selected)])

    random.Random(seed).shuffle(selected)
    return selected


def split_by_scene(
    rows: list[dict[str, Any]],
    val_ratio: float,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按 scene 划分 DPO train/val，避免相邻帧跨集合。"""
    scenes = sorted(
        {str(row["metadata"].get("scene_token", "")) for row in rows} - {""}
    )
    if len(scenes) < 2 or val_ratio <= 0:
        return rows, []
    random_generator = random.Random(seed)
    random_generator.shuffle(scenes)
    val_scene_count = max(1, min(len(scenes) - 1, round(len(scenes) * val_ratio)))
    val_scenes = set(scenes[:val_scene_count])
    train_rows = [
        row for row in rows if row["metadata"].get("scene_token") not in val_scenes
    ]
    val_rows = [
        row for row in rows if row["metadata"].get("scene_token") in val_scenes
    ]
    return train_rows, val_rows


def build_report(
    predictions_count: int,
    eligible_rows: list[dict[str, Any]],
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """汇总偏好数据数量、类别和质量差距。"""
    margins = [
        float(row["metadata"]["preference_margin"]) for row in eligible_rows
    ]
    train_scenes = {
        row["metadata"].get("scene_token") for row in train_rows
    } - {""}
    val_scenes = {
        row["metadata"].get("scene_token") for row in val_rows
    } - {""}
    confusion_counts = Counter(
        (
            f"{row['metadata']['ground_truth_action']}"
            f"->{row['metadata']['predicted_action']}"
        )
        for row in eligible_rows
        if row["metadata"]["ground_truth_action"]
        != row["metadata"]["predicted_action"]
    )
    return {
        "input_predictions": predictions_count,
        "eligible_pairs": len(eligible_rows),
        "train_pairs": len(train_rows),
        "val_pairs": len(val_rows),
        "train_scenes": len(train_scenes),
        "val_scenes": len(val_scenes),
        "scene_overlap": len(train_scenes & val_scenes),
        "category_counts": dict(
            sorted(Counter(row["metadata"]["category"] for row in eligible_rows).items())
        ),
        "ground_truth_action_counts": dict(
            sorted(
                Counter(
                    row["metadata"]["ground_truth_action"] for row in eligible_rows
                ).items()
            )
        ),
        "action_confusion_counts": dict(sorted(confusion_counts.items())),
        "isolated_field_counts": dict(
            sorted(
                Counter(
                    row["metadata"].get("isolated_field", "unknown")
                    for row in eligible_rows
                ).items()
            )
        ),
        "mean_preference_margin": mean(margins) if margins else 0.0,
        "all_images_exist": all(
            Path(row["images"][0]).exists() for row in eligible_rows
        ),
    }


def render_report_markdown(report: dict[str, Any]) -> str:
    """把偏好数据报告渲染成便于人工审阅的 Markdown。"""
    lines = [
        "# DriveVLA DPO 偏好数据报告",
        "",
        f"- 输入预测：{report['input_predictions']}",
        f"- 可用偏好对：{report['eligible_pairs']}",
        f"- 训练 / 验证：{report['train_pairs']} / {report['val_pairs']}",
        f"- 训练 / 验证 scene：{report['train_scenes']} / {report['val_scenes']}",
        f"- scene 交集：{report['scene_overlap']}",
        f"- 图片全部存在：{report['all_images_exist']}",
        f"- 平均偏好间隔：{report['mean_preference_margin']:.4f}",
        "",
        "## 失败类别",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {name} | {count} |"
        for name, count in report["category_counts"].items()
    )
    lines.extend(
        [
            "",
            "## 隔离字段",
            "",
            "| Field | Count |",
            "|---|---:|",
        ]
    )
    lines.extend(
        f"| {name} | {count} |"
        for name, count in report["isolated_field_counts"].items()
    )
    lines.extend(
        [
            "",
            "## 动作混淆",
            "",
            "| Ground Truth -> Prediction | Count |",
            "|---|---:|",
        ]
    )
    lines.extend(
        f"| {name} | {count} |"
        for name, count in report["action_confusion_counts"].items()
    )
    return "\n".join(lines) + "\n"


def build_preferences(args: argparse.Namespace) -> dict[str, Any]:
    """加载源数据与预测，生成、筛选并按 scene 划分偏好对。"""
    source_rows = load_jsonl(Path(args.source_data_path))
    prediction_rows = load_jsonl(Path(args.predictions_path))
    if args.forbidden_data_path:
        assert_no_final_validation_leakage(
            source_rows,
            load_jsonl(Path(args.forbidden_data_path)),
        )

    source_by_id = {sample_id(row): row for row in source_rows}
    if len(source_by_id) != len(source_rows):
        raise ValueError("源数据存在空 ID 或重复 ID")

    max_per_category = (
        {str(key): int(value) for key, value in json.loads(args.max_per_category_json).items()}
        if args.max_per_category_json
        else {}
    )
    eligible: list[dict[str, Any]] = []
    missing_source_ids: list[str] = []
    for prediction_row in prediction_rows:
        prediction_id = str(prediction_row.get("sample_id", ""))
        source_row = source_by_id.get(prediction_id)
        if source_row is None:
            missing_source_ids.append(prediction_id)
            continue
        ground_truth = source_row.get("ground_truth", {})
        diagnostics = score_prediction(
            ground_truth,
            str(prediction_row.get("prediction", "")),
        )
        category = classify_pair(ground_truth, diagnostics)
        if category is None or diagnostics["margin"] < args.min_margin:
            continue
        if category == "risk_only" and not args.include_risk_only:
            continue
        eligible.append(
            make_preference_row(
                source_row,
                prediction_row,
                diagnostics,
                category,
                args.rejected_mode,
            )
        )

    if missing_source_ids:
        raise ValueError(
            f"{len(missing_source_ids)} 条预测无法在源数据中找到，例如 {missing_source_ids[:3]}"
        )

    selected = select_with_category_caps(
        eligible,
        args.max_pairs,
        max_per_category,
        args.seed,
    )
    train_rows, val_rows = split_by_scene(selected, args.val_ratio, args.seed)
    if not train_rows:
        raise ValueError("筛选后没有 DPO 训练数据，请降低 --min-margin 或扩大候选集")

    output_dir = Path(args.output_dir)
    save_json(output_dir / "train.json", train_rows)
    save_json(output_dir / "val.json", val_rows)
    save_json(output_dir / "all_preferences.json", selected)
    report = build_report(len(prediction_rows), selected, train_rows, val_rows)
    save_json(output_dir / "preference_report.json", report)
    (output_dir / "preference_report.md").write_text(
        render_report_markdown(report),
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-data-path",
        default="data/drivevla_dpo/candidates.jsonl",
    )
    parser.add_argument(
        "--predictions-path",
        default="results/dpo_candidate_predictions.jsonl",
    )
    parser.add_argument(
        "--forbidden-data-path",
        default="data/nuscenes_vla_sft_trainval_v5_history/val.jsonl",
    )
    parser.add_argument("--output-dir", default="data/drivevla_dpo/preferences")
    parser.add_argument("--min-margin", type=float, default=0.10)
    parser.add_argument("--max-pairs", type=int, default=4000)
    parser.add_argument("--max-per-category-json", default=None)
    parser.add_argument(
        "--rejected-mode",
        choices=("model_output", "isolated_error"),
        default="model_output",
        help="model_output 保留整段预测；isolated_error 只替换当前错误字段。",
    )
    parser.add_argument("--val-ratio", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-risk-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    """命令行入口。"""
    report = build_preferences(parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
