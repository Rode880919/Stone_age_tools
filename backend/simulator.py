"""
simulator.py — 宠物成长正向模拟（对齐 GetNewPet / CHAR_PetLevelUp）

== 完整随机机制 ==

【1级初始化 GetNewPet()】
  ev_X      = RAND(0,4) - 2            ← ±2 波动，各维独立
  stored_X  = base_X + ev_X            ← 打包存入 CHAR_ALLOCPOINT
  petrank   = get_rank(Σ stored_X)     ← 由波动后 VSTD 决定，终身固定
  extra_X   = 10次随机+1到随机一维（RAND(0,3)，单项不超过4）
  raw_X_lv1 = INITNUM × (stored_X + extra_X)

【每次升级 CHAR_PetLevelUp()】
  Param_X = 10次随机+1到随机一维（RAND(0,3)，无上限）
  fRand   = RAND(flo, fhi) × 0.01  ← 由 petrank 决定，各 rank 范围宽度均为 50
  Δraw_X  = int( (stored_X + Param_X) × fRand )

== Rank 表（普通捕捉版 enemy.c:855 ENEMY_getRank）==
  ≥100 → rank 0   ≥95 → rank 1   ≥90 → rank 2
  ≥85  → rank 3   ≥80 → rank 4   <80  → rank 5

== fRand 范围（char_data.c RankRandTbl）==
  rank 0 : [450, 500]   rank 1 : [470, 520]   rank 2 : [490, 540]
  rank 3 : [510, 560]   rank 4 : [530, 580]   rank 5 : [550, 600]
"""

from __future__ import annotations
import numpy as np
from .matrix import raw_to_display

_rng = np.random.default_rng()

# ─────────────────────────────────────────────
# 常量
# ─────────────────────────────────────────────

# 普通捕捉版 Rank 表 (enemy.c:855 ENEMY_getRank)
RANK_BOUNDS_NORMAL = [100, 95, 90, 85, 80, 0]

# 转生版 Rank 表 (enemy.c:2671 GetNewPet 内部 ranktbl)
RANK_BOUNDS_TRANS = [130, 100, 95, 85, 80, 0]

# 各 rank 的 fRand 范围 (char_data.c RankRandTbl)
RANK_RAND_TBL = [
    (450, 500), (470, 520), (490, 540),
    (510, 560), (530, 580), (550, 600),
]

_PCTS = (0, 5, 25, 50, 75, 95, 100)


def get_rank_normal(vstd: int) -> int:
    """普通捕捉版 Rank 判定"""
    for r, bound in enumerate(RANK_BOUNDS_NORMAL):
        if vstd >= bound:
            return r
    return 5


def get_rank_trans(vstd: int) -> int:
    """转生版 Rank 判定"""
    for r, bound in enumerate(RANK_BOUNDS_TRANS):
        if vstd >= bound:
            return r
    return 5


# ─────────────────────────────────────────────
# 公开接口
# ─────────────────────────────────────────────
def simulate_lv140(
    ini: int,
    alloc: list[int],
    n: int = 2000,
) -> list[tuple]:
    """
    运行 n 次模拟，返回 140 级时 5 项指标的 7 分位数。

    返回 5 行，每行：
        (属性名, 最弱, P5, P25, P50, P75, P95, 最强)
    指标：生命 / 攻击 / 防御 / 敏捷 / 成长（每级 ATK+DEF+SPD 增量均值）
    """
    base = np.array(alloc, dtype=np.int32)
    rng = _rng

    # ── lv1 初始化 ──────────────────────────────
    ev      = rng.integers(0, 5, (4, n)) - 2          # RAND(0,4)-2
    stored  = base[:, None] + ev                       # (4,n) 含波动的成长率

    vstd    = stored.sum(axis=0)                       # (n,) 波动后 VSTD
    petrank = np.array([get_rank_normal(int(v)) for v in vstd])
    flo     = np.array([RANK_RAND_TBL[r][0] for r in petrank], dtype=np.int32)

    extra   = _distribute_10pts(rng, n)                # 当前配套模拟默认采用单项≤4加点
    raw     = (ini * (stored + extra)).astype(np.int64)

    # lv1 ATK+DEF+SPD（用于计算成长）
    V1, S1, T1, D1 = raw[0], raw[1], raw[2], raw[3]
    atk1 = (S1.astype(float) + T1*0.1 + V1*0.1 + D1*0.05).astype(np.int64) // 100
    def1 = (T1.astype(float) + S1*0.1 + V1*0.1 + D1*0.05).astype(np.int64) // 100
    spd1 = D1 // 100
    ads1 = (atk1 + def1 + spd1).astype(float)

    # ── lv2 → lv140：139 次升级 ─────────────────
    for _ in range(139):
        params = _param_multi(rng, n)
        fr     = (flo + rng.integers(0, 51, n)) * 0.01
        raw    = raw + ((stored + params) * fr[None, :]).astype(np.int64)

    # ── lv140 四维显示值 ─────────────────────────
    V, S, T, D = raw[0], raw[1], raw[2], raw[3]
    hp140  = (V * 4 + S + T + D) // 100
    atk140 = (S.astype(float) + T*0.1 + V*0.1 + D*0.05).astype(np.int64) // 100
    def140 = (T.astype(float) + S*0.1 + V*0.1 + D*0.05).astype(np.int64) // 100
    spd140 = D // 100

    # 成长 = (ATK140+DEF140+SPD140 - ATK1-DEF1-SPD1) / 139
    growth = (atk140 + def140 + spd140 - ads1) / 139.0

    rows = []
    for name, stat, as_float in [
        ("生命",  hp140,  False),
        ("攻击",  atk140, False),
        ("防御",  def140, False),
        ("敏捷",  spd140, False),
        ("成长",  growth, True),
    ]:
        pcts = np.percentile(stat, _PCTS)
        vals = tuple(f"{p:.2f}" for p in pcts) if as_float else tuple(int(p) for p in pcts)
        rows.append((name,) + vals)
    return rows


def simulate_percentiles(
    ini: int,
    alloc: list[int],
    target_level: int = 140,
    n: int = 2000,
) -> list[tuple]:
    """
    运行 n 次模拟，返回各级 7 分位数。

    每行：(lv, hp_min,..,hp_max, atk_min,..,atk_max, def_min,..,def_max, spd_min,..,spd_max)
    共 1 + 4×7 = 29 列。
    """
    base = np.array(alloc, dtype=np.int32)
    rng = _rng

    ev      = rng.integers(0, 5, (4, n)) - 2
    stored  = base[:, None] + ev
    vstd    = stored.sum(axis=0)
    petrank = np.array([get_rank_normal(int(v)) for v in vstd])
    flo     = np.array([RANK_RAND_TBL[r][0] for r in petrank], dtype=np.int32)

    extra   = _distribute_10pts(rng, n)
    raw     = (ini * (stored + extra)).astype(np.int64)

    results = [_pct_row(1, raw)]

    for lv in range(2, target_level + 1):
        params = _param_multi(rng, n)
        fr     = (flo + rng.integers(0, 51, n)) * 0.01
        raw    = raw + ((stored + params) * fr[None, :]).astype(np.int64)
        results.append(_pct_row(lv, raw))

    return results


def simulate_single(
    ini: int,
    alloc: list[int],
    target_level: int = 140,
) -> list[tuple[int, int, int, int, int]]:
    """
    单次随机模拟，返回各级 (lv, HP, ATK, DEF, SPD)。
    """
    rng = _rng
    base   = np.array(alloc, dtype=np.int32)
    ev     = rng.integers(0, 5, 4) - 2
    stored = (base + ev).astype(np.int32)

    petrank = get_rank_normal(int(stored.sum()))
    flo, fhi = RANK_RAND_TBL[petrank]

    extra = _distribute_10pts_single(rng)
    raw   = (ini * (stored + extra)).astype(np.int64)

    results = [(1, *raw_to_display(int(raw[0]), int(raw[1]), int(raw[2]), int(raw[3])))]

    for lv in range(2, target_level + 1):
        param = _param_single(rng)
        fr    = int(rng.integers(flo, fhi + 1)) * 0.01
        raw   = raw + ((stored + param) * fr).astype(np.int64)
        results.append((lv, *raw_to_display(int(raw[0]), int(raw[1]), int(raw[2]), int(raw[3]))))

    return results


# ─────────────────────────────────────────────
# 转生模拟
# ─────────────────────────────────────────────
def calc_transmigration(
    pet_alloc: list[int],
    stone_alloc: list[int],
    pet_level: int,
    trans_count: int,
    ans_cap: int | None = None,
) -> dict:
    """
    计算转生后的新成长率（确定性部分，无随机）。

    参数 `ans_cap` 表示转生能力上限。

    Returns
    -------
    dict with keys: ans, new_alloc, petrank, Fx
    """
    total1 = min(sum(stone_alloc), 150)
    total2 = sum(pet_alloc)

    # petrank: 首转用普通表，二转用转生表
    if trans_count == 0:
        petrank = get_rank_normal(total2)
    else:
        petrank = get_rank_trans(total2)

    Fx = int((5 - petrank) * 1.2) + 5
    lv = min(pet_level, 130)

    # ans = floor((total1/100)^5 * 1.3) + total2 + floor((LV-100)/Fx)
    ratio = total1 / 100.0
    power5 = ratio ** 5
    ans = int(power5 * 1.3) + total2 + (lv - 100) // Fx

    # 转生能力上限
    default_cap = 150 if trans_count == 0 else 200
    cap = default_cap if ans_cap is None else int(ans_cap)
    ans = min(ans, cap)

    # 按维度加权分配
    total_weight = total1 + total2 * 4
    new_alloc = [
        ans * (stone_alloc[d] + pet_alloc[d] * 4) // total_weight
        for d in range(4)
    ]

    return {
        "ans": ans,
        "new_alloc": new_alloc,
        "petrank": petrank,
        "Fx": Fx,
        "total1": total1,
        "total2": total2,
        "ans_cap": cap,
        "default_ans_cap": default_cap,
    }


def simulate_transmigration(
    ini: int,
    pet_alloc: list[int],
    stone_alloc: list[int],
    pet_level: int,
    trans_count: int,
    ans_cap: int | None = None,
    n: int = 2000,
) -> tuple[dict, list[tuple]]:
    """
    转生模拟：计算新成长率 → ±2 波动 → rank 判定 → 10 点加点 → 升级到 140。

    Returns
    -------
    (info, rows)
    - info: calc_transmigration 的结果
    - rows: 与 simulate_lv140 格式相同的 5 行分位数
    """
    info = calc_transmigration(
        pet_alloc,
        stone_alloc,
        pet_level,
        trans_count,
        ans_cap=ans_cap,
    )
    new_alloc = info["new_alloc"]
    base = np.array(new_alloc, dtype=np.int32)
    rng = _rng

    # ── ±2 波动 ────────────────────────────────
    ev     = rng.integers(0, 5, (4, n)) - 2          # RAND(0,4)-2
    stored = base[:, None] + ev                       # (4,n)

    # ── rank 判定（波动后、10 点加点前，使用转生版表）──
    vstd    = stored.sum(axis=0)
    petrank = np.array([get_rank_trans(int(v)) for v in vstd])
    flo     = np.array([RANK_RAND_TBL[r][0] for r in petrank], dtype=np.int32)

    # ── 10 点加点（当前配套模拟默认单项≤4）──────────
    extra = _distribute_10pts(rng, n)
    raw   = (ini * (stored + extra)).astype(np.int64)

    # lv1 ATK+DEF+SPD（用于计算成长）
    V1, S1, T1, D1 = raw[0], raw[1], raw[2], raw[3]
    atk1 = (S1.astype(float) + T1*0.1 + V1*0.1 + D1*0.05).astype(np.int64) // 100
    def1 = (T1.astype(float) + S1*0.1 + V1*0.1 + D1*0.05).astype(np.int64) // 100
    spd1 = D1 // 100
    ads1 = (atk1 + def1 + spd1).astype(float)

    # ── lv2 → lv140：139 次升级 ─────────────────
    for _ in range(139):
        params = _param_multi(rng, n)
        fr     = (flo + rng.integers(0, 51, n)) * 0.01
        raw    = raw + ((stored + params) * fr[None, :]).astype(np.int64)

    # ── lv140 四维显示值 ─────────────────────────
    V, S, T, D = raw[0], raw[1], raw[2], raw[3]
    hp140  = (V * 4 + S + T + D) // 100
    atk140 = (S.astype(float) + T*0.1 + V*0.1 + D*0.05).astype(np.int64) // 100
    def140 = (T.astype(float) + S*0.1 + V*0.1 + D*0.05).astype(np.int64) // 100
    spd140 = D // 100

    growth = (atk140 + def140 + spd140 - ads1) / 139.0

    rows = []
    for name, stat, as_float in [
        ("生命",  hp140,  False),
        ("攻击",  atk140, False),
        ("防御",  def140, False),
        ("敏捷",  spd140, False),
        ("成长",  growth, True),
    ]:
        pcts = np.percentile(stat, _PCTS)
        vals = tuple(f"{p:.2f}" for p in pcts) if as_float else tuple(int(p) for p in pcts)
        rows.append((name,) + vals)

    return info, rows


# ─────────────────────────────────────────────
# 内部工具
# ─────────────────────────────────────────────
def _pct_row(lv: int, raw: np.ndarray) -> tuple:
    V, S, T, D = raw[0], raw[1], raw[2], raw[3]
    hp  = (V * 4 + S + T + D) // 100
    atk = (S.astype(float) + T*0.1 + V*0.1 + D*0.05).astype(np.int64) // 100
    df  = (T.astype(float) + S*0.1 + V*0.1 + D*0.05).astype(np.int64) // 100
    spd = D // 100

    row = [lv]
    for stat in (hp, atk, df, spd):
        row.extend(int(np.percentile(stat, q)) for q in _PCTS)
    return tuple(row)


def _distribute_10pts(rng: np.random.Generator, n: int) -> np.ndarray:
    """1级初始化用：10点随机分配。

    这里的“单项≤4”是当前工具配套模拟采用的限制，不是服务器源码侧
    已在本项目内完成验证的硬编码规则。实现上使用拒绝采样。shape (4, n)
    """
    result = np.zeros((4, n), dtype=np.int32)
    dims = rng.integers(0, 4, (10, n))
    for k in range(10):
        result[dims[k], np.arange(n)] += 1

    for _ in range(100):
        bad = np.any(result > 4, axis=0)
        bad_count = bad.sum()
        if bad_count == 0:
            break
        new_result = np.zeros((4, bad_count), dtype=np.int32)
        new_dims = rng.integers(0, 4, (10, bad_count))
        for k in range(10):
            new_result[new_dims[k], np.arange(bad_count)] += 1
        result[:, bad] = new_result

    return result


def _distribute_10pts_single(rng: np.random.Generator) -> np.ndarray:
    """1级初始化用：单次10点随机分配。

    这里的“单项≤4”是当前工具配套模拟采用的限制，不是服务器源码侧
    已在本项目内完成验证的硬编码规则。实现上使用拒绝采样。
    """
    while True:
        result = np.zeros(4, dtype=np.int32)
        for c in rng.integers(0, 4, 10):
            result[c] += 1
        if result.max() <= 4:
            return result


def _param_single(rng: np.random.Generator) -> np.ndarray:
    """升级用：10次随机+1，无上限"""
    result = np.zeros(4, dtype=np.int32)
    for c in rng.integers(0, 4, 10):
        result[c] += 1
    return result


def _param_multi(rng: np.random.Generator, n: int) -> np.ndarray:
    """升级用：批量 shape (4, n)，无上限"""
    param = np.zeros((4, n), dtype=np.int32)
    dims = rng.integers(0, 4, (10, n))
    for k in range(10):
        param[dims[k], np.arange(n)] += 1
    return param
