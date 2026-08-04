#!/usr/bin/env python3
"""比较两版 CARLA 多 seed 聚合结果。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METRICS = (
    ("route_completion_mean", "Route", True),
    ("collision_run_rate", "Collision", True),
    ("safe_stop_run_rate", "Safe stop", True),
    ("lane_invasions_mean", "Lane", False),
    ("fallback_rate_mean", "Fallback", True),
    ("hard_brake_rate_mean", "Hard brake", True),
    ("latency_mean_s", "Latency(s)", False),
    ("minimum_ttc_mean_s", "Min TTC(s)", False),
)


def load_aggregate(path: Path) -> dict[str, Any]:
    """读取汇总 JSON，并兼容顶层就是 aggregate 的旧文件。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("aggregate", data)


def format_value(value: float | None, percentage: bool) -> str:
    """格式化可空指标。"""
    if value is None:
        return "-"
    return f"{100.0 * value:.2f}%" if percentage else f"{value:.2f}"


def build_report(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    baseline_name: str,
    candidate_name: str,
) -> str:
    """按共同场景生成同口径比较表。"""
    common = sorted(set(baseline["scenarios"]) & set(candidate["scenarios"]))
    lines = [
        "# CARLA 版本对照",
        "",
        f"- Baseline：`{baseline_name}`，运行 {baseline['run_count']} 次",
        f"- Candidate：`{candidate_name}`，运行 {candidate['run_count']} 次",
        f"- 共同场景：{len(common)}",
        "",
    ]
    for scenario in common:
        before = baseline["scenarios"][scenario]
        after = candidate["scenarios"][scenario]
        lines.extend(
            [
                f"## {scenario}",
                "",
                "| Metric | Baseline | Candidate | Delta |",
                "|---|---:|---:|---:|",
            ]
        )
        for key, label, percentage in METRICS:
            old_value = before.get(key)
            new_value = after.get(key)
            delta = (
                float(new_value) - float(old_value)
                if old_value is not None and new_value is not None
                else None
            )
            lines.append(
                f"| {label} | {format_value(old_value, percentage)} | "
                f"{format_value(new_value, percentage)} | {format_value(delta, percentage)} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--baseline-name", default="v5")
    parser.add_argument("--candidate-name", default="v6")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = build_report(
        load_aggregate(Path(args.baseline)),
        load_aggregate(Path(args.candidate)),
        args.baseline_name,
        args.candidate_name,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"对照报告：{output}")


if __name__ == "__main__":
    main()
