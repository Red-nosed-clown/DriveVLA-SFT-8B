#!/usr/bin/env bash
set -euo pipefail

# 单卡教学型 smoke：验证当前 v6 adapter 能完成 rollout、奖励和一次 LoRA 更新。
PYTHON_BIN="${PYTHON_BIN:-/home/pc/miniconda3/envs/drivevla_verl/bin/python}"
MODEL_PATH="${MODEL_PATH:-/home/pc/.cache/huggingface/hub/models--Qwen--Qwen3-VL-8B-Instruct/snapshots/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b}"
ADAPTER_PATH="${ADAPTER_PATH:-results/qwen3vl_8b_drivevla_trainval_v6_safety_full}"
TRAIN_FILE="${TRAIN_FILE:-data/drivevla_verl/smoke/train.parquet}"
VAL_FILE="${VAL_FILE:-data/drivevla_verl/smoke/val.parquet}"
TOTAL_STEPS="${TOTAL_STEPS:-1}"
SAVE_FREQ="${SAVE_FREQ:--1}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-qwen3vl_8b_v6_grpo_smoke}"
OUTPUT_DIR="${OUTPUT_DIR:-results/verl/qwen3vl_8b_v6_grpo_smoke}"
ROLLOUT_DATA_DIR="${ROLLOUT_DATA_DIR:-}"

export PYTHONNOUSERSITE=1
export TOKENIZERS_PARALLELISM=false
export HYDRA_FULL_ERROR=1
export HF_HUB_OFFLINE=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
# 单机共置 actor 与 vLLM 时峰值约 60.4/62.2GB；放宽 Ray 提前终止阈值。
export RAY_memory_usage_threshold=0.99
# VERL V0 只借用 FlashAttention 的 padding 工具；本目录提供等价的纯 PyTorch 实现。
# 不继承外部 PYTHONPATH，避免 CARLA/Isaac Sim 的预装包污染独立 Conda 环境。
export PYTHONPATH="$(pwd)/compat:$(pwd)"

# 该脚本是幂等的：补丁已存在时只打印提示，不会重复修改第三方源码。
bash scripts/apply_verl_compat_patch.sh

"${PYTHON_BIN}" -m verl.trainer.main_ppo \
  algorithm.adv_estimator=grpo \
  algorithm.use_kl_in_reward=false \
  algorithm.rollout_correction.bypass_mode=true \
  data.train_files="${TRAIN_FILE}" \
  data.val_files="${VAL_FILE}" \
  data.image_key=images \
  data.train_batch_size=1 \
  data.max_prompt_length=1536 \
  data.max_response_length=128 \
  data.filter_overlong_prompts=true \
  data.truncation=error \
  actor_rollout_ref.model.path="${MODEL_PATH}" \
  actor_rollout_ref.model.lora_adapter_path="${ADAPTER_PATH}" \
  actor_rollout_ref.model.lora_rank=16 \
  actor_rollout_ref.model.lora_alpha=32 \
  +actor_rollout_ref.model.override_config.attn_implementation=sdpa \
  actor_rollout_ref.model.use_remove_padding=false \
  actor_rollout_ref.model.enable_gradient_checkpointing=true \
  actor_rollout_ref.actor.strategy=fsdp2 \
  actor_rollout_ref.actor.fsdp_config.model_dtype=bf16 \
  actor_rollout_ref.actor.optim.lr=5e-6 \
  actor_rollout_ref.actor.ppo_mini_batch_size=1 \
  actor_rollout_ref.actor.use_dynamic_bsz=true \
  actor_rollout_ref.actor.ppo_max_token_len_per_gpu=1792 \
  actor_rollout_ref.actor.use_kl_loss=false \
  actor_rollout_ref.actor.kl_loss_coef=0.01 \
  actor_rollout_ref.actor.kl_loss_type=low_var_kl \
  actor_rollout_ref.actor.fsdp_config.param_offload=true \
  actor_rollout_ref.actor.fsdp_config.optimizer_offload=true \
  actor_rollout_ref.actor.checkpoint.save_contents='["model"]' \
  +actor_rollout_ref.actor.checkpoint.save_lora_only=true \
  actor_rollout_ref.rollout.name=vllm \
  actor_rollout_ref.rollout.tensor_model_parallel_size=1 \
  actor_rollout_ref.rollout.load_format=safetensors \
  actor_rollout_ref.rollout.layered_summon=true \
  actor_rollout_ref.rollout.gpu_memory_utilization=0.85 \
  actor_rollout_ref.rollout.max_model_len=1664 \
  actor_rollout_ref.rollout.max_num_seqs=4 \
  actor_rollout_ref.rollout.max_num_batched_tokens=2048 \
  actor_rollout_ref.rollout.enable_chunked_prefill=false \
  actor_rollout_ref.rollout.enforce_eager=true \
  actor_rollout_ref.rollout.free_cache_engine=true \
  actor_rollout_ref.rollout.agent.num_workers=1 \
  actor_rollout_ref.rollout.n=2 \
  actor_rollout_ref.rollout.log_prob_use_dynamic_bsz=true \
  actor_rollout_ref.rollout.log_prob_max_token_len_per_gpu=1792 \
  actor_rollout_ref.ref.log_prob_use_dynamic_bsz=true \
  actor_rollout_ref.ref.log_prob_max_token_len_per_gpu=1792 \
  actor_rollout_ref.ref.fsdp_config.model_dtype=bf16 \
  actor_rollout_ref.ref.fsdp_config.param_offload=true \
  reward.custom_reward_function.path=scripts/drivevla_verl_reward.py \
  reward.custom_reward_function.name=compute_score \
  reward.num_workers=1 \
  trainer.logger='["console"]' \
  trainer.project_name=drivevla_verl \
  trainer.experiment_name="${EXPERIMENT_NAME}" \
  trainer.n_gpus_per_node=1 \
  trainer.nnodes=1 \
  trainer.use_v1=False \
  trainer.total_epochs=1 \
  trainer.total_training_steps="${TOTAL_STEPS}" \
  trainer.save_freq="${SAVE_FREQ}" \
  trainer.test_freq=-1 \
  trainer.val_before_train=false \
  trainer.rollout_data_dir="${ROLLOUT_DATA_DIR}" \
  trainer.default_local_dir="${OUTPUT_DIR}"
