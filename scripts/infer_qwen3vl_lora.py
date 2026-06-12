#!/usr/bin/env python3
"""加载 Qwen3-VL LoRA adapter，对单条 VLA 样本做推理。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_jsonl_row(path: str, index: int) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return rows[index]


def load_config(path: str) -> dict[str, Any]:
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def infer(args: argparse.Namespace) -> None:
    import torch
    from peft import PeftModel
    from PIL import Image
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    cfg = load_config(args.config)
    sample = load_jsonl_row(args.sample_file, args.index)
    base_model = args.base_model or cfg["model_name_or_path"]
    adapter_path = args.adapter_path or cfg["output_dir"]

    processor = AutoProcessor.from_pretrained(
        adapter_path if Path(adapter_path).exists() else base_model,
        trust_remote_code=True,
        max_pixels=cfg.get("image_max_pixels", 602112),
    )
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        base_model,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()

    prompt_messages = sample["messages"][:1]
    prompt = processor.apply_chat_template(
        prompt_messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    image = Image.open(sample["image"]).convert("RGB")
    inputs = processor(text=[prompt], images=[image], return_tensors="pt").to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
        )
    new_tokens = generated_ids[:, inputs["input_ids"].shape[1] :]
    pred = processor.batch_decode(new_tokens, skip_special_tokens=True)[0]

    print("预测结果：")
    print(pred.strip())
    print("\n参考答案：")
    print(sample["messages"][1]["content"][0]["text"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/qwen3vl_8b_qlora_nuscenes.yaml")
    parser.add_argument("--sample-file", default="data/nuscenes_vla_sft/val.jsonl")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--adapter-path", default=None)
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    return parser.parse_args()


if __name__ == "__main__":
    infer(parse_args())
