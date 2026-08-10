"""FlashAttention bert_padding 的纯 PyTorch 兼容实现。"""

from __future__ import annotations

import torch
from einops import rearrange


def index_first_axis(tensor: torch.Tensor, indices: torch.Tensor) -> torch.Tensor:
    """按第一维选择有效 token，并保留 PyTorch 自动求导。"""
    return tensor.index_select(0, indices.to(device=tensor.device, dtype=torch.long))


def pad_input(
    hidden_states: torch.Tensor,
    indices: torch.Tensor,
    batch: int,
    seqlen: int,
) -> torch.Tensor:
    """把连续的有效 token 放回带 padding 的批次张量。"""
    output = hidden_states.new_zeros((batch * seqlen, *hidden_states.shape[1:]))
    output.index_copy_(0, indices.to(device=hidden_states.device, dtype=torch.long), hidden_states)
    return output.reshape(batch, seqlen, *hidden_states.shape[1:])


def unpad_input(hidden_states: torch.Tensor, attention_mask: torch.Tensor):
    """移除 padding，并返回 FlashAttention bert_padding 相同的四元组。"""
    mask = attention_mask.to(dtype=torch.bool)
    seqlens = mask.sum(dim=-1, dtype=torch.int32)
    indices = torch.nonzero(mask.reshape(-1), as_tuple=False).reshape(-1)
    unpadded = index_first_axis(hidden_states.flatten(0, 1), indices)
    cu_seqlens = torch.nn.functional.pad(torch.cumsum(seqlens, dim=0, dtype=torch.int32), (1, 0))
    max_seqlen = int(seqlens.max().item()) if seqlens.numel() else 0
    return unpadded, indices, cu_seqlens, max_seqlen


__all__ = ["index_first_axis", "pad_input", "rearrange", "unpad_input"]
