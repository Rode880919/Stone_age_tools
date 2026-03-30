"""
scorer.py — 蒙特卡洛概率评分

对每个 (rank, alloc, ini) 候选，正向模拟 N 次，统计
与输入显示值精确匹配的频率，作为该候选的"置信概率"。

性能策略：
    - alloc_err >= 0.5 的候选跳过 MC，直接按解析残差给低分
    - MC 在调用方的子线程中执行，通过 progress_cb 回调更新进度
"""

from __future__ import annotations
from typing import Callable, Optional
import numpy as np
from .reverse import ReverseCandidate, IniCandidate, RANK_RAND_TBL, N_UPS
from .matrix import raw_to_display

_rng = np.random.default_rng()

MC_N         = 2000    # 蒙特卡洛样本数
ALLOC_ERR_THRESHOLD = 1.5   # 超过此值跳过 MC（floor误差常使err达到0.5~1.5）


def score_candidates_multi(
    candidates: list[ReverseCandidate],
    level_data: list[tuple[int, int, int, int, int]],
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> list[ReverseCandidate]:
    """
    多等级版评分入口。

    从 level_data 中提取 lv1（若有）与 lv140（若有）作为 MC 对照目标。
    至少找到一个目标等级才做 MC；其余情况用解析残差评分。

    progress_cb(done, total) — 可选进度回调
    """
    lv_map = {lv: (hp, atk, df, spd) for lv, hp, atk, df, spd in level_data}
    target1   = lv_map.get(1)
    target140 = lv_map.get(140)

    # 若既无 lv1 又无 lv140，退化为纯解析评分
    has_mc = (target1 is not None) or (target140 is not None)

    total_items = sum(
        1 for c in candidates for _ in c.ini_candidates
        if has_mc and c.alloc_err < ALLOC_ERR_THRESHOLD
    )
    done = 0

    for c in candidates:
        for ic in c.ini_candidates:
            if not has_mc or c.alloc_err >= ALLOC_ERR_THRESHOLD:
                ic.score = max(0.0, 0.01 - ic.residual * 1e-8)
                continue

            p1, p140 = _mc_score(
                c.rank, c.alloc, ic.ini, target1, target140
            )
            # 得分 = 有效目标概率之积（未提供的目标不参与）
            probs = [p for p in (p1, p140) if p is not None]
            ic.score = float(np.prod(probs)) if probs else 0.0

            done += 1
            if progress_cb:
                progress_cb(done, total_items)

        c.total_score = max((ic.score for ic in c.ini_candidates), default=0.0)

    return sorted(candidates, key=lambda c: c.total_score, reverse=True)


def score_candidates(
    candidates: list[ReverseCandidate],
    hp1: int, atk1: int, def1: int, spd1: int,
    hp140: int, atk140: int, def140: int, spd140: int,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> list[ReverseCandidate]:
    """旧版两等级接口，保持向后兼容。"""
    level_data = [(1, hp1, atk1, def1, spd1), (140, hp140, atk140, def140, spd140)]
    return score_candidates_multi(candidates, level_data, progress_cb)


def _mc_score(
    rank: int,
    alloc: list[int],
    ini: int,
    target1:   tuple[int, int, int, int] | None,
    target140: tuple[int, int, int, int] | None,
) -> tuple[float | None, float | None]:
    """
    正向模拟 MC_N 次，返回 (P(lv1匹配), P(lv140匹配))。
    目标为 None 时对应返回值也为 None（不参与评分）。
    """
    flo, fhi  = RANK_RAND_TBL[rank]
    alloc_arr = np.array(alloc, dtype=np.int32)

    # ── 1 级模拟 ─────────────────────────────
    extras = _sim_param_10(MC_N)                    # (4, MC_N)，无上限
    raw1   = ini * (alloc_arr[:, None] + extras)    # (4, MC_N)

    p1: float | None = None
    if target1 is not None:
        hp1_s, atk1_s, def1_s, spd1_s = _batch_display(raw1)
        p1 = float((
            (hp1_s  == target1[0]) &
            (atk1_s == target1[1]) &
            (def1_s == target1[2]) &
            (spd1_s == target1[3])
        ).mean())

    # ── 140 级模拟 ────────────────────────────
    p140: float | None = None
    if target140 is not None:
        rawN = raw1.copy()
        for _ in range(N_UPS):
            param = _sim_param_10(MC_N)
            fr    = _rng.integers(flo, fhi + 1, MC_N) * 0.01
            rawN += ((alloc_arr[:, None] + param) * fr[None, :]).astype(np.int32)

        hp140_s, atk140_s, def140_s, spd140_s = _batch_display(rawN)
        p140 = float((
            (hp140_s  == target140[0]) &
            (atk140_s == target140[1]) &
            (def140_s == target140[2]) &
            (spd140_s == target140[3])
        ).mean())

    return p1, p140


# ─────────────────────────────────────────────
# 辅助：批量随机生成
# ─────────────────────────────────────────────
def _sim_param_10(n: int) -> np.ndarray:
    """
    升级时 10 次随机加点（无单维上限）。
    shape: (4, n)
    """
    param = np.zeros((4, n), dtype=np.int32)
    rows  = _rng.integers(0, 4, (10, n))
    for k in range(10):
        param[rows[k], np.arange(n)] += 1
    return param


def _batch_display(raw: np.ndarray) -> tuple:
    """
    raw shape (4, n): [V, S, T, D] 各 n 个 -> (hp, atk, def, spd) 各 n 个
    """
    V, S, T, D = raw[0], raw[1], raw[2], raw[3]
    hp  = (V * 4 + S + T + D) // 100
    # 先转 float 做混合精度加法，再 floor 除 100（等价于 int(sum/100)）
    atk = (S.astype(float) + T * 0.1 + V * 0.1 + D * 0.05).astype(np.int64) // 100
    df  = (T.astype(float) + S * 0.1 + V * 0.1 + D * 0.05).astype(np.int64) // 100
    spd = D // 100
    return hp, atk, df, spd
