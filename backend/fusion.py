"""
fusion.py — 融合成蛋基础成长计算

严格按 gmsv 当前代码顺序计算，不合并中间步骤：
1. 若宠物等级 < 80，则每项先做 value * 8 // 10
2. 副宠部分先做逐项整数平均 sum // count
3. 再对副宠平均值逐项做 value * 4 // 10
4. 主宠修正值逐项做 value * 6 // 10
5. 两部分相加得到蛋的基础成长
6. 再按 PET_getEvolutionAns 的无喂药情形，得到孵化后成长档

这里不包含：
- PETFUSION_SetNewEgg() 里的单项 +-2 随机
- 出生时的 10 点随机分配
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.evolution import EvolutionParams, incubate_alloc

DIM_NAMES = ("V", "S", "T", "D")


@dataclass(frozen=True)
class FusionPet:
    level: int
    alloc: tuple[int, int, int, int]


def _alloc_tuple(values, label: str) -> tuple[int, int, int, int]:
    if len(values) != 4:
        raise ValueError(f"{label}成长必须是 4 维 [V, S, T, D]")
    alloc = tuple(int(v) for v in values)
    if any(v < 1 for v in alloc):
        raise ValueError(f"{label} V/S/T/D 必须 >= 1")
    return alloc


def _pet(level, alloc, label: str) -> FusionPet:
    level = int(level)
    if not (1 <= level <= 140):
        raise ValueError(f"{label}等级范围必须是 1~140")
    return FusionPet(level=level, alloc=_alloc_tuple(alloc, label))


def _mul_floor(value: int, numer: int, denom: int) -> int:
    return (value * numer) // denom


def _scale_alloc_floor(alloc: tuple[int, int, int, int], numer: int, denom: int) -> tuple[int, int, int, int]:
    return tuple(_mul_floor(value, numer, denom) for value in alloc)


def _sum_allocs(allocs: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    return tuple(sum(values[i] for values in allocs) for i in range(4))


def _calc_hatch_alloc(egg_base: tuple[int, int, int, int]) -> dict:
    zero_plan = [[0, 0, 0, 0, 0] for _ in range(4)]
    params = EvolutionParams()
    return incubate_alloc(list(egg_base), zero_plan, params)


def calc_fusion_egg_base(
    main_level: int,
    main_alloc,
    sub1_level: int,
    sub1_alloc,
    sub2_level: int | None = None,
    sub2_alloc=None,
) -> dict:
    main_pet = _pet(main_level, main_alloc, "主宠")
    sub_pets = [_pet(sub1_level, sub1_alloc, "副宠1")]

    if sub2_level is not None or sub2_alloc is not None:
        if sub2_level is None or sub2_alloc is None:
            raise ValueError("副宠2必须同时填写等级和 V/S/T/D，或全部留空")
        sub_pets.append(_pet(sub2_level, sub2_alloc, "副宠2"))

    main_adjusted = _scale_alloc_floor(main_pet.alloc, 8, 10) if main_pet.level < 80 else main_pet.alloc
    sub_adjusted = [
        _scale_alloc_floor(pet.alloc, 8, 10) if pet.level < 80 else pet.alloc
        for pet in sub_pets
    ]
    sub_sum = _sum_allocs(sub_adjusted)
    sub_count = len(sub_adjusted)
    sub_avg = tuple(value // sub_count for value in sub_sum)
    sub_contrib = _scale_alloc_floor(sub_avg, 4, 10)
    main_contrib = _scale_alloc_floor(main_adjusted, 6, 10)
    egg_base = tuple(main_contrib[i] + sub_contrib[i] for i in range(4))
    hatch = _calc_hatch_alloc(egg_base)

    return {
        "main": {
            "level": main_pet.level,
            "input_alloc": main_pet.alloc,
            "adjusted_alloc": main_adjusted,
            "contrib": main_contrib,
        },
        "subs": [
            {
                "name": f"副宠{idx + 1}",
                "level": pet.level,
                "input_alloc": pet.alloc,
                "adjusted_alloc": sub_adjusted[idx],
            }
            for idx, pet in enumerate(sub_pets)
        ],
        "sub_count": sub_count,
        "sub_sum": sub_sum,
        "sub_avg": sub_avg,
        "sub_contrib": sub_contrib,
        "egg_base": egg_base,
        "egg_vstd": sum(egg_base),
        "hatch_alloc": tuple(hatch["final_alloc"]),
        "hatch_vstd": hatch["final_total"],
        "rounding_steps": [
            "低于 80 级：每项先做 value * 8 // 10",
            f"副宠平均：每项做 (副宠和) // {sub_count}",
            "副宠贡献：每项做 value * 4 // 10",
            "主宠贡献：每项做 value * 6 // 10",
            "最终蛋成长 = 主宠贡献 + 副宠贡献",
            "孵化档位：按 PET_getEvolutionAns 的无喂药情形继续计算（不含 10 点随机）",
        ],
    }
