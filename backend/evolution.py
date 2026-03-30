"""
evolution.py — 融合蛋喂药与孵化后成长优化

按 gmsv 当前实现的整数规则计算：
1. 蛋药按 itemset6.txt 中的原始值累加到蛋的 EVOLUTIONBASE
2. 按 PET_getEvolutionAns() 做折算、50 压缩、并入蛋成长、150 压缩，得到孵化后成长档
3. 这里只分析“孵化后成长档”，不包含出生后 10 点随机

默认规则等价于：
- 40 颗药
- 5 个等级原始值：25 / 50 / 75 / 100 / 125
- 折算：floor(raw * 7 / 1000)
- 折算单项上限：60
- 折算总和上限：50
- 最终单项上限：60
- 最终总和上限：150
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable


DIM_NAMES = ("V", "S", "T", "D")
LEVEL_NAMES = ("Lv1", "Lv2", "Lv3", "Lv4", "Lv5")


@dataclass(frozen=True)
class EvolutionParams:
    total_feeds: int = 40
    medicine_effects: tuple[int, int, int, int, int] = (25, 50, 75, 100, 125)
    fold_scale_num: int = 7
    fold_scale_den: int = 1000
    effective_single_cap: int = 60
    work_total_cap: int = 50
    base_single_min: int = 0
    base_single_max: int = 60
    final_single_cap: int = 60
    final_total_cap: int = 150
    top_n: int = 12


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _normalize_effects(effects: Iterable[int]) -> tuple[int, int, int, int, int]:
    values = tuple(int(x) for x in effects)
    if len(values) != 5:
        raise ValueError("蛋药等级效果必须是 5 项 [Lv1..Lv5]")
    if any(x < 0 for x in values):
        raise ValueError("蛋药等级效果必须 ≥ 0")
    return values


def normalize_base_alloc(base_alloc: list[int], params: EvolutionParams) -> list[int]:
    if len(base_alloc) != 4:
        raise ValueError("蛋成长必须是 4 维 [V, S, T, D]")
    normalized: list[int] = []
    for value in base_alloc:
        value = int(value)
        if value < params.base_single_min:
            value = params.base_single_min
        if value > params.base_single_max:
            value = params.base_single_max
        normalized.append(value)
    return normalized


def normalize_weights(weights: list[float]) -> list[float]:
    if len(weights) != 4:
        raise ValueError("线性目标权重必须是 4 维 [xV, xS, xT, xD]")
    return [float(x) for x in weights]


def format_plan_summary(plan: list[list[int]]) -> str:
    parts: list[str] = []
    for dim_name, counts in zip(DIM_NAMES, plan):
        used = [f"{idx + 1}:{count}" for idx, count in enumerate(counts) if count]
        parts.append(f"{dim_name}[{' '.join(used) if used else '-'}]")
    return "  ".join(parts)


def plan_total_feeds(plan: list[list[int]]) -> int:
    return sum(sum(int(x) for x in row) for row in plan)


def plan_dim_feed_counts(plan: list[list[int]]) -> list[int]:
    return [sum(int(x) for x in row) for row in plan]


def plan_raw_totals(plan: list[list[int]], params: EvolutionParams) -> list[int]:
    effects = _normalize_effects(params.medicine_effects)
    if len(plan) != 4 or any(len(row) != 5 for row in plan):
        raise ValueError("喂药方案必须是 4x5：V/S/T/D × Lv1..Lv5")
    return [
        sum(int(count) * effects[level] for level, count in enumerate(row))
        for row in plan
    ]


def _plan_level_preference(plan: list[list[int]]) -> tuple[int, int, int, int, int]:
    totals = [sum(int(row[level]) for row in plan) for level in range(5)]
    return tuple(totals[::-1])


def _single_level_preference(level_counts: tuple[int, int, int, int, int]) -> tuple[int, int, int, int, int]:
    return tuple(int(level_counts[idx]) for idx in range(4, -1, -1))


def _pair_level_preference(pair: tuple[dict, dict]) -> tuple[int, int, int, int, int]:
    totals = [
        int(pair[0]["level_counts"][idx]) + int(pair[1]["level_counts"][idx])
        for idx in range(5)
    ]
    return tuple(totals[::-1])


def _witness_level_preference(witness: tuple[dict, dict, dict, dict]) -> tuple[int, int, int, int, int]:
    totals = [
        sum(int(witness[dim]["level_counts"][idx]) for dim in range(4))
        for idx in range(5)
    ]
    return tuple(totals[::-1])


def _fold_raw_to_work(raw_totals: list[int], params: EvolutionParams) -> list[int]:
    return [
        clamp(
            (max(0, int(value)) * params.fold_scale_num) // params.fold_scale_den,
            0,
            params.effective_single_cap,
        )
        for value in raw_totals
    ]


def _apply_work_total_cap(work_raw: list[int], params: EvolutionParams) -> list[int]:
    work = [clamp(int(value), 0, params.effective_single_cap) for value in work_raw]
    total = sum(work)
    if total > params.work_total_cap and total > 0:
        work = [
            clamp((value * params.work_total_cap) // total, 0, params.effective_single_cap)
            for value in work
        ]
    return work


def incubate_alloc(base_alloc: list[int], plan: list[list[int]], params: EvolutionParams) -> dict:
    base = normalize_base_alloc(base_alloc, params)
    raw_totals = plan_raw_totals(plan, params)
    work_raw = _fold_raw_to_work(raw_totals, params)
    work = _apply_work_total_cap(work_raw, params)

    total1 = sum(work)
    total2 = sum(base)
    total = (total1 // 2) + total2

    final_alloc = list(base)
    if total > 0:
        for i in range(4):
            fixwork = base[i] + float(work[i] // 2)
            delta = int((fixwork / total) * total1)
            final_alloc[i] = clamp(base[i] + delta, 1, params.final_single_cap)

    final_total_before_cap = sum(final_alloc)
    if final_total_before_cap > params.final_total_cap and final_total_before_cap > 0:
        final_alloc = [
            clamp((value * params.final_total_cap) // final_total_before_cap, 1, params.final_single_cap)
            for value in final_alloc
        ]

    final_total = sum(final_alloc)
    return {
        "base_alloc": base,
        "plan": [[int(x) for x in row] for row in plan],
        "plan_summary": format_plan_summary(plan),
        "plan_level_preference": _plan_level_preference(plan),
        "dim_feed_counts": plan_dim_feed_counts(plan),
        "total_feeds": plan_total_feeds(plan),
        "raw_totals": raw_totals,
        "folded_work_raw": work_raw,
        "effective_work": work,
        "final_alloc": final_alloc,
        "final_total": final_total,
        "triggered_work_total_cap": sum(work_raw) > params.work_total_cap,
        "triggered_final_total_cap": final_total_before_cap > params.final_total_cap,
    }


def _iter_level_count_vectors(total: int):
    for c1 in range(total + 1):
        remain1 = total - c1
        for c2 in range(remain1 + 1):
            remain2 = remain1 - c2
            for c3 in range(remain2 + 1):
                remain3 = remain2 - c3
                for c4 in range(remain3 + 1):
                    c5 = remain3 - c4
                    yield (c1, c2, c3, c4, c5)


@lru_cache(maxsize=None)
def _single_dim_options(
    total_feeds: int,
    medicine_effects: tuple[int, int, int, int, int],
    fold_scale_num: int,
    fold_scale_den: int,
    effective_single_cap: int,
) -> tuple[tuple[tuple[int, tuple[dict, ...]], ...], int]:
    by_work: dict[int, dict[int, dict]] = {}
    for pill_count in range(total_feeds + 1):
        for level_counts in _iter_level_count_vectors(pill_count):
            raw_total = sum(level_counts[idx] * medicine_effects[idx] for idx in range(5))
            work = clamp((raw_total * fold_scale_num) // fold_scale_den, 0, effective_single_cap)
            work_bucket = by_work.setdefault(work, {})
            candidate = {
                "pill_count": pill_count,
                "raw_total": raw_total,
                "work": work,
                "level_counts": level_counts,
            }
            current = work_bucket.get(pill_count)
            if current is None:
                work_bucket[pill_count] = candidate
            else:
                current_key = (current["raw_total"], _single_level_preference(current["level_counts"]))
                candidate_key = (candidate["raw_total"], _single_level_preference(candidate["level_counts"]))
                if candidate_key > current_key:
                    work_bucket[pill_count] = candidate

    frozen = tuple(
        (work, tuple(sorted(options.values(), key=lambda item: item["pill_count"])))
        for work, options in sorted(by_work.items())
    )
    max_work = max(by_work) if by_work else 0
    return frozen, max_work


@lru_cache(maxsize=None)
def _reachable_work_states(
    total_feeds: int,
    medicine_effects: tuple[int, int, int, int, int],
    fold_scale_num: int,
    fold_scale_den: int,
    effective_single_cap: int,
) -> tuple[dict, ...]:
    single_options_frozen, max_work = _single_dim_options(
        total_feeds,
        medicine_effects,
        fold_scale_num,
        fold_scale_den,
        effective_single_cap,
    )
    options_by_work = dict(single_options_frozen)
    work_values = tuple(range(max_work + 1))

    pair_maps: dict[tuple[int, int], dict[int, tuple[dict, dict]]] = {}
    for w1 in work_values:
        opts1 = options_by_work.get(w1, ())
        for w2 in work_values:
            opts2 = options_by_work.get(w2, ())
            total_map: dict[int, tuple[dict, dict]] = {}
            for opt1 in opts1:
                for opt2 in opts2:
                    pills = opt1["pill_count"] + opt2["pill_count"]
                    candidate = (opt1, opt2)
                    current = total_map.get(pills)
                    if current is None or _pair_level_preference(candidate) > _pair_level_preference(current):
                        total_map[pills] = candidate
            pair_maps[(w1, w2)] = total_map

    states: list[dict] = []
    for w1 in work_values:
        for w2 in work_values:
            pair12 = pair_maps[(w1, w2)]
            if not pair12:
                continue
            for w3 in work_values:
                for w4 in work_values:
                    pair34 = pair_maps[(w3, w4)]
                    if not pair34:
                        continue
                    witness = None
                    for pills12, plan12 in pair12.items():
                        plan34 = pair34.get(total_feeds - pills12)
                        if plan34 is None:
                            continue
                        candidate = plan12 + plan34
                        if witness is None or _witness_level_preference(candidate) > _witness_level_preference(witness):
                            witness = candidate
                    if witness is None:
                        continue
                    states.append(
                        {
                            "folded_work_raw": [w1, w2, w3, w4],
                            "plan": [
                                list(witness[0]["level_counts"]),
                                list(witness[1]["level_counts"]),
                                list(witness[2]["level_counts"]),
                                list(witness[3]["level_counts"]),
                            ],
                        }
                    )

    return tuple(states)


def _score_entry(final_alloc: list[int], weights: list[float]) -> float:
    return sum(final_alloc[idx] * weights[idx] for idx in range(4))


def _target_index(target_dim: str | None) -> int | None:
    if not target_dim:
        return None
    normalized = target_dim.upper()
    if normalized not in DIM_NAMES:
        raise ValueError("目标单项必须是 V/S/T/D 或留空")
    return DIM_NAMES.index(normalized)


def _entry_key(
    entry: dict,
    weights: list[float],
    target_idx: int | None = None,
    secondary_idx: int | None = None,
) -> tuple:
    final_alloc = entry["final_alloc"]
    score = _score_entry(final_alloc, weights)
    target_value = final_alloc[target_idx] if target_idx is not None else -1
    secondary_value = final_alloc[secondary_idx] if secondary_idx is not None else -1
    return (
        score,
        target_value,
        secondary_value,
        entry["final_total"],
        tuple(final_alloc),
        tuple(entry["effective_work"]),
        tuple(entry["dim_feed_counts"]),
        tuple(entry["plan_level_preference"]),
    )


def _insert_top(top_entries: list[dict], entry: dict, weights: list[float], target_idx: int | None, top_n: int):
    top_entries.append(entry)
    top_entries.sort(key=lambda item: _entry_key(item, weights, target_idx), reverse=True)
    del top_entries[top_n:]


def _best_dim_key(entry: dict, dim_index: int, secondary_idx: int | None = None) -> tuple:
    final_alloc = entry["final_alloc"]
    secondary_value = final_alloc[secondary_idx] if secondary_idx is not None else -1
    return (
        final_alloc[dim_index],
        secondary_value,
        entry["final_total"],
        tuple(final_alloc),
        tuple(entry["effective_work"]),
        tuple(entry["dim_feed_counts"]),
        tuple(entry["plan_level_preference"]),
    )


def optimize_feed_distributions(
    base_alloc: list[int],
    weights: list[float],
    params: EvolutionParams,
    target_dim: str | None = None,
    best_secondary_dim: str | None = None,
) -> dict:
    if params.total_feeds <= 0:
        raise ValueError("总喂食颗数必须 ≥ 1")
    if params.fold_scale_den <= 0:
        raise ValueError("折算分母必须 ≥ 1")
    if params.top_n < 1:
        raise ValueError("最优解显示条数必须 ≥ 1")

    weights = normalize_weights(weights)
    target_idx = _target_index(target_dim)
    best_secondary_idx = _target_index(best_secondary_dim)
    states = _reachable_work_states(
        params.total_feeds,
        _normalize_effects(params.medicine_effects),
        params.fold_scale_num,
        params.fold_scale_den,
        params.effective_single_cap,
    )

    top_entries: list[dict] = []
    best_by_dim: dict[str, dict | None] = {name: None for name in DIM_NAMES}

    for state in states:
        entry = incubate_alloc(base_alloc, state["plan"], params)
        entry["score"] = _score_entry(entry["final_alloc"], weights)

        if len(top_entries) < params.top_n or _entry_key(entry, weights, target_idx) > _entry_key(
            top_entries[-1], weights, target_idx
        ):
            _insert_top(top_entries, entry, weights, target_idx, params.top_n)

        for dim_index, dim_name in enumerate(DIM_NAMES):
            best = best_by_dim[dim_name]
            secondary_idx = best_secondary_idx
            if secondary_idx == dim_index:
                secondary_idx = None
            if best is None or _best_dim_key(entry, dim_index, secondary_idx) > _best_dim_key(
                best, dim_index, secondary_idx
            ):
                best_by_dim[dim_name] = dict(entry)

    return {
        "top_results": top_entries,
        "best_by_dim": best_by_dim,
        "searched_states": len(states),
    }


def analyze_evolution_feeding(
    base_alloc: list[int],
    weights: list[float],
    params: EvolutionParams,
    target_dim: str | None = None,
    best_secondary_dim: str | None = None,
) -> dict:
    base = normalize_base_alloc(base_alloc, params)
    optimized = optimize_feed_distributions(
        base,
        weights,
        params,
        target_dim=target_dim,
        best_secondary_dim=best_secondary_dim,
    )
    return {
        "base_alloc": base,
        "weights": weights,
        "target_dim": target_dim or "",
        "best_secondary_dim": best_secondary_dim or "",
        "top_results": optimized["top_results"],
        "best_by_dim": optimized["best_by_dim"],
        "searched_states": optimized["searched_states"],
    }
