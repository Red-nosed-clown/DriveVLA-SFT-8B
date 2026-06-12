#!/usr/bin/env python3
"""Qwen3-VL 单卡 LoRA/QLoRA 教学版训练脚本。

这个脚本的目标是帮助初学者理解多模态 SFT 的关键步骤，不用于替代
LLaMA-Factory。它只支持：

1. 单张 GPU；
2. batch size 固定为 1；
3. 小规模 JSONL 数据；
4. LoRA 或 4bit QLoRA。

项目的正式训练结果应以 LLaMA-Factory 配置为准。
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SmallVLADataset:
    """读取转换脚本生成的 JSONL，并只保留少量教学样本。

    输入：
        path：例如 data/nuscenes_vla_sft/train.jsonl。
        max_samples：最多读取多少条；教学脚本默认只读取 32 条。

    输出：
        每次索引返回一条包含 image 和 messages 的字典。

    为什么限制样本数：
        这个脚本用于看懂训练原理。先让少量数据快速跑通，比一开始等待
        完整训练更容易定位数据格式、显存和 loss mask 问题。
    """

    def __init__(self, path: Path, max_samples: int) -> None:
        self.rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path} 第 {line_number} 行不是合法 JSON") from exc
                self.rows.append(row)
                if len(self.rows) >= max_samples:
                    break

        if not self.rows:
            raise ValueError(f"训练文件没有有效样本：{path}")

    def __len__(self) -> int:
        """返回当前教学数据集的样本数。"""
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, Any]:
        """根据索引返回一条原始样本。"""
        return self.rows[index]


@dataclass
class AssistantOnlyCollator:
    """把一条图文对话转换为模型输入，并创建 assistant-only 标签。

    `Trainer` 会把 Dataset 返回的原始字典交给这个 collator。collator 需要
    完成四件事：

    1. 打开前视相机图像；
    2. 用 Qwen chat template 拼出完整对话；
    3. 用 processor 同时处理文本和图像；
    4. 把用户提示对应的 label 改为 -100。

    PyTorch 的交叉熵会忽略 label=-100 的位置，因此 loss 只监督 assistant
    的 JSON 答案，不会要求模型背诵用户提示词。
    """

    processor: Any
    max_length: int

    def __call__(self, batch: list[dict[str, Any]]) -> dict[str, Any]:
        """处理一个 batch；教学版明确要求 batch 中只能有一条样本。"""
        from PIL import Image

        if len(batch) != 1:
            raise ValueError("教学版脚本只支持 per_device_train_batch_size=1")

        sample = batch[0]
        image_path = Path(sample["image"])
        if not image_path.exists():
            raise FileNotFoundError(f"训练图片不存在：{image_path}")

        # 完整文本包含 user 提示和 assistant 标准答案，是模型真正看到的序列。
        full_text = self.processor.apply_chat_template(
            sample["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )

        # prompt 文本只包含 user 部分，末尾保留 assistant 开始标记。
        # 它的 token 长度用于判断从哪里开始计算答案 loss。
        prompt_text = self.processor.apply_chat_template(
            sample["messages"][:1],
            tokenize=False,
            add_generation_prompt=True,
        )

        with Image.open(image_path) as opened_image:
            image = opened_image.convert("RGB")
            full_inputs = self.processor(
                text=[full_text],
                images=[image],
                # 教学版 batch=1 时不会额外补很多 token，但仍显式使用
                # longest padding，展示真实 batch collator 的标准接口。
                padding="longest",
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )
            prompt_inputs = self.processor(
                text=[prompt_text],
                images=[image],
                padding="longest",
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )

        labels = full_inputs["input_ids"].clone()
        prompt_length = int(prompt_inputs["attention_mask"].sum().item())

        # 用户提示、图像 token 和 assistant 起始标记均不参与 loss。
        labels[:, : min(prompt_length, labels.shape[1])] = -100
        labels[full_inputs["attention_mask"] == 0] = -100

        if bool((labels != -100).any()) is False:
            raise ValueError(
                "答案 token 全部被截断，请提高 --max-length 或降低图片像素"
            )

        full_inputs["labels"] = labels
        return full_inputs


def build_processor(args: argparse.Namespace) -> Any:
    """加载 Qwen3-VL processor，它同时负责 tokenizer 和图像预处理。"""
    from transformers import AutoProcessor

    processor = AutoProcessor.from_pretrained(
        args.model_name_or_path,
        trust_remote_code=True,
    )

    # Transformers 4.57 的 Fast image processor 在部分版本中仍优先读取
    # size["longest_edge"]。因此这里同时设置 size 和 max_pixels，确保命令行
    # 参数真的控制视觉 token 数，而不是只留下一个没有生效的属性。
    processor.image_processor.size["longest_edge"] = args.image_max_pixels
    processor.image_processor.max_pixels = args.image_max_pixels

    # Qwen tokenizer 默认可能没有独立 pad token。训练时直接使用 eos token
    # 作为 padding，不会改变本项目 batch=1 的实际内容。
    if processor.tokenizer.pad_token_id is None:
        processor.tokenizer.pad_token = processor.tokenizer.eos_token
    return processor


def build_model(args: argparse.Namespace) -> Any:
    """加载基座模型，并只给语言模型线性层挂载 LoRA adapter。"""
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import BitsAndBytesConfig, Qwen3VLForConditionalGeneration

    quantization_config = None
    if args.use_qlora:
        # NF4 专门适合近似正态分布的神经网络权重；双重量化还能进一步节省显存。
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

    model = Qwen3VLForConditionalGeneration.from_pretrained(
        args.model_name_or_path,
        trust_remote_code=True,
        device_map="auto",
        dtype=torch.bfloat16,
        quantization_config=quantization_config,
    )

    # 第一版只训练语言侧 LoRA。视觉塔和多模态投影层保留基座能力，
    # 既降低显存占用，也让教学版与正式 LLaMA-Factory 配置保持一致。
    for parameter_name, parameter in model.named_parameters():
        if "visual" in parameter_name or "merger" in parameter_name:
            parameter.requires_grad = False

    if args.use_qlora:
        # 4bit 权重不能直接按普通全精度方式训练，这一步会处理输入梯度等细节。
        model = prepare_model_for_kbit_training(
            model,
            # 视觉塔已经冻结，不需要对它做 checkpoint。下面只对语言模型开启，
            # 可以避免 frozen vision 输入没有梯度的无意义 warning。
            use_gradient_checkpointing=False,
        )

    if args.gradient_checkpointing:
        # embedding 本身被冻结，但 checkpointing 需要至少一个输入保留梯度，
        # PEFT 提供的这个 helper 会给 embedding 输出注册梯度 hook。
        model.enable_input_require_grads()
        model.model.language_model.gradient_checkpointing_enable()
        model.config.use_cache = False

    lora_config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model


def run_training(args: argparse.Namespace) -> None:
    """组装 Dataset、Collator 和 Trainer，完成一次小规模教学训练。"""
    import torch
    from transformers import Trainer, TrainingArguments, set_seed

    if not torch.cuda.is_available():
        raise RuntimeError("没有检测到 CUDA GPU，教学版脚本只支持单卡训练")
    if torch.cuda.device_count() != 1:
        print(f"提示：检测到 {torch.cuda.device_count()} 张 GPU，本脚本只会使用一张。")

    set_seed(args.seed)
    processor = build_processor(args)
    model = build_model(args)
    dataset = SmallVLADataset(Path(args.train_file), args.max_samples)
    collator = AssistantOnlyCollator(processor, args.max_length)

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        max_steps=args.max_steps,
        logging_steps=1,
        save_steps=args.max_steps,
        save_total_limit=1,
        bf16=True,
        tf32=True,
        gradient_checkpointing=args.gradient_checkpointing,
        remove_unused_columns=False,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collator,
    )
    trainer.train()

    # PEFT 模型的 save_pretrained 只保存 adapter，而不是再复制一份 8B 基座权重。
    trainer.save_model(args.output_dir)
    processor.save_pretrained(args.output_dir)
    print(f"教学训练完成，LoRA adapter 已保存到：{args.output_dir}")


def parse_args() -> argparse.Namespace:
    """定义教学脚本参数，并给出适合 RTX 5090 的保守默认值。"""
    parser = argparse.ArgumentParser(
        description="Qwen3-VL 单卡小数据 LoRA/QLoRA 教学脚本"
    )
    parser.add_argument(
        "--model-name-or-path",
        default="Qwen/Qwen3-VL-8B-Instruct",
    )
    parser.add_argument(
        "--train-file",
        default="data/nuscenes_vla_sft/train.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        default="results/qwen3vl_8b_minimal_qlora",
    )
    parser.add_argument("--max-samples", type=int, default=32)
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--image-max-pixels", type=int, default=131072)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=1.0e-4)
    parser.add_argument("--lora-rank", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--use-qlora",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="默认使用 4bit QLoRA；传入 --no-use-qlora 可切换为 bf16 LoRA。",
    )
    parser.add_argument(
        "--gradient-checkpointing",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="教学小数据默认关闭；显存不足时传入 --gradient-checkpointing。",
    )
    return parser.parse_args()


if __name__ == "__main__":
    run_training(parse_args())
