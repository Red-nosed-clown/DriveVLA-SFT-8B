#!/usr/bin/env python3
"""计算 DriveVLA 的格式、动作、风险和轨迹指标。

输入：
    已包含 parsed_prediction 的预测 JSONL。

输出：
    机器可读的指标 JSON、适合 README 的 Markdown 报告，以及失败样本 JSONL。

为什么单独实现：
    训练框架只负责优化模型；评估定义由本项目掌握，才能清楚解释 Action
    Accuracy、ADE 和 FDE 的计算口径。
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

try:
    from parse_outputs import load_jsonl, parse_model_output, save_jsonl
except ModuleNotFoundError:  # 作为模块被单元测试导入时使用包内路径。
    from scripts.parse_outputs import load_jsonl, parse_model_output, save_jsonl


def displacement_errors(
    ground_truth: list[list[float]],
    prediction: list[list[float]],
) -> tuple[float, float]:
    """计算一条样本的 ADE 和 FDE。

    ADE 是六个对应轨迹点欧氏距离的平均值；FDE 是最后一个点的欧氏距离。
    """
    distances = [
        math.hypot(pred[0] - gt[0], pred[1] - gt[1])
        for gt, pred in zip(ground_truth, prediction)
    ]
    return mean(distances), distances[-1]


def get_ground_truth(row: dict[str, Any]) -> dict[str, Any]:
    """兼容直接 ground_truth 字典和旧版 assistant JSON 文本。"""
    ground_truth = row.get("ground_truth")
    if isinstance(ground_truth, dict):
        return ground_truth
    if isinstance(ground_truth, str):
        try:
            return json.loads(ground_truth)
        except json.JSONDecodeError:
            return {}
    return {}


def evaluate_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """遍历预测结果并聚合所有指标。"""
    parse_flags: list[bool] = []
    action_flags: list[bool] = []
    risk_flags: list[bool] = []
    trajectory_flags: list[bool] = []
    ades: list[float] = []
    fdes: list[float] = []
    reason_lengths: list[int] = []
    target_speed_errors: list[float] = []
    failures: list[dict[str, Any]] = []

    for row in rows:
        parsed = row.get("parsed_prediction")
        if not isinstance(parsed, dict):
            parsed = parse_model_output(str(row.get("prediction", "")))
            row["parsed_prediction"] = parsed
        ground_truth = get_ground_truth(row)

        parse_flags.append(bool(parsed["parse_success"]))
        action_correct = parsed["action"] == ground_truth.get("action")
        risk_correct = parsed["risk"] == ground_truth.get("risk")
        action_flags.append(action_correct)
        risk_flags.append(risk_correct)
        trajectory_flags.append(bool(parsed["trajectory_valid"]))
        reason_lengths.append(len(parsed.get("reason", "")))

        gt_target_speed = ground_truth.get("target_speed_mps")
        pred_target_speed = parsed.get("target_speed_mps")
        if isinstance(gt_target_speed, (int, float)) and isinstance(
            pred_target_speed, (int, float)
        ):
            target_speed_errors.append(abs(float(pred_target_speed) - float(gt_target_speed)))

        sample_ade: float | None = None
        sample_fde: float | None = None
        gt_trajectory = ground_truth.get("trajectory")
        pred_trajectory = parsed.get("trajectory")
        if isinstance(gt_trajectory, list) and isinstance(pred_trajectory, list):
            sample_ade, sample_fde = displacement_errors(gt_trajectory, pred_trajectory)
            ades.append(sample_ade)
            fdes.append(sample_fde)

        error_types: list[str] = []
        if not parsed["parse_success"]:
            error_types.append("Invalid output format")
        if not action_correct:
            error_types.append("Action error")
        if not risk_correct:
            error_types.append("Risk error")
        if not parsed["trajectory_valid"]:
            error_types.append("Trajectory parse failure")
        if sample_ade is not None and sample_ade >= 5.0:
            error_types.append("Large ADE")
        if sample_fde is not None and sample_fde >= 8.0:
            error_types.append("Large FDE")

        if error_types:
            failures.append(
                {
                    "sample_id": row.get("sample_id"),
                    "image": row.get("image"),
                    "prediction": row.get("prediction"),
                    "ground_truth": ground_truth,
                    "parsed_prediction": parsed,
                    "ade": sample_ade,
                    "fde": sample_fde,
                    "error_types": error_types,
                }
            )

    total = len(rows)
    valid_trajectory_count = len(ades)
    metrics = {
        "model": rows[0].get("model", "unknown") if rows else "unknown",
        "num_samples": total,
        "parse_success_rate": sum(parse_flags) / total if total else 0.0,
        "action_accuracy": sum(action_flags) / total if total else 0.0,
        "risk_accuracy": sum(risk_flags) / total if total else 0.0,
        "trajectory_valid_rate": sum(trajectory_flags) / total if total else 0.0,
        "ade": mean(ades) if ades else None,
        "fde": mean(fdes) if fdes else None,
        "trajectory_metric_samples": valid_trajectory_count,
        "average_reason_length": mean(reason_lengths) if reason_lengths else 0.0,
        "target_speed_valid_rate": len(target_speed_errors) / total if total else 0.0,
        "target_speed_mae_mps": mean(target_speed_errors) if target_speed_errors else None,
        "target_speed_metric_samples": len(target_speed_errors),
        "failure_count": len(failures),
    }
    return metrics, failures


def format_metric(value: Any, percent: bool = False) -> str:
    """把可空指标格式化为 Markdown 文本。"""
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%" if percent else f"{value:.4f}"


def build_markdown(metrics: dict[str, Any]) -> str:
    """生成单模型评估报告。"""
    return "\n".join(
        [
            "# DriveVLA 评估报告",
            "",
            f"- 模型：`{metrics['model']}`",
            f"- 样本数：{metrics['num_samples']}",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Parse Success | {format_metric(metrics['parse_success_rate'], True)} |",
            f"| Action Accuracy | {format_metric(metrics['action_accuracy'], True)} |",
            f"| Risk Accuracy | {format_metric(metrics['risk_accuracy'], True)} |",
            f"| Trajectory Valid | {format_metric(metrics['trajectory_valid_rate'], True)} |",
            f"| ADE | {format_metric(metrics['ade'])} m |",
            f"| FDE | {format_metric(metrics['fde'])} m |",
            f"| Target Speed Valid | {format_metric(metrics['target_speed_valid_rate'], True)} |",
            f"| Target Speed MAE | {format_metric(metrics['target_speed_mae_mps'])} m/s |",
            f"| Average Reason Length | {format_metric(metrics['average_reason_length'])} |",
            "",
            f"- 可计算轨迹误差样本：{metrics['trajectory_metric_samples']}",
            f"- 可计算目标速度误差样本：{metrics['target_speed_metric_samples']}",
            f"- 失败样本：{metrics['failure_count']}",
            "",
        ]
    )


def evaluate_file(args: argparse.Namespace) -> None:
    """读取预测文件、计算指标并写出三类结果。"""
    rows = load_jsonl(Path(args.pred_path))
    metrics, failures = evaluate_rows(rows)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(metrics), encoding="utf-8")
    save_jsonl(Path(args.failure_path), failures)

    print(json.dumps(metrics, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred-path", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--failure-path", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    evaluate_file(parse_args())
