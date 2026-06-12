#!/usr/bin/env python3
"""绘制 DriveVLA 真实轨迹和预测轨迹。

每张输出图左侧显示原始前视图，右侧显示当前自车坐标系下的六点轨迹。
横轴为 lateral，纵轴为 forward，这样图像方向与驾驶视角更直观。
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

# 服务器或受限环境中的 HOME 目录可能不可写。把 Matplotlib 缓存放到 /tmp，
# 避免首次导入时产生权限 warning，同时不影响最终图片的保存位置。
os.environ.setdefault("MPLCONFIGDIR", "/tmp/drivevla_matplotlib")

import matplotlib


matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from evaluate_drivevla import displacement_errors, get_ground_truth
from parse_outputs import load_jsonl, parse_model_output


def safe_file_name(value: Any) -> str:
    """把样本 ID 转成适合作为文件名的字符串。"""
    text = str(value)
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in text)


def visualize_row(row: dict[str, Any], output_path: Path) -> bool:
    """绘制一条有效轨迹样本；轨迹无效时返回 False。"""
    ground_truth = get_ground_truth(row)
    parsed = row.get("parsed_prediction")
    if not isinstance(parsed, dict):
        parsed = parse_model_output(str(row.get("prediction", "")))
    gt_trajectory = ground_truth.get("trajectory")
    pred_trajectory = parsed.get("trajectory")
    if not isinstance(gt_trajectory, list) or not isinstance(pred_trajectory, list):
        return False

    ade, fde = displacement_errors(gt_trajectory, pred_trajectory)
    image = Image.open(row["image"]).convert("RGB")
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].imshow(image)
    axes[0].axis("off")
    axes[0].set_title("CAM_FRONT")

    gt_lateral = [0.0] + [point[1] for point in gt_trajectory]
    gt_forward = [0.0] + [point[0] for point in gt_trajectory]
    pred_lateral = [0.0] + [point[1] for point in pred_trajectory]
    pred_forward = [0.0] + [point[0] for point in pred_trajectory]
    axes[1].plot(gt_lateral, gt_forward, marker="o", label="Ground Truth")
    axes[1].plot(pred_lateral, pred_forward, marker="x", label="Prediction")
    axes[1].scatter([0.0], [0.0], marker="s", color="black", label="Ego")
    axes[1].set_xlabel("Lateral (m)")
    axes[1].set_ylabel("Forward (m)")
    axes[1].set_aspect("equal", adjustable="datalim")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    axes[1].set_title(
        f"Action {ground_truth.get('action')} / {parsed.get('action')}\n"
        f"Risk {ground_truth.get('risk')} / {parsed.get('risk')} | "
        f"ADE {ade:.2f} m | FDE {fde:.2f} m"
    )

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return True


def visualize_file(args: argparse.Namespace) -> None:
    """读取预测文件并生成指定数量的可视化图片。"""
    rows = load_jsonl(Path(args.pred_path))
    output_dir = Path(args.output_dir)
    saved = 0
    for index, row in enumerate(rows):
        sample_id = row.get("sample_id", index)
        output_path = output_dir / f"{index:03d}_{safe_file_name(sample_id)}.png"
        if visualize_row(row, output_path):
            saved += 1
        if saved >= args.num_samples:
            break
    print(f"已保存 {saved} 张轨迹图到 {output_dir}")


def parse_args() -> argparse.Namespace:
    """解析可视化参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--num-samples", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    visualize_file(parse_args())
