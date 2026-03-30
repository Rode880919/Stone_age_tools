from pathlib import Path
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager

_FONT_PATH = '/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc'
font_manager.fontManager.addfont(_FONT_PATH)
_FONT_NAME = font_manager.FontProperties(fname=_FONT_PATH).get_name()

OUT = Path(__file__).resolve().parent / 'figures'
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    'font.family': _FONT_NAME,
    'font.size': 10,
    'axes.unicode_minus': False,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
})


def clip(v, lo, hi):
    return max(lo, min(hi, v))


def dodge_base(x: float, y: float) -> float:
    if y >= x:
        return math.sqrt(max((y - x) / 0.02, 0.0))
    if x == 0:
        return 0.0
    return math.sqrt(max((x - y) / 0.02, 0.0)) * (y / x)


def dodge_src_percent(x: float, y: float, luck: float = 0.0) -> float:
    work = math.floor(100.0 * (dodge_base(x, y) + luck))
    work = int(clip(work, 1, 7500))
    return work / 100.0


def hit_rate(x: float, y: float, luck: float = 0.0) -> float:
    return 100.0 - dodge_src_percent(x, y, luck)


def make_dodge_heatmap():
    xs = np.linspace(50, 400, 100)
    ys = np.linspace(50, 400, 100)
    X, Y = np.meshgrid(xs, ys)
    Z = np.zeros_like(X)
    for i in range(len(ys)):
        for j in range(len(xs)):
            Z[i, j] = dodge_src_percent(X[i, j], Y[i, j], 0.0)

    fig, ax = plt.subplots(figsize=(8.0, 6.5))
    contour = ax.contourf(X, Y, Z, levels=20, cmap='RdYlGn')
    cbar = fig.colorbar(contour, ax=ax)
    cbar.set_label('回避率 (%)')
    ax.set_xlabel('攻方固定敏 att_dex')
    ax.set_ylabel('防守方固定敏 def_dex')
    ax.set_title('人打人普通回避率热力图 (L=0)')
    ax.plot([50, 400], [50, 400], 'k--', linewidth=1.5, alpha=0.7, label='att_dex = def_dex')
    ax.legend(loc='upper left')
    fig.tight_layout()
    fig.savefig(OUT / 'dodge_heatmap.png', dpi=220, bbox_inches='tight')
    plt.close(fig)
    print('✓ 生成: dodge_heatmap.png')


def make_hit_slice():
    y = 200
    xs = np.arange(50, 451)
    ys = np.array([hit_rate(float(x), float(y), 0.0) for x in xs])
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.step(xs, ys, where='mid', color='black', linewidth=1.8)
    ax.axvline(y, color='#777777', linestyle='--', linewidth=1.0)
    ax.axvline(2 * y, color='#999999', linestyle=':', linewidth=1.0)
    ax.set_xlim(50, 450)
    ax.set_ylim(0, 100)
    ax.set_xlabel('攻方固定敏 att_dex')
    ax.set_ylabel('命中率 (%)')
    ax.set_title('人打人源码离散命中率切片图: def_dex=200, L=0')
    ax.grid(True, color='#dddddd', linewidth=0.6)
    ax.text(y + 4, 12, 'att_dex = def_dex', fontsize=8.5, color='#555555')
    ax.text(2 * y + 4, 12, 'att_dex = 2 def_dex', fontsize=8.5, color='#555555')
    fig.tight_layout()
    fig.savefig(OUT / 'hit_slice_y200.png', dpi=220, bbox_inches='tight')
    plt.close(fig)
    print('✓ 生成: hit_slice_y200.png')


if __name__ == '__main__':
    print('开始生成基础可视化图表...')
    make_dodge_heatmap()
    make_hit_slice()
    print(f'\n所有图表已生成到: {OUT}')
