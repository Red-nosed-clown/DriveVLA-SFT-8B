#!/usr/bin/env bash
set -euo pipefail

# 8-step 教学短训：规模足以验证保存、导出和评估，不用于宣称最终效果。
export TOTAL_STEPS="${TOTAL_STEPS:-8}"
export SAVE_FREQ="${SAVE_FREQ:-8}"
export EXPERIMENT_NAME="${EXPERIMENT_NAME:-qwen3vl_8b_v6_grpo_short}"
export OUTPUT_DIR="${OUTPUT_DIR:-results/verl/qwen3vl_8b_v6_grpo_short}"
export ROLLOUT_DATA_DIR="${ROLLOUT_DATA_DIR:-${OUTPUT_DIR}/rollouts}"

bash scripts/run_verl_grpo_smoke.sh

CHECKPOINT_DIR="${OUTPUT_DIR}/global_step_${TOTAL_STEPS}/actor"
MERGE_DIR="${OUTPUT_DIR}/adapter_hf"
ADAPTER_DIR="${MERGE_DIR}/lora_adapter"

if [[ ! -f "${CHECKPOINT_DIR}/lora_train_meta.json" ]]; then
  echo "未找到 LoRA checkpoint：${CHECKPOINT_DIR}" >&2
  exit 1
fi

# VERL checkpoint 是 FSDP shard；官方 merger 会将其转换成标准 PEFT safetensors。
set +e
PYTHONPATH="$(pwd)/compat:$(pwd)" \
PYTHONNOUSERSITE=1 \
HF_HUB_OFFLINE=1 \
/home/pc/miniconda3/envs/drivevla_verl/bin/python -m verl.model_merger merge \
  --backend fsdp \
  --local_dir "${CHECKPOINT_DIR}" \
  --target_dir "${MERGE_DIR}"
MERGE_STATUS=$?
set -e

# LoRA-only checkpoint 会正确生成子目录，但当前 merger 随后可能因根目录没有完整基座而返回 1。
# 这里以标准 PEFT 文件是否存在作为导出成功条件，不额外复制 8B 基础权重。
test -f "${ADAPTER_DIR}/adapter_config.json"
test -f "${ADAPTER_DIR}/adapter_model.safetensors"
if [[ "${MERGE_STATUS}" -ne 0 ]]; then
  echo "提示：merger 跳过完整基座校验，LoRA adapter 已正常生成。"
fi

/home/pc/miniconda3/envs/drivevla_verl/bin/python \
  scripts/finalize_verl_adapter.py \
  --adapter-dir "${ADAPTER_DIR}" \
  --base-model "${MODEL_PATH:-Qwen/Qwen3-VL-8B-Instruct}"

/home/pc/miniconda3/envs/drivevla_verl/bin/python \
  scripts/summarize_verl_rollouts.py \
  --rollout-dir "${ROLLOUT_DATA_DIR}" \
  --output-prefix "${OUTPUT_DIR}/short_train"

echo "GRPO 短训与 adapter 导出完成：${ADAPTER_DIR}"
