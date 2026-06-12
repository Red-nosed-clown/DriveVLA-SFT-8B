#!/usr/bin/env python3
"""使用 QLoRA 微调 Qwen3-VL-8B-Instruct。"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def load_config(path: str) -> dict[str, Any]:
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class JsonlVLADataset:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        with self.path.open("r", encoding="utf-8") as f:
            self.rows = [json.loads(line) for line in f if line.strip()]

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        return self.rows[idx]


@dataclass
class QwenVLCollator:
    processor: Any
    max_length: int

    def _load_image(self, image_path: str) -> Any:
        from PIL import Image

        return Image.open(image_path).convert("RGB")

    def __call__(self, batch: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        full_texts: list[str] = []
        prompt_texts: list[str] = []
        images: list[Image.Image] = []

        for row in batch:
            messages = row["messages"]
            full_texts.append(
                self.processor.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=False,
                )
            )
            prompt_texts.append(
                self.processor.apply_chat_template(
                    messages[:1],
                    tokenize=False,
                    add_generation_prompt=True,
                )
            )
            images.append(self._load_image(row["image"]))

        full = self.processor(
            text=full_texts,
            images=images,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        prompt = self.processor(
            text=prompt_texts,
            images=images,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        labels = full["input_ids"].clone()
        labels[full["attention_mask"] == 0] = -100

        # 只训练 assistant 输出，避免模型把用户提示词也作为监督目标。
        prompt_lengths = prompt["attention_mask"].sum(dim=1).tolist()
        for row_idx, prompt_len in enumerate(prompt_lengths):
            labels[row_idx, : min(prompt_len, labels.shape[1])] = -100

        full["labels"] = labels
        return full


def build_model_and_processor(cfg: dict[str, Any]) -> tuple[Any, Any]:
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoProcessor, BitsAndBytesConfig, Qwen3VLForConditionalGeneration

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if cfg.get("bf16", True) else torch.float16,
    )

    processor = AutoProcessor.from_pretrained(
        cfg["model_name_or_path"],
        trust_remote_code=True,
        max_pixels=cfg.get("image_max_pixels", 602112),
    )
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        cfg["model_name_or_path"],
        quantization_config=quantization_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16 if cfg.get("bf16", True) else torch.float16,
    )

    if cfg.get("gradient_checkpointing", True):
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

    model = prepare_model_for_kbit_training(model)
    lora_config = LoraConfig(
        r=cfg.get("lora_r", 16),
        lora_alpha=cfg.get("lora_alpha", 32),
        lora_dropout=cfg.get("lora_dropout", 0.05),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=cfg.get("lora_target_modules"),
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model, processor


def train(cfg: dict[str, Any]) -> None:
    from transformers import Trainer, TrainingArguments, set_seed

    set_seed(int(cfg.get("seed", 42)))
    model, processor = build_model_and_processor(cfg)

    train_dataset = JsonlVLADataset(cfg["train_file"])
    eval_dataset = JsonlVLADataset(cfg["validation_file"])
    collator = QwenVLCollator(processor=processor, max_length=int(cfg.get("max_length", 2048)))

    args = TrainingArguments(
        output_dir=cfg["output_dir"],
        num_train_epochs=float(cfg.get("num_train_epochs", 3)),
        per_device_train_batch_size=int(cfg.get("per_device_train_batch_size", 1)),
        per_device_eval_batch_size=int(cfg.get("per_device_eval_batch_size", 1)),
        gradient_accumulation_steps=int(cfg.get("gradient_accumulation_steps", 8)),
        learning_rate=float(cfg.get("learning_rate", 2e-4)),
        weight_decay=float(cfg.get("weight_decay", 0.0)),
        warmup_ratio=float(cfg.get("warmup_ratio", 0.03)),
        logging_steps=int(cfg.get("logging_steps", 5)),
        save_steps=int(cfg.get("save_steps", 50)),
        eval_steps=int(cfg.get("eval_steps", 50)),
        save_total_limit=int(cfg.get("save_total_limit", 2)),
        evaluation_strategy="steps",
        save_strategy="steps",
        bf16=bool(cfg.get("bf16", True)),
        tf32=bool(cfg.get("tf32", True)),
        gradient_checkpointing=bool(cfg.get("gradient_checkpointing", True)),
        remove_unused_columns=False,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=collator,
    )
    trainer.train()
    trainer.save_model(cfg["output_dir"])
    processor.save_pretrained(cfg["output_dir"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/qwen3vl_8b_qlora_nuscenes.yaml")
    return parser.parse_args()


if __name__ == "__main__":
    train(load_config(parse_args().config))
