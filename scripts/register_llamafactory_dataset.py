#!/usr/bin/env python3
"""把 DriveVLA 数据注册到本地 LLaMA-Factory。

这个脚本只做两件事：
1. 把已经转换好的训练集和验证集复制到 LLaMA-Factory/data。
2. 使用 json 模块更新 dataset_info.json，而不是手工拼接 JSON 字符串。

输入：
    项目数据目录、LLaMA-Factory 目录和数据集名称。

输出：
    LLaMA-Factory/data 下的数据文件，以及更新后的 dataset_info.json。

为什么这样做：
    LLaMA-Factory 通过 dataset_info.json 查找数据。把注册过程写成脚本后，
    重新转换数据或更换机器时都能稳定复现，也不容易把 JSON 配置改坏。
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    """读取 JSON 文件。

    输入：
        path：需要读取的 JSON 文件路径。

    输出：
        Python 字典或列表。

    为什么这样做：
        统一使用 UTF-8 和 json 模块，避免中文内容乱码或字符串拼接错误。
    """
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    """写入格式化 JSON 文件。

    输入：
        path：输出文件路径。
        data：需要保存的 Python 数据。

    输出：
        无返回值，结果直接写入磁盘。

    为什么这样做：
        缩进后的 JSON 便于人工检查，ensure_ascii=False 可保留中文。
    """
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def dataset_entry(file_name: str) -> dict[str, Any]:
    """创建一条 LLaMA-Factory ShareGPT 多模态数据配置。

    输入：
        file_name：位于 LLaMA-Factory/data 下的 JSON 文件名。

    输出：
        可以写入 dataset_info.json 的配置字典。

    为什么这样做：
        训练集和验证集使用完全相同的字段映射，封装后可以避免重复和漏项。
    """
    return {
        "file_name": file_name,
        "formatting": "sharegpt",
        "columns": {
            "messages": "messages",
            "images": "images",
        },
        "tags": {
            "role_tag": "role",
            "content_tag": "content",
            "user_tag": "user",
            "assistant_tag": "assistant",
        },
    }


def register_dataset(args: argparse.Namespace) -> None:
    """复制数据并更新 dataset_info.json。

    输入：
        args：命令行参数，其中包含源数据目录和 LLaMA-Factory 目录。

    输出：
        在终端打印注册结果。

    为什么这样做：
        训练配置只引用数据集名称，因此正式训练前必须先完成注册。
    """
    source_dir = Path(args.source_dir).expanduser().resolve()
    factory_dir = Path(args.llamafactory_dir).expanduser().resolve()
    factory_data_dir = factory_dir / "data"
    dataset_info_path = factory_data_dir / "dataset_info.json"

    train_source = source_dir / "drivevla_train.json"
    val_source = source_dir / "drivevla_val.json"
    for path in (train_source, val_source, dataset_info_path):
        if not path.exists():
            raise FileNotFoundError(f"缺少必要文件：{path}")

    train_target_name = f"{args.dataset_prefix}_train.json"
    val_target_name = f"{args.dataset_prefix}_val.json"
    train_target = factory_data_dir / train_target_name
    val_target = factory_data_dir / val_target_name

    # copy2 会保留文件时间等基础元数据，方便判断注册数据是否为最新版本。
    shutil.copy2(train_source, train_target)
    shutil.copy2(val_source, val_target)

    dataset_info = load_json(dataset_info_path)
    dataset_info[f"{args.dataset_prefix}_train"] = dataset_entry(train_target_name)
    dataset_info[f"{args.dataset_prefix}_val"] = dataset_entry(val_target_name)
    save_json(dataset_info_path, dataset_info)

    # 重新读取一次，确保写出的 JSON 仍然合法。
    verified_info = load_json(dataset_info_path)
    for name in (f"{args.dataset_prefix}_train", f"{args.dataset_prefix}_val"):
        if name not in verified_info:
            raise RuntimeError(f"数据集注册失败：dataset_info.json 中没有 {name}")

    print(f"训练数据：{train_target}")
    print(f"验证数据：{val_target}")
    print(f"注册名称：{args.dataset_prefix}_train / {args.dataset_prefix}_val")


def parse_args() -> argparse.Namespace:
    """解析命令行参数并返回 argparse.Namespace。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="data/nuscenes_vla_sft")
    parser.add_argument("--llamafactory-dir", default="third_party/LLaMA-Factory")
    parser.add_argument("--dataset-prefix", default="drivevla")
    return parser.parse_args()


if __name__ == "__main__":
    register_dataset(parse_args())
