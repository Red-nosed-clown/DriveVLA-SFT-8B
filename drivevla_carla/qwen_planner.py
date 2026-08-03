#!/usr/bin/env python3
"""面向 CARLA 在线图像的 Qwen3-VL DriveVLA 规划器。"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlannerPrediction:
    """单次在线规划结果和延迟信息。"""

    raw_text: str
    parsed: dict[str, Any]
    latency_s: float
    generated_at_s: float


class QwenDrivePlanner:
    """复用项目批量推理加载逻辑，支持内存中的 CARLA RGB 图像。"""

    def __init__(
        self,
        model_name_or_path: str,
        adapter_path: str | None = None,
        image_max_pixels: int = 196608,
        max_new_tokens: int = 192,
        load_in_4bit: bool = True,
        gpu_memory_fraction: float = 0.65,
    ) -> None:
        # 延迟导入重依赖，保证控制器测试不需要加载 8B 模型。
        import torch
        from scripts.infer_drivevla import load_model

        if torch.cuda.is_available():
            if not 0.0 < gpu_memory_fraction <= 1.0:
                raise ValueError("gpu_memory_fraction 必须在 (0, 1] 范围内")
            # CARLA Vulkan 与 Qwen 共用一张显卡，必须为模拟器预留显存。
            torch.cuda.set_per_process_memory_fraction(gpu_memory_fraction)

        args = argparse.Namespace(
            model_name_or_path=model_name_or_path,
            adapter_path=adapter_path,
            image_max_pixels=image_max_pixels,
            load_in_4bit=load_in_4bit,
        )
        self.model, self.processor = load_model(args)
        self.max_new_tokens = max_new_tokens

    def predict(self, image: Any, prompt_text: str) -> PlannerPrediction:
        """对一帧 PIL RGB 图像生成结构化动作和六点轨迹。"""
        import torch
        from scripts.parse_outputs import parse_model_output

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt_text},
                ],
            }
        ]
        prompt = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.processor(
            text=[prompt],
            images=[image],
            padding=True,
            return_tensors="pt",
        )
        inputs = {
            key: value.to(self.model.device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }

        started = time.perf_counter()
        with torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )
        latency = time.perf_counter() - started
        prompt_length = inputs["input_ids"].shape[1]
        raw_text = self.processor.batch_decode(
            generated[:, prompt_length:],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0].strip()
        # generate 的 KV cache 会被 PyTorch 缓存分配器保留。主动归还给驱动，
        # 避免同卡 CARLA Vulkan 在创建传感器缓冲区时 OOM。
        del generated, inputs
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return PlannerPrediction(
            raw_text=raw_text,
            parsed=parse_model_output(raw_text),
            latency_s=latency,
            generated_at_s=time.monotonic(),
        )
