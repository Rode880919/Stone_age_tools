from __future__ import annotations

import math
from pathlib import Path
from typing import Callable

import numpy as np

OUT_DIR = Path('/home/jzhou/sa/tools/pet_reverse/battle_heatmaps')
REPORT = Path('/home/jzhou/sa/tools/pet_reverse/battle_heatmaps.md')

DEX_MIN = 0
DEX_MAX = 600
DEX_STEP = 2
DEX_VALUES = np.arange(DEX_MIN, DEX_MAX + DEX_STEP, DEX_STEP, dtype=float)

CELL = 2
LEFT = 72
TOP = 28
RIGHT = 24
BOTTOM = 58

BLUE = np.array((49, 54, 149), dtype=float)
CYAN = np.array((69, 117, 180), dtype=float)
YELLOW = np.array((254, 224, 144), dtype=float)
ORANGE = np.array((252, 141, 89), dtype=float)
RED = np.array((215, 48, 39), dtype=float)


def dodge_base(att_dex: float, def_dex: float) -> float:
    if def_dex >= att_dex:
        big = def_dex
        small = att_dex
        wari = 1.0
    else:
        big = att_dex
        small = def_dex
        wari = 0.0 if big <= 0 else small / big
    work = max((big - small) / 0.02, 0.0)
    return math.sqrt(work) * wari


def crit_base(att_dex: float, def_dex: float) -> float:
    if att_dex >= def_dex:
        big = att_dex
        small = def_dex
        wari = 1.0
    else:
        big = def_dex
        small = att_dex
        wari = 0.0 if big <= 0 else small / big
    work = max((big - small) / 0.09, 0.0)
    return math.sqrt(work) * wari


def counter_base(att_dex: float, def_dex: float) -> float:
    if att_dex >= def_dex:
        big = att_dex
        small = def_dex
        wari = 1.0
    else:
        big = def_dex
        small = att_dex
        wari = 0.0 if big <= 0 else small / big
    work = max((big - small) / 0.08, 0.0)
    return math.sqrt(work) * wari


def clip_percent(value: float, upper: float) -> float:
    return max(0.01, min(value, upper))


def make_matrix(func: Callable[[float, float], float]) -> np.ndarray:
    mat = np.zeros((len(DEX_VALUES), len(DEX_VALUES)), dtype=float)
    for yi, def_dex in enumerate(DEX_VALUES):
        for xi, att_dex in enumerate(DEX_VALUES):
            mat[yi, xi] = func(att_dex, def_dex)
    return mat


def color_for(value: float, vmin: float, vmax: float) -> str:
    t = 0.0 if vmax <= vmin else (value - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    if t < 0.33:
        local = t / 0.33
        color = BLUE * (1 - local) + CYAN * local
    elif t < 0.66:
        local = (t - 0.33) / 0.33
        color = CYAN * (1 - local) + YELLOW * local
    else:
        local = (t - 0.66) / 0.34
        blend = YELLOW * (1 - local) + ORANGE * local
        color = blend * (1 - local * 0.4) + RED * (local * 0.4)
    r, g, b = np.clip(color.astype(int), 0, 255)
    return f'#{r:02x}{g:02x}{b:02x}'


def render_svg(matrix: np.ndarray, title: str, subtitle: str, out_path: Path, vmax: float, legend_label: str) -> None:
    rows, cols = matrix.shape
    plot_w = cols * CELL
    plot_h = rows * CELL
    width = LEFT + plot_w + RIGHT + 72
    height = TOP + plot_h + BOTTOM

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    lines.append('<style>')
    lines.append('text { font-family: "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "PingFang SC", "WenQuanYi Zen Hei", "DejaVu Sans", sans-serif; fill: #222; }')
    lines.append('.title { font-size: 18px; font-weight: 700; }')
    lines.append('.subtitle { font-size: 12px; fill: #444; }')
    lines.append('.tick { font-size: 11px; fill: #444; }')
    lines.append('.axis { font-size: 13px; font-weight: 600; }')
    lines.append('</style>')
    lines.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>')
    lines.append(f'<text class="title" x="{LEFT}" y="20">{title}</text>')
    lines.append(f'<text class="subtitle" x="{LEFT}" y="38">{subtitle}</text>')

    origin_x = LEFT
    origin_y = TOP + 18

    for yi in range(rows):
        y = origin_y + yi * CELL
        for xi in range(cols):
            x = origin_x + xi * CELL
            lines.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{color_for(matrix[yi, xi], 0.0, vmax)}" stroke="none"/>')

    lines.append(f'<rect x="{origin_x}" y="{origin_y}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#222" stroke-width="1"/>')

    tick_values = list(range(0, DEX_MAX + 1, 100))
    for tick in tick_values:
        idx = int(round((tick - DEX_MIN) / DEX_STEP))
        x = origin_x + idx * CELL
        yy = origin_y + plot_h - idx * CELL
        lines.append(f'<line x1="{x}" y1="{origin_y + plot_h}" x2="{x}" y2="{origin_y + plot_h + 5}" stroke="#444"/>')
        lines.append(f'<text class="tick" x="{x}" y="{origin_y + plot_h + 18}" text-anchor="middle">{tick}</text>')
        lines.append(f'<line x1="{origin_x - 5}" y1="{yy}" x2="{origin_x}" y2="{yy}" stroke="#444"/>')
        lines.append(f'<text class="tick" x="{origin_x - 10}" y="{yy + 4}" text-anchor="end">{tick}</text>')

    lines.append(f'<text class="axis" x="{origin_x + plot_w / 2}" y="{height - 12}" text-anchor="middle">攻击方装备后敏捷</text>')
    cy = origin_y + plot_h / 2
    lines.append(f'<text class="axis" x="18" y="{cy}" transform="rotate(-90 18 {cy})" text-anchor="middle">防守方装备后敏捷</text>')

    legend_x = origin_x + plot_w + 28
    legend_y = origin_y
    legend_h = plot_h
    for i in range(legend_h):
        frac = 1.0 - i / max(legend_h - 1, 1)
        val = frac * vmax
        lines.append(f'<rect x="{legend_x}" y="{legend_y + i}" width="16" height="1" fill="{color_for(val, 0.0, vmax)}" stroke="none"/>')
    lines.append(f'<rect x="{legend_x}" y="{legend_y}" width="16" height="{legend_h}" fill="none" stroke="#222" stroke-width="1"/>')
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        yy = legend_y + (1.0 - frac) * legend_h
        val = frac * vmax
        lines.append(f'<line x1="{legend_x + 16}" y1="{yy}" x2="{legend_x + 21}" y2="{yy}" stroke="#444"/>')
        lines.append(f'<text class="tick" x="{legend_x + 25}" y="{yy + 4}">{val:.0f}%</text>')
    lines.append(f'<text class="axis" x="{legend_x + 8}" y="{legend_y - 8}" text-anchor="middle">{legend_label}</text>')
    lines.append('</svg>')
    out_path.write_text('\n'.join(lines), encoding='utf-8')


def write_report() -> None:
    text = '''# 玩家对玩家敏捷热力图

这份报告只看 **玩家对玩家**，且横轴、纵轴都使用 **装备装备后的敏捷**，也就是源码里的 `CHAR_WORKFIXDEX`。

本组图统一采用下面的基准条件：

- 不考虑守方防御
- 不考虑醉酒
- 不考虑弓额外修正
- 不考虑命中修正 `WORKHITRIGHT`
- 不考虑职业技能附加修正
- 会心图固定 `武器会心值 = 0`
- 反击图分别给出 `武器系数 = 6 / 8 / 10`
- 敏捷范围改为 `0 ~ 600`

补充：

- 玩家幸运有效范围只有 `1~5`
- 这组图统一把幸运固定成 `0`，只展示敏捷基础体
- 真实玩家图形可以在此基础上，再叠加 `1~5` 的幸运修正

## 1. 幸运修正是否线性

当前源码下，幸运对玩家对玩家热力图的影响是 **线性的**。

### 1.1 回避

```text
回避率(x, y, L_def) = clip(H_dodge(x, y) + L_def, 0.01, 75.00)
```

也就是：守方每 `+1` 幸运，整张图整体上移 `+1` 个百分点，直到碰到 `75%` 上限。

这里的 `L_def` 对玩家有效范围是 `1~5`。

### 1.2 会心

幸运修正本身是线性的，但武器会心值 `C` 只有在 `x >= y` 时才是简单平移。更精确地说：

```text
若 x >= y：
  会心率 = clip(H_crit(x, y) + L_atk + 0.5*C, 0.01, 100.00)
否则：
  会心率 = clip(H_crit(x, y) + L_atk + 0.5*C*(x/y), 0.01, 100.00)
```

也就是：

- 攻方每 `+1` 幸运，整张图整体上移 `+1` 个百分点
- 但武器会心值 `C` 在攻方敏低于守方时，会再乘一次 `x / y`

本组会心图固定 `C = 0`，所以图面本身只展示敏捷基础体。

### 1.3 反击

```text
反击率(x, y, L_atk, F) = clip(H_counter_base(x, y) * 0.1 * F + L_atk, 0.01, 100.00)
```

也就是：攻方每 `+1` 幸运，整张图整体上移 `+1` 个百分点；武器系数 `F` 会按比例缩放整张图。

## 2. 玩家与宠物能否合并

**不建议直接合并。**

原因：

- 这组图是纯玩家 PVP 口径
- 玩家 / 宠物 / 敌人之间会触发 `0.6`、`0.8` 的身份缩放
- 在主 PVP 概率里，宠物通常又不直接吃玩家这一套幸运修正

所以这组图只适合纯玩家对玩家基准分析。

## 3. 热力图

### 3.1 回避率，守方幸运 = 0

![回避率基准图](battle_heatmaps/dodge_pvp_luck0.svg)

### 3.2 会心率，攻方幸运 = 0，武器会心值 = 0

![会心率基准图](battle_heatmaps/critical_pvp_luck0_wcrit0.svg)

### 3.3 反击率，攻方幸运 = 0，武器系数 = 6

![反击率 F6](battle_heatmaps/counter_pvp_factor6_luck0.svg)

### 3.4 反击率，攻方幸运 = 0，武器系数 = 8

![反击率 F8](battle_heatmaps/counter_pvp_factor8_luck0.svg)

### 3.5 反击率，攻方幸运 = 0，武器系数 = 10

![反击率 F10](battle_heatmaps/counter_pvp_factor10_luck0.svg)

## 4. 基础公式

### 4.1 回避基础体

```text
if y >= x:
  Big = y
  Small = x
  wari = 1
else:
  Big = x
  Small = y
  wari = Small / Big

Work = (Big - Small) / 0.02
H_dodge = sqrt(Work) * wari
```

### 4.2 会心基础体

```text
if x >= y:
  Big = x
  Small = y
  wari = 1
else:
  Big = y
  Small = x
  wari = Small / Big

Work = (Big - Small) / 0.09
H_crit = sqrt(Work) * wari
```

### 4.3 反击基础体

```text
if x >= y:
  Big = x
  Small = y
  wari = 1
else:
  Big = y
  Small = x
  wari = Small / Big

Work = (Big - Small) / 0.08
H_counter_base = sqrt(Work) * wari
```
'''
    REPORT.write_text(text, encoding='utf-8')


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dodge = make_matrix(lambda x, y: clip_percent(dodge_base(x, y), 75.0))
    crit = make_matrix(lambda x, y: clip_percent(crit_base(x, y), 100.0))
    counter6 = make_matrix(lambda x, y: clip_percent(counter_base(x, y) * 0.6, 100.0))
    counter8 = make_matrix(lambda x, y: clip_percent(counter_base(x, y) * 0.8, 100.0))
    counter10 = make_matrix(lambda x, y: clip_percent(counter_base(x, y) * 1.0, 100.0))

    render_svg(dodge, '玩家对玩家：回避率热力图', '基准条件：守方幸运=0，无弓、无命中修正、无额外状态；敏捷范围 0~600', OUT_DIR / 'dodge_pvp_luck0.svg', 75.0, '回避率')
    render_svg(crit, '玩家对玩家：会心率热力图', '基准条件：攻方幸运=0，武器会心值=0；敏捷范围 0~600', OUT_DIR / 'critical_pvp_luck0_wcrit0.svg', 100.0, '会心率')
    render_svg(counter6, '玩家对玩家：反击率热力图', '基准条件：攻方幸运=0，武器系数=6；敏捷范围 0~600', OUT_DIR / 'counter_pvp_factor6_luck0.svg', 100.0, '反击率')
    render_svg(counter8, '玩家对玩家：反击率热力图', '基准条件：攻方幸运=0，武器系数=8；敏捷范围 0~600', OUT_DIR / 'counter_pvp_factor8_luck0.svg', 100.0, '反击率')
    render_svg(counter10, '玩家对玩家：反击率热力图', '基准条件：攻方幸运=0，武器系数=10；敏捷范围 0~600', OUT_DIR / 'counter_pvp_factor10_luck0.svg', 100.0, '反击率')
    write_report()


if __name__ == '__main__':
    main()
