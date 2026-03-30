"""
matrix.py — 显示值 ↔ 原始点数线性代数

显示值公式（char/char.c CHAR_initcharWorkInt）：
    HP  = int((V*4 + S + T + D) / 100)
    ATK = int((S + T*0.1 + V*0.1 + D*0.05) / 100)
    DEF = int((T + S*0.1 + V*0.1 + D*0.05) / 100)
    SPD = int(D / 100)

矩阵 M：(V,S,T,D) -> (HP*100, ATK*100, DEF*100, SPD*100)
    M = [[4, 1, 1, 1],
         [0.1, 1, 0.1, 0.05],
         [0.1, 0.1, 1, 0.05],
         [0, 0, 0, 1]]

det(M) = 189/50，可逆。
"""

import numpy as np

_M = np.array([
    [4.0,   1.0,  1.0,  1.0 ],
    [0.1,   1.0,  0.1,  0.05],
    [0.1,   0.1,  1.0,  0.05],
    [0.0,   0.0,  0.0,  1.0 ],
], dtype=float)

_M_INV = np.linalg.inv(_M)


def display_to_raw(hp: int, atk: int, def_: int, spd: int) -> np.ndarray:
    """
    (hp, atk, def, spd) -> 近似原始点数 [V, S, T, D]（浮点）

    由于显示值经过 floor()，结果存在 ≈±200 的系统误差。
    """
    b = np.array([hp * 100, atk * 100, def_ * 100, spd * 100], dtype=float)
    return _M_INV @ b


def raw_to_display(V: float, S: float, T: float, D: float) -> tuple[int, int, int, int]:
    """
    原始点数 -> (hp, atk, def, spd)，向下取整。
    """
    hp  = int((V * 4 + S + T + D) / 100)
    atk = int((S + T * 0.1 + V * 0.1 + D * 0.05) / 100)
    def_ = int((T + S * 0.1 + V * 0.1 + D * 0.05) / 100)
    spd = int(D / 100)
    return hp, atk, def_, spd
