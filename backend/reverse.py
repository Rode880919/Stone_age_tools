"""
reverse.py — 核心反推算法

支持输入任意等级组合（≥2个），推算个体成长率 alloc[V,S,T,D]
（CHAR_ALLOCPOINT，经 ±2 波动后），及 INITNUM，并外推 140 级预测。

两套 Rank 表：
  普通捕捉版（enemy.c:855 ENEMY_getRank）：
    ≥100 → rank 0   ≥95 → rank 1   ≥90 → rank 2
    ≥85  → rank 3   ≥80 → rank 4   <80  → rank 5
  转生版（enemy.c:2671 GetNewPet 内部 ranktbl）：
    ≥130 → rank 0   ≥100 → rank 1   ≥95 → rank 2
    ≥85  → rank 3   ≥80  → rank 4   <80  → rank 5
"""

from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from .matrix import display_to_raw, raw_to_display

# ─────────────────────────────────────────────
# Rank 常量
# ─────────────────────────────────────────────
# 转生版 Rank 表
RANK_BOUNDS_TRANS  = [130, 100, 95, 85, 80, 0]
# 普通捕捉版 Rank 表
RANK_BOUNDS_NORMAL = [100, 95, 90, 85, 80, 0]

# 默认使用普通捕捉版（向后兼容的别名）
RANK_BOUNDS   = RANK_BOUNDS_NORMAL

RANK_RAND_TBL = [(450, 500), (470, 520), (490, 540),
                 (510, 560), (530, 580), (550, 600)]
FRAND_MEAN    = [(lo + hi) * 0.005 for lo, hi in RANK_RAND_TBL]
# [4.75, 4.95, 5.15, 5.35, 5.55, 5.75]

BORDER_TOL = 5    # vstd 自洽性验证的边界容差
N_UPS = 139       # lv1 → lv140 共 139 次升级（供 scorer 引用）


def get_rank(vstd: int, transmigrated: bool = False) -> int:
    """Rank 判定。transmigrated=True 时使用转生版表，否则普通捕捉版。"""
    bounds = RANK_BOUNDS_TRANS if transmigrated else RANK_BOUNDS_NORMAL
    for r, thresh in enumerate(bounds[:-1]):
        if vstd >= thresh:
            return r
    return 5


def _rank_upper(rank: int, bounds: list[int]) -> int:
    return bounds[rank - 1] if rank > 0 else 9999


# ─────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────
@dataclass
class IniCandidate:
    ini: int
    residual: float          # 4维联合残差（越小越好）
    score: float = 0.0       # 由 scorer 填写的综合概率


@dataclass
class ReverseCandidate:
    rank: int
    alloc: list[int]               # [V, S, T, D] 成长率整数
    vstd: float                    # alloc 浮点估算总和
    alloc_err: float               # 各维 |float - int| L1 范数
    ini_candidates: list[IniCandidate] = field(default_factory=list)
    total_score: float = 0.0       # 由 scorer 填写
    # 140 级预测（显示值）
    pred_lv140: tuple[int, int, int, int] | None = None   # (hp, atk, def, spd)
    pred_lv140_sum: int = 0        # hp + atk + def + spd

    @property
    def alloc_sum(self) -> int:
        return sum(self.alloc)


# ─────────────────────────────────────────────
# 核心：多等级反推
# ─────────────────────────────────────────────
def reverse_engineer_multi(
    level_data: list[tuple[int, int, int, int, int]],
    ini_range: range = range(5, 61),
    top_ini: int = 8,
    transmigrated: bool = False,
) -> list[ReverseCandidate]:
    """
    多等级反推主函数。

    Parameters
    ----------
    level_data : list of (level, hp, atk, def, spd)，至少两条，等级各不同
    ini_range  : 搜索 INITNUM 的范围
    top_ini    : 每个 alloc 候选保留的最优 INITNUM 数量
    transmigrated : 是否为转生宠物（决定使用哪套 Rank 表）

    Returns
    -------
    list[ReverseCandidate]，按 alloc_err 升序排列
    """
    if len(level_data) < 2:
        raise ValueError("至少需要 2 个等级的数据")

    # 转为原始点数并按等级排序
    parsed: list[tuple[int, np.ndarray]] = []
    for lv, hp, atk, df, spd in level_data:
        parsed.append((lv, display_to_raw(hp, atk, df, spd)))
    parsed.sort(key=lambda x: x[0])

    # 生成所有等级对，权重 = 等级差（差越大信噪比越好）
    pairs: list[tuple[int, np.ndarray, int, np.ndarray, int, np.ndarray]] = []
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            lv_i, raw_i = parsed[i]
            lv_j, raw_j = parsed[j]
            gap = lv_j - lv_i
            pairs.append((gap, raw_j - raw_i, lv_i, raw_i, lv_j, raw_j))

    total_weight = sum(gap for gap, *_ in pairs)

    bounds = RANK_BOUNDS_TRANS if transmigrated else RANK_BOUNDS_NORMAL
    candidates: list[ReverseCandidate] = []

    for rank in range(6):
        fm = FRAND_MEAN[rank]

        # 加权平均 alloc 估算：每对提供 alloc_X ≈ ΔX/(gap*fm) - 2.5
        alloc_float = [0.0] * 4
        for gap, delta, *_ in pairs:
            w = gap / total_weight
            for d in range(4):
                alloc_float[d] += w * (delta[d] / (gap * fm) - 2.5)

        vstd_est = sum(alloc_float)
        lo, hi   = bounds[rank], _rank_upper(rank, bounds)
        if not (lo - BORDER_TOL <= vstd_est < hi + BORDER_TOL):
            continue

        alloc_int = [round(a) for a in alloc_float]
        alloc_err = sum(abs(alloc_float[d] - alloc_int[d]) for d in range(4))

        # 140 级预测：基于显示值线性外推（与 rank/alloc 无关）
        pred_lv140 = _predict_lv140_linear(level_data)

        # INITNUM 搜索：用最低等级的数据（如有 lv1 则最准）
        # 若最低等级 > 1，先反推到 lv1
        raw_for_ini = _backtrack_to_lv1(parsed[0][0], parsed[0][1], alloc_int, fm)
        ini_cands = _find_ini_candidates(raw_for_ini, alloc_int, ini_range, top_ini)
        if not ini_cands:
            continue

        cand = ReverseCandidate(
            rank=rank,
            alloc=alloc_int,
            vstd=vstd_est,
            alloc_err=alloc_err,
            ini_candidates=ini_cands,
            pred_lv140=pred_lv140,
            pred_lv140_sum=sum(pred_lv140) if pred_lv140 else 0,
        )
        candidates.append(cand)

    candidates.sort(key=lambda c: c.alloc_err)
    return candidates


# ─────────────────────────────────────────────
# 便捷包装：保持与旧代码的兼容
# ─────────────────────────────────────────────
def reverse_engineer(
    hp1: int, atk1: int, def1: int, spd1: int,
    hp140: int, atk140: int, def140: int, spd140: int,
    ini_range: range = range(5, 61),
    top_ini: int = 8,
    transmigrated: bool = False,
) -> list[ReverseCandidate]:
    """两等级快速入口（lv1 + lv140）"""
    return reverse_engineer_multi(
        [(1, hp1, atk1, def1, spd1), (140, hp140, atk140, def140, spd140)],
        ini_range=ini_range,
        top_ini=top_ini,
        transmigrated=transmigrated,
    )


# ─────────────────────────────────────────────
# 内部工具
# ─────────────────────────────────────────────
def _predict_lv140_linear(
    level_data: list[tuple[int, int, int, int, int]],
) -> tuple[int, int, int, int]:
    """
    基于显示值线性外推预测 140 级状态。

    算法：
      - 若已有 lv140，直接返回
      - 否则对 HP/ATK/DEF/SPD 各自做最小二乘线性拟合（≥2 点时等价最优回归），
        预测 lv=140 时的显示值：stat_140 = a×140 + b
      - 两点时退化为简单斜率外推：
          rate = (stat_high − stat_low) / (lv_high − lv_low)
          stat_140 = stat_high + rate × (140 − lv_high)
    """
    for lv, hp, atk, df, spd in level_data:
        if lv == 140:
            return (hp, atk, df, spd)

    lvs   = np.array([d[0] for d in level_data], dtype=float)
    stats = np.array([[d[1], d[2], d[3], d[4]] for d in level_data], dtype=float)

    preds = []
    for dim in range(4):
        a, b = np.polyfit(lvs, stats[:, dim], 1)   # 最小二乘线性拟合
        preds.append(int(round(a * 140 + b)))

    return tuple(preds)


def _backtrack_to_lv1(
    lv_ref: int,
    raw_ref: np.ndarray,
    alloc_int: list[int],
    fm: float,
) -> np.ndarray:
    """
    若参考等级不是 1，反向推算 lv1 的原始点数估算值。
    lv1 与 lv_ref 的差值 = (lv_ref-1) 次升级的期望增量。
    """
    if lv_ref == 1:
        return raw_ref
    n_down = lv_ref - 1
    exp_gain = np.array([(alloc_int[d] + 2.5) * fm for d in range(4)])
    return raw_ref - n_down * exp_gain


def _find_ini_candidates(
    raw1: np.ndarray,
    alloc_int: list[int],
    ini_range: range,
    top_k: int,
) -> list[IniCandidate]:
    """
    4 维联合残差评分，返回最优 top_k 个 INITNUM 候选。
    ev_d ∈ {0..10}：1级时 10 次无上限加点，单维最多全部 +10。
    """
    best: dict[int, float] = {}

    for ini_c in ini_range:
        total_res = 0.0
        feasible  = True
        for d in range(4):
            best_res_d = min(
                (ini_c * (alloc_int[d] + ev) - raw1[d]) ** 2
                for ev in range(11)
            )
            if best_res_d > (ini_c * max(alloc_int[d], 1) * 0.6) ** 2 + 1:
                feasible = False
                break
            total_res += best_res_d

        if feasible:
            if ini_c not in best or total_res < best[ini_c]:
                best[ini_c] = total_res

    scored = [IniCandidate(ini=k, residual=v) for k, v in best.items()]
    scored.sort(key=lambda x: x.residual)
    return scored[:top_k]
