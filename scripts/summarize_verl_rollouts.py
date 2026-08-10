#!/usr/bin/env python3
"""汇总 VERL rollout 中可直接验证的奖励与轨迹指标。"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


METRICS = ("score", "parse_success", "ade", "fde", "speed_error", "reward_penalty")


def mean(rows: list[dict], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return statistics.fmean(values) if values else 0.0


def summarize(rollout_dir: Path) -> dict:
    by_step: dict[int, list[dict]] = defaultdict(list)
    for path in sorted(rollout_dir.glob("*.jsonl"), key=lambda item: int(item.stem)):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                by_step[int(row["step"])].append(row)

    if not by_step:
        raise ValueError(f"没有找到 rollout JSONL：{rollout_dir}")

    steps = []
    for step, rows in sorted(by_step.items()):
        item = {"step": step, "samples": len(rows)}
        item.update({key: mean(rows, key) for key in METRICS})
        steps.append(item)

    all_rows = [row for rows in by_step.values() for row in rows]
    return {
        "rollout_dir": str(rollout_dir.resolve()),
        "steps": steps,
        "overall": {"samples": len(all_rows), **{key: mean(all_rows, key) for key in METRICS}},
    }


def write_report(summary: dict, output_prefix: Path) -> None:
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    output_prefix.with_suffix(".json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# VERL GRPO 短训 rollout 汇总",
        "",
        "| Step | Samples | Reward | Parse | ADE (m) | FDE (m) | Speed Error (m/s) | Penalty |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["steps"]:
        lines.append(
            f"| {row['step']} | {row['samples']} | {row['score']:.4f} | "
            f"{row['parse_success']:.2%} | {row['ade']:.4f} | {row['fde']:.4f} | "
            f"{row['speed_error']:.4f} | {row['reward_penalty']:.4f} |"
        )
    overall = summary["overall"]
    lines.extend(
        [
            "",
            "## 总体",
            "",
            f"- rollout 数：{overall['samples']}",
            f"- 平均奖励：{overall['score']:.4f}",
            f"- 解析成功率：{overall['parse_success']:.2%}",
            f"- 平均 ADE/FDE：{overall['ade']:.4f} m / {overall['fde']:.4f} m",
            f"- 平均速度误差：{overall['speed_error']:.4f} m/s",
            "",
            "> 这些是训练时采样指标，不是冻结验证集上的 SFT/GRPO 效果对比。",
        ]
    )
    output_prefix.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollout-dir", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = summarize(args.rollout_dir)
    write_report(result, args.output_prefix)
    print(json.dumps(result["overall"], ensure_ascii=False, indent=2))
