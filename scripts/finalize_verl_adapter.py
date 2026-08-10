#!/usr/bin/env python3
"""补全 VERL 导出的 PEFT 元数据，并检查 adapter 权重是否可读。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from safetensors import safe_open


def finalize_adapter(adapter_dir: Path, base_model: str) -> dict:
    config_path = adapter_dir / "adapter_config.json"
    weights_path = adapter_dir / "adapter_model.safetensors"
    if not config_path.is_file() or not weights_path.is_file():
        raise FileNotFoundError(f"adapter 文件不完整：{adapter_dir}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["base_model_name_or_path"] = base_model
    config["inference_mode"] = True
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with safe_open(weights_path, framework="pt", device="cpu") as reader:
        keys = list(reader.keys())
        shapes = [tuple(reader.get_tensor(key).shape) for key in keys]

    if not keys or not all("lora_" in key for key in keys):
        raise ValueError("导出权重为空，或包含非 LoRA 参数")

    return {
        "adapter_dir": str(adapter_dir.resolve()),
        "base_model": base_model,
        "tensor_count": len(keys),
        "parameter_count": sum(shape[0] * shape[1] for shape in shapes if len(shape) == 2),
        "size_bytes": weights_path.stat().st_size,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--base-model", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = finalize_adapter(args.adapter_dir, args.base_model)
    print(json.dumps(result, ensure_ascii=False, indent=2))
