#!/usr/bin/env python3
"""注册 DriveVLA 多模态 chosen/rejected 数据到 LLaMA-Factory。

与 SFT 注册脚本分开，避免误把 preference 数据按普通监督数据读取。
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    """读取 JSON 文件。"""
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    """保存格式化 UTF-8 JSON。"""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def preference_entry(file_name: str) -> dict[str, Any]:
    """创建 LLaMA-Factory 多模态 ShareGPT preference 配置。"""
    return {
        "file_name": file_name,
        "formatting": "sharegpt",
        "ranking": True,
        "columns": {
            "messages": "messages",
            "images": "images",
            "chosen": "chosen",
            "rejected": "rejected",
        },
        "tags": {
            "role_tag": "role",
            "content_tag": "content",
            "user_tag": "user",
            "assistant_tag": "assistant",
        },
    }


def register(args: argparse.Namespace) -> None:
    """复制 train/val preference 数据并更新 dataset_info.json。"""
    source_dir = Path(args.source_dir).resolve()
    factory_data_dir = Path(args.llamafactory_dir).resolve() / "data"
    dataset_info_path = factory_data_dir / "dataset_info.json"

    train_source = source_dir / "train.json"
    val_source = source_dir / "val.json"
    for path in (train_source, val_source, dataset_info_path):
        if not path.exists():
            raise FileNotFoundError(f"缺少必要文件：{path}")

    train_name = f"{args.dataset_prefix}_train.json"
    val_name = f"{args.dataset_prefix}_val.json"
    shutil.copy2(train_source, factory_data_dir / train_name)
    shutil.copy2(val_source, factory_data_dir / val_name)

    dataset_info = load_json(dataset_info_path)
    dataset_info[f"{args.dataset_prefix}_train"] = preference_entry(train_name)
    dataset_info[f"{args.dataset_prefix}_val"] = preference_entry(val_name)
    save_json(dataset_info_path, dataset_info)

    verified = load_json(dataset_info_path)
    for name in (f"{args.dataset_prefix}_train", f"{args.dataset_prefix}_val"):
        if not verified.get(name, {}).get("ranking"):
            raise RuntimeError(f"{name} 没有被正确注册为 preference 数据")
    print(f"注册名称：{args.dataset_prefix}_train / {args.dataset_prefix}_val")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="data/drivevla_dpo/preferences")
    parser.add_argument("--llamafactory-dir", default="third_party/LLaMA-Factory")
    parser.add_argument("--dataset-prefix", default="drivevla_v5_dpo")
    return parser.parse_args()


if __name__ == "__main__":
    register(parse_args())
