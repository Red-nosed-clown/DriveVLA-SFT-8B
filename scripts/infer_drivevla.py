#!/usr/bin/env python3
"""对 DriveVLA 验证集执行批量推理。

输入：
    Qwen3-VL 基座模型、可选 LoRA adapter，以及转换后的 val.jsonl。

输出：
    每个样本一行的 predictions JSONL，包含原始预测和真实答案。

为什么单独实现：
    LLaMA-Factory 负责训练最稳妥，但自写推理可以展示模型加载、图像预处理、
    adapter 挂载和生成结果保存的完整流程。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """读取验证集 JSONL，并返回样本列表。"""
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """保存预测结果，确保输出目录自动创建。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def get_prompt_text(sample: dict[str, Any], processor: Any) -> str:
    """应用 Qwen3-VL chat template，构造带 generation prompt 的输入文本。"""
    return processor.apply_chat_template(
        sample["messages"][:1],
        tokenize=False,
        add_generation_prompt=True,
    )


def load_model(args: argparse.Namespace) -> tuple[Any, Any]:
    """加载 processor、基座模型和可选 LoRA adapter。

    4bit 推理能显著降低显存占用，使 base 和 fine-tuned 对比都能在单卡完成。
    """
    import torch
    from transformers import AutoProcessor, BitsAndBytesConfig, Qwen3VLForConditionalGeneration

    quantization_config = None
    if args.load_in_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

    processor = AutoProcessor.from_pretrained(
        args.model_name_or_path,
        trust_remote_code=True,
    )
    # Fast image processor 实际按 size["longest_edge"] 缩放图像。显式同步
    # 两处配置，避免推理时意外使用默认的超高分辨率。
    processor.image_processor.size["longest_edge"] = args.image_max_pixels
    processor.image_processor.max_pixels = args.image_max_pixels
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        args.model_name_or_path,
        device_map="auto",
        dtype=torch.bfloat16,
        quantization_config=quantization_config,
        trust_remote_code=True,
    )
    if args.adapter_path:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, args.adapter_path)
    model.eval()
    return model, processor


def infer_one(
    sample: dict[str, Any],
    model: Any,
    processor: Any,
    max_new_tokens: int,
) -> str:
    """对单个图像样本生成结构化驾驶预测。"""
    import torch
    from PIL import Image

    image_path = Path(sample["image"])
    if not image_path.exists():
        raise FileNotFoundError(f"图片不存在：{image_path}")
    image = Image.open(image_path).convert("RGB")
    prompt = get_prompt_text(sample, processor)
    inputs = processor(
        text=[prompt],
        images=[image],
        padding=True,
        return_tensors="pt",
    )
    inputs = {
        key: value.to(model.device) if hasattr(value, "to") else value
        for key, value in inputs.items()
    }

    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
    prompt_length = inputs["input_ids"].shape[1]
    new_tokens = generated[:, prompt_length:]
    return processor.batch_decode(
        new_tokens,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0].strip()


def run_inference(args: argparse.Namespace) -> None:
    """遍历验证集并持续保存结果，避免中途失败丢失全部预测。"""
    samples = load_jsonl(Path(args.data_path))
    if args.max_samples > 0:
        samples = samples[: args.max_samples]
    model, processor = load_model(args)
    model_label = args.model_label or ("finetuned" if args.adapter_path else "base")

    predictions: list[dict[str, Any]] = []
    output_path = Path(args.output_path)
    for index, sample in enumerate(samples):
        try:
            prediction = infer_one(sample, model, processor, args.max_new_tokens)
            error = None
        except Exception as exc:
            prediction = ""
            error = f"{type(exc).__name__}: {exc}"
            print(f"WARNING: 样本 {sample.get('id', index)} 推理失败：{error}")

        prompt_content = sample["messages"][0]["content"]
        prompt_text = next(
            item["text"] for item in prompt_content if item.get("type") == "text"
        )
        predictions.append(
            {
                "sample_id": sample.get("id", index),
                "image": sample["image"],
                "model": model_label,
                "prompt": prompt_text,
                "ground_truth": sample.get("ground_truth", {}),
                "prediction": prediction,
                "inference_error": error,
            }
        )
        save_jsonl(output_path, predictions)
        print(f"[{index + 1}/{len(samples)}] {sample.get('id', index)}")

    print(f"推理完成：{output_path}")


def parse_args() -> argparse.Namespace:
    """解析批量推理参数。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name-or-path", default="Qwen/Qwen3-VL-8B-Instruct")
    parser.add_argument("--adapter-path", default=None)
    parser.add_argument("--data-path", default="data/nuscenes_vla_sft/val.jsonl")
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--model-label", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--max-samples", type=int, default=-1)
    parser.add_argument("--image-max-pixels", type=int, default=262144)
    parser.add_argument(
        "--load-in-4bit",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser.parse_args()


if __name__ == "__main__":
    run_inference(parse_args())
