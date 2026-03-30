"""
simulate_pet.py — 从 enemybase.txt 读取宠物参数，模拟成长至 140 级

用法:
    python simulate_pet.py [宠物名] [模拟次数]
    python simulate_pet.py 巴朵兰恩 10000

流程:
  1. 从 enemybase.txt 中读取宠物模板参数 (INITNUM, BASEVITAL, BASESTR, BASETGH, BASEDEX)
  2. 模拟 1 级初始化:
     - 四维各自 ±2 波动: RAND(0,4)-2
     - 10 点随机分配到四维 (等权), 当前配套模拟默认单项不超过 4 点
  3. 由波动后的成长率总和 (VSTD) 确定 PETRANK (使用普通捕捉版 Rank 表)
  4. 模拟升级至 140 级 (139 次升级)
  5. 输出 140 级时 HP/ATK/DEF/SPD 的统计分布
"""

from __future__ import annotations
import sys
import os
import numpy as np

# ─── 常量 ───────────────────────────────────────────

# 普通捕捉版 Rank 表 (enemy.c:855 ENEMY_getRank)
RANK_BOUNDS_NORMAL = [100, 95, 90, 85, 80, 0]

# 各 rank 的 fRand 范围 (char_data.c RankRandTbl)
RANK_RAND_TBL = [
    (450, 500), (470, 520), (490, 540),
    (510, 560), (530, 580), (550, 600),
]

ENEMYBASE_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'gmsv', 'data', 'enemybase.txt'
)


def get_rank_normal(vstd: int) -> int:
    """普通捕捉版 Rank 判定"""
    for r, bound in enumerate(RANK_BOUNDS_NORMAL):
        if vstd >= bound:
            return r
    return 5


# ─── 读取 enemybase.txt ────────────────────────────

def load_enemybase(path: str = ENEMYBASE_PATH) -> list[dict]:
    """
    解析 enemybase.txt, 返回全部宠物模板列表。

    字段映射 (CSV 逗号分隔):
      [0]   = 名称
      [1-5] = 材质等字符串字段
      [6]   = E_T_TEMPNO
      [7]   = E_T_INITNUM
      [8]   = E_T_LVUPPOINT
      [9]   = E_T_BASEVITAL
      [10]  = E_T_BASESTR
      [11]  = E_T_BASETGH
      [12]  = E_T_BASEDEX
    """
    results = []
    with open(path, 'rb') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fields = line.split(b',')
            if len(fields) < 13:
                continue
            try:
                name = fields[0].decode('gbk', errors='replace')
                tempno = int(fields[6])
                initnum = int(fields[7])
                # lvuppoint 可以是小数, 但成长模拟中不直接用到
                lvuppoint = float(fields[8])
                basevital = int(fields[9])
                basestr = int(fields[10])
                basetgh = int(fields[11])
                basedex = int(fields[12])
            except (ValueError, IndexError):
                continue
            results.append({
                'name': name,
                'tempno': tempno,
                'initnum': initnum,
                'lvuppoint': lvuppoint,
                'basevital': basevital,
                'basestr': basestr,
                'basetgh': basetgh,
                'basedex': basedex,
            })
    return results


def find_pet(pets: list[dict], name: str) -> list[dict]:
    """按名称搜索宠物, 返回所有匹配项"""
    return [p for p in pets if name in p['name']]


# ─── 模拟核心 ──────────────────────────────────────

def _distribute_10pts(rng: np.random.Generator, n: int) -> np.ndarray:
    """
    10 点随机分配到四维, 等权。当前配套模拟默认采用“单项不超过 4 点”的限制。
    返回 shape (4, n)。

    这是工具侧的模拟口径, 不是服务器源码侧已在本项目内完成验证的
    硬编码规则。实现上采用拒绝采样: 先无限制分配, 再对超限的列重新采样。
    """
    result = np.zeros((4, n), dtype=np.int32)
    dims = rng.integers(0, 4, (10, n))
    for k in range(10):
        result[dims[k], np.arange(n)] += 1

    # 拒绝超过4的, 重新采样
    max_iter = 100
    for _ in range(max_iter):
        bad_mask = np.any(result > 4, axis=0)  # (n,)
        bad_count = bad_mask.sum()
        if bad_count == 0:
            break
        # 对超限列重新采样
        new_result = np.zeros((4, bad_count), dtype=np.int32)
        new_dims = rng.integers(0, 4, (10, bad_count))
        for k in range(10):
            new_result[new_dims[k], np.arange(bad_count)] += 1
        result[:, bad_mask] = new_result

    return result


def simulate(
    initnum: int,
    base_alloc: list[int],
    n: int = 10000,
    seed: int | None = None,
) -> dict:
    """
    模拟 n 次从 1 级到 140 级的成长。

    参数:
        initnum: 初始乘数基数 (E_T_INITNUM)
        base_alloc: [BASEVITAL, BASESTR, BASETGH, BASEDEX]
        n: 模拟次数
        seed: 随机种子 (可选)

    返回:
        包含统计结果的字典
    """
    rng = np.random.default_rng(seed)
    base = np.array(base_alloc, dtype=np.int32)

    # ── 1级初始化 ──────────────────────────────
    # Step 1: 四维各自 ±2 波动
    ev = rng.integers(0, 5, (4, n)) - 2  # RAND(0,4)-2
    stored = base[:, None] + ev  # (4, n) 波动后的成长率

    # Step 2: 10 点随机分配
    # 当前配套模拟默认采用“单项 ≤ 4”的限制；这不是服务器源码侧
    # 已在本项目内完成验证的硬编码规则。
    extra = _distribute_10pts(rng, n)  # (4, n)

    # VSTD 和 Rank (由波动后成长率决定, 终身固定)
    vstd = stored.sum(axis=0)  # (n,)
    petrank = np.array([get_rank_normal(int(v)) for v in vstd])  # (n,)

    # fRand 下限
    flo = np.array([RANK_RAND_TBL[r][0] for r in petrank], dtype=np.int32)

    # 1级原始属性
    raw = (initnum * (stored + extra)).astype(np.int64)  # (4, n)

    # ── 升级 lv2 → lv140: 共 139 次 ───────────
    for _ in range(139):
        # 每级 10 点随机分配 (原版无上限)
        params = np.zeros((4, n), dtype=np.int32)
        dims = rng.integers(0, 4, (10, n))
        for k in range(10):
            params[dims[k], np.arange(n)] += 1

        fr = (flo + rng.integers(0, 51, n)) * 0.01  # fRand
        raw = raw + ((stored + params) * fr[None, :]).astype(np.int64)

    # ── 计算 140 级显示值 ──────────────────────
    V, S, T, D = raw[0], raw[1], raw[2], raw[3]
    hp  = (V * 4 + S + T + D) // 100
    atk = (S.astype(float) + T * 0.1 + V * 0.1 + D * 0.05).astype(np.int64) // 100
    def_ = (T.astype(float) + S * 0.1 + V * 0.1 + D * 0.05).astype(np.int64) // 100
    spd = D // 100

    pcts = (0, 5, 25, 50, 75, 95, 100)
    pct_labels = ('Min', 'P5', 'P25', 'P50', 'P75', 'P95', 'Max')

    stats = {}
    for name, arr in [('HP', hp), ('ATK', atk), ('DEF', def_), ('SPD', spd)]:
        values = np.percentile(arr, pcts)
        stats[name] = {label: int(v) for label, v in zip(pct_labels, values)}
        stats[name]['Mean'] = float(np.mean(arr))
        stats[name]['Std'] = float(np.std(arr))

    # Rank 分布统计
    rank_counts = {}
    for r in range(6):
        cnt = int((petrank == r).sum())
        if cnt > 0:
            rank_counts[r] = cnt

    return {
        'stats': stats,
        'rank_distribution': rank_counts,
        'vstd_mean': float(np.mean(vstd)),
        'vstd_std': float(np.std(vstd)),
        'n': n,
    }


# ─── 输出格式化 ────────────────────────────────────

def print_results(pet_info: dict, results: dict):
    """格式化输出模拟结果"""
    print(f"\n{'='*60}")
    print(f"  宠物: {pet_info['name']}  (TEMPNO={pet_info['tempno']})")
    print(f"  INITNUM={pet_info['initnum']}  LVUPPOINT={pet_info['lvuppoint']}")
    print(f"  基础成长率: V={pet_info['basevital']} S={pet_info['basestr']}"
          f" T={pet_info['basetgh']} D={pet_info['basedex']}"
          f"  (总和={sum([pet_info['basevital'], pet_info['basestr'], pet_info['basetgh'], pet_info['basedex']])})")
    print(f"  模拟次数: {results['n']}")
    print(f"{'='*60}")

    print(f"\n  VSTD (波动后): 均值={results['vstd_mean']:.1f}  标准差={results['vstd_std']:.1f}")

    print(f"\n  Rank 分布:")
    for r, cnt in sorted(results['rank_distribution'].items()):
        pct = cnt / results['n'] * 100
        print(f"    Rank {r}: {cnt:>6} ({pct:5.1f}%)")

    print(f"\n  140 级属性分布:")
    print(f"  {'属性':>4}  {'Min':>6} {'P5':>6} {'P25':>6} {'P50':>6} {'P75':>6} {'P95':>6} {'Max':>6}  {'Mean':>7} {'Std':>6}")
    print(f"  {'-'*74}")
    for name in ('HP', 'ATK', 'DEF', 'SPD'):
        s = results['stats'][name]
        print(f"  {name:>4}  {s['Min']:>6} {s['P5']:>6} {s['P25']:>6} {s['P50']:>6}"
              f" {s['P75']:>6} {s['P95']:>6} {s['Max']:>6}  {s['Mean']:>7.1f} {s['Std']:>6.1f}")
    print()


# ─── 入口 ──────────────────────────────────────────

def main():
    pet_name = '巴朵兰恩'
    n_sim = 10000

    if len(sys.argv) >= 2:
        pet_name = sys.argv[1]
    if len(sys.argv) >= 3:
        n_sim = int(sys.argv[2])

    pets = load_enemybase()
    matches = find_pet(pets, pet_name)

    if not matches:
        print(f"未找到名为 '{pet_name}' 的宠物")
        print("可用宠物 (前20个):")
        for p in pets[:20]:
            print(f"  {p['name']} (TEMPNO={p['tempno']})")
        sys.exit(1)

    print(f"找到 {len(matches)} 条匹配记录:")
    for i, p in enumerate(matches):
        vstd = p['basevital'] + p['basestr'] + p['basetgh'] + p['basedex']
        print(f"  [{i}] {p['name']} TEMPNO={p['tempno']} "
              f"INITNUM={p['initnum']} V={p['basevital']} S={p['basestr']} "
              f"T={p['basetgh']} D={p['basedex']} (VSTD={vstd})")

    # 默认模拟第一条
    pet = matches[0]
    base_alloc = [pet['basevital'], pet['basestr'], pet['basetgh'], pet['basedex']]

    results = simulate(pet['initnum'], base_alloc, n=n_sim)
    print_results(pet, results)


if __name__ == '__main__':
    main()
