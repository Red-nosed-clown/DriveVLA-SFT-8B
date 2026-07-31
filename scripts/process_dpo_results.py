#!/usr/bin/env python3
"""一键处理 DPO 推理结果并与冻结 SFT baseline 对比。

输入是两个模型在同一最终验证集上的 predictions JSONL。脚本会依次生成：
解析结果、总体评估、失败样本、轨迹几何报告，以及 SFT/DPO 成对对比报告。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_trajectory_geometry import analyze_rows, build_markdown as build_geometry_markdown
from compare_drivevla_models import build_markdown as build_compare_markdown
from compare_drivevla_models import compare_rows
from evaluate_drivevla import build_markdown as build_eval_markdown
from evaluate_drivevla import evaluate_rows
from parse_outputs import load_jsonl, parse_model_output, save_jsonl


def parse_rows(rows: list[dict]) -> list[dict]:
    """给预测行补充 parsed_prediction，不覆盖已有字段。"""
    parsed_rows: list[dict] = []
    for row in rows:
        parsed_row = dict(row)
        if not isinstance(parsed_row.get("parsed_prediction"), dict):
            parsed_row["parsed_prediction"] = parse_model_output(
                str(parsed_row.get("prediction", ""))
            )
        parsed_rows.append(parsed_row)
    return parsed_rows


def save_json(path: Path, data: dict) -> None:
    """保存 UTF-8 格式化 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> None:
    """执行 DPO 单模型评估和 SFT/DPO 对比。"""
    baseline_rows = parse_rows(load_jsonl(Path(args.baseline_path)))
    candidate_rows = parse_rows(load_jsonl(Path(args.candidate_path)))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix

    parsed_path = output_dir / f"{prefix}_parsed.jsonl"
    metrics_path = output_dir / f"{prefix}_metrics.json"
    eval_report_path = output_dir / f"{prefix}_eval_report.md"
    failures_path = output_dir / f"{prefix}_failures.jsonl"
    baseline_geometry_json_path = (
        output_dir / f"{prefix}_sft_trajectory_geometry.json"
    )
    baseline_geometry_md_path = (
        output_dir / f"{prefix}_sft_trajectory_geometry.md"
    )
    geometry_json_path = output_dir / f"{prefix}_trajectory_geometry.json"
    geometry_md_path = output_dir / f"{prefix}_trajectory_geometry.md"
    comparison_json_path = output_dir / f"{prefix}_vs_sft.json"
    comparison_md_path = output_dir / f"{prefix}_vs_sft.md"

    save_jsonl(parsed_path, candidate_rows)
    metrics, failures = evaluate_rows(candidate_rows)
    save_json(metrics_path, metrics)
    eval_report_path.write_text(build_eval_markdown(metrics), encoding="utf-8")
    save_jsonl(failures_path, failures)

    baseline_geometry = analyze_rows(baseline_rows, args.line_like_threshold)
    save_json(baseline_geometry_json_path, baseline_geometry)
    baseline_geometry_md_path.write_text(
        build_geometry_markdown(baseline_geometry),
        encoding="utf-8",
    )

    geometry = analyze_rows(candidate_rows, args.line_like_threshold)
    save_json(geometry_json_path, geometry)
    geometry_md_path.write_text(
        build_geometry_markdown(geometry),
        encoding="utf-8",
    )

    comparison = compare_rows(
        baseline_rows,
        candidate_rows,
        args.ade_tolerance,
    )
    save_json(comparison_json_path, comparison)
    comparison_md_path.write_text(
        build_compare_markdown(comparison),
        encoding="utf-8",
    )

    print(f"DPO 指标：{metrics_path}")
    print(f"DPO 评估报告：{eval_report_path}")
    print(f"SFT 轨迹几何报告：{baseline_geometry_md_path}")
    print(f"轨迹几何报告：{geometry_md_path}")
    print(f"SFT/DPO 对比：{comparison_md_path}")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-path", required=True)
    parser.add_argument("--candidate-path", required=True)
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--prefix", default="trainval_v5_history_dpo_full")
    parser.add_argument("--line-like-threshold", type=float, default=0.05)
    parser.add_argument("--ade-tolerance", type=float, default=0.01)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
