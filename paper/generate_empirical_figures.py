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


def crit_base(x: float, y: float, luck: float = 0.0, wcrit: float = 0.0) -> float:
    if x >= y:
        return math.sqrt(max((x - y) / 0.09, 0.0)) + luck + 0.5 * wcrit
    if y == 0:
        return 0.0
    return (math.sqrt(max((y - x) / 0.09, 0.0)) + 0.5 * wcrit) * (x / y) + luck


def crit_rate(x: float, y: float, luck: float = 0.0, wcrit: float = 0.0) -> float:
    work = math.floor(100.0 * crit_base(x, y, luck, wcrit)) - 1
    work = int(clip(work, 0, 9999))
    return work / 100.0


def counter_base(x: float, y: float) -> float:
    if x >= y:
        return math.sqrt(max((x - y) / 0.08, 0.0))
    if y == 0:
        return 0.0
    return math.sqrt(max((y - x) / 0.08, 0.0)) * (x / y)


def counter_rate(x: float, y: float, luck: float = 0.0, weapon_coeff: float = 10.0) -> float:
    raw = 0.1 * weapon_coeff * counter_base(x, y) + luck
    work = math.ceil(100.0 * raw) - 1
    work = int(clip(work, 0, 10000))
    return work / 100.0


def make_turn_region_table():
    vals = [80, 120, 160, 200, 240, 280, 320]
    cell_text = []
    cell_colors = []
    for wa in vals:
        row_text = []
        row_colors = []
        for wb in vals:
            if 0.7 * wa > wb:
                row_text.append('必先')
                row_colors.append('#d9d9d9')
            elif wa < 0.7 * wb:
                row_text.append('不先')
                row_colors.append('#f0f0f0')
            else:
                row_text.append('重叠')
                row_colors.append('#ffffff')
        cell_text.append(row_text)
        cell_colors.append(row_colors)

    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.axis('off')
    table = ax.table(
        cellText=cell_text,
        cellColours=cell_colors,
        rowLabels=[str(v) for v in vals],
        colLabels=[str(v) for v in vals],
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.1, 1.6)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#555555')
        if r == 0 or c == -1:
            cell.set_facecolor('#e6e6e6')
            cell.set_text_props(weight='bold')
    ax.set_title('默认乱敏规则下的先手区间判别表')
    ax.text(0.5, -0.08, '行: 攻方参照敏 + 20；列: 守方参照敏 + 20',
            ha='center', va='top', transform=ax.transAxes, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / 'turn_region_table.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


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


def make_crit_slice():
    y = 200
    xs = np.arange(50, 451)
    ys = np.array([crit_rate(float(x), float(y), 0.0, 0.0) for x in xs])
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.step(xs, ys, where='mid', color='black', linewidth=1.8)
    ax.axvline((2.0 / 3.0) * y, color='#999999', linestyle=':', linewidth=1.0)
    ax.axvline(y, color='#777777', linestyle='--', linewidth=1.0)
    ax.set_xlim(50, 450)
    ax.set_ylim(0, 100)
    ax.set_xlabel('攻方固定敏 att_dex')
    ax.set_ylabel('会心率 (%)')
    ax.set_title('人打人源码离散会心率切片图: def_dex=200, L=0, C=0')
    ax.grid(True, color='#dddddd', linewidth=0.6)
    ax.text((2.0 / 3.0) * y + 4, 8, 'att_dex = 2 def_dex / 3', fontsize=8.5, color='#555555')
    ax.text(y + 4, 8, 'att_dex = def_dex', fontsize=8.5, color='#555555')
    fig.tight_layout()
    fig.savefig(OUT / 'crit_slice_y200.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


import sys
sys.path.append('/home/jzhou/sa/tools/pet_reverse')
from backend.simulator import calc_transmigration
from backend.fusion import calc_fusion_egg_base
from backend.evolution import EvolutionParams, incubate_alloc


def split_total(total, weights=(4, 3, 2, 1)):
    base = [total * w // sum(weights) for w in weights]
    while sum(base) < total:
        for i in range(len(base)):
            if sum(base) < total:
                base[i] += 1
    return base


def wrong_sub_average_then_discount(main_level, main_alloc, sub1_level, sub1_alloc, sub2_level, sub2_alloc):
    def scale80(alloc):
        return tuple((x * 8) // 10 for x in alloc)
    def scale60(alloc):
        return tuple((x * 6) // 10 for x in alloc)
    def scale40(alloc):
        return tuple((x * 4) // 10 for x in alloc)
    main_adj = scale80(tuple(main_alloc)) if main_level < 80 else tuple(main_alloc)
    main_contrib = scale60(main_adj)
    sub_avg_raw = tuple((int(sub1_alloc[i]) + int(sub2_alloc[i])) // 2 for i in range(4))
    if sub1_level < 80 and sub2_level < 80:
        sub_avg_used = scale80(sub_avg_raw)
    else:
        sub_avg_used = sub_avg_raw
    sub_contrib = scale40(sub_avg_used)
    return tuple(main_contrib[i] + sub_contrib[i] for i in range(4))


def make_counter_slice():
    y = 200
    xs = np.arange(50, 451)
    ys = np.array([counter_rate(float(x), float(y), 0.0, 10.0) for x in xs])
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.step(xs, ys, where='mid', color='black', linewidth=1.8)
    ax.axvline((2.0 / 3.0) * y, color='#999999', linestyle=':', linewidth=1.0)
    ax.axvline(y, color='#777777', linestyle='--', linewidth=1.0)
    ax.set_xlim(50, 450)
    ax.set_ylim(0, 100)
    ax.set_xlabel('攻方固定敏 att_dex')
    ax.set_ylabel('反击率 (%)')
    ax.set_title('人打人源码离散反击率切片图: def_dex=200, L=0, F=10')
    ax.grid(True, color='#dddddd', linewidth=0.6)
    ax.text((2.0 / 3.0) * y + 4, 8, 'att_dex = 2 def_dex / 3', fontsize=8.5, color='#555555')
    ax.text(y + 4, 8, 'att_dex = def_dex', fontsize=8.5, color='#555555')
    fig.tight_layout()
    fig.savefig(OUT / 'counter_slice_y200_f10.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


def make_trans_table():
    pet_alloc = [37, 33, 28, 22]
    mm_totals = [80, 100, 120, 130, 140, 150]
    rows = []
    for total in mm_totals:
        stone = split_total(total)
        info1 = calc_transmigration(pet_alloc, stone, 130, 0, ans_cap=999)
        info2 = calc_transmigration(pet_alloc, stone, 130, 1, ans_cap=999)
        rows.append([
            str(total),
            str(info1['ans']),
            str(min(info1['ans'], 150)),
            str(info2['ans']),
            str(min(info2['ans'], 200)),
        ])
    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    ax.axis('off')
    table = ax.table(
        cellText=rows,
        colLabels=['MM 总和', '首转原始 A', '首转封顶后', '二转原始 A', '二转封顶后'],
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.08, 1.55)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#555555')
        if r == 0:
            cell.set_facecolor('#e6e6e6')
            cell.set_text_props(weight='bold')
    ax.set_title('转生能力值参数扫描表（原宠总和=120，等级=130）')
    ax.text(0.5, -0.08, '原宠固定为 (37, 33, 28, 22)；MM 维持 4:3:2:1 分配比例。',
            ha='center', va='top', transform=ax.transAxes, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / 'transmigration_scan_table.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


def make_trans_alloc_loss_table():
    pet_alloc = [37, 33, 28, 22]
    stone = split_total(150)
    total1 = min(sum(stone), 150)
    total2 = sum(pet_alloc)
    total_weight = total1 + total2 * 4
    rows = []
    for ans in [140, 145, 150, 155, 160]:
        new_alloc = [
            ans * (stone[d] + pet_alloc[d] * 4) // total_weight
            for d in range(4)
        ]
        rows.append([
            str(ans),
            '/'.join(map(str, new_alloc)),
            str(sum(new_alloc)),
            str(ans - sum(new_alloc)),
        ])
    fig, ax = plt.subplots(figsize=(8.1, 3.5))
    ax.axis('off')
    table = ax.table(
        cellText=rows,
        colLabels=['A*', '分配后四维', '四维总和', '取整损失'],
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.08, 1.55)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#555555')
        if r == 0:
            cell.set_facecolor('#e6e6e6')
            cell.set_text_props(weight='bold')
    ax.set_title('转生能力值分配后的取整损失表')
    ax.text(0.5, -0.08, '原宠固定为 (37, 33, 28, 22)；MM 总和固定 150，分配比例 4:3:2:1。',
            ha='center', va='top', transform=ax.transAxes, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / 'transmigration_alloc_loss_table.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


def make_fusion_rounding_table():
    cases = [
        {
            'name': '案例A',
            'main_level': 100,
            'main_alloc': [40, 35, 30, 25],
            'sub1_level': 60,
            'sub1_alloc': [31, 27, 23, 19],
            'sub2_level': 70,
            'sub2_alloc': [30, 26, 22, 18],
        },
        {
            'name': '案例B',
            'main_level': 100,
            'main_alloc': [41, 34, 29, 24],
            'sub1_level': 79,
            'sub1_alloc': [33, 29, 25, 21],
            'sub2_level': 79,
            'sub2_alloc': [32, 28, 24, 20],
        },
        {
            'name': '案例C',
            'main_level': 100,
            'main_alloc': [39, 36, 28, 23],
            'sub1_level': 50,
            'sub1_alloc': [28, 25, 21, 17],
            'sub2_level': 78,
            'sub2_alloc': [27, 24, 20, 16],
        },
    ]
    rows = []
    for case in cases:
        correct = calc_fusion_egg_base(
            case['main_level'], case['main_alloc'],
            case['sub1_level'], case['sub1_alloc'],
            case['sub2_level'], case['sub2_alloc'],
        )['egg_base']
        wrong = wrong_sub_average_then_discount(
            case['main_level'], case['main_alloc'],
            case['sub1_level'], case['sub1_alloc'],
            case['sub2_level'], case['sub2_alloc'],
        )
        rows.append([
            case['name'],
            f"{case['sub1_level']}/{case['sub2_level']}",
            '/'.join(map(str, correct)),
            '/'.join(map(str, wrong)),
        ])
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    ax.axis('off')
    table = ax.table(
        cellText=rows,
        colLabels=['案例', '副宠等级', 'gmsv 顺序', '先平均再 0.8（误解）'],
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.06, 1.55)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#555555')
        if r == 0:
            cell.set_facecolor('#e6e6e6')
            cell.set_text_props(weight='bold')
    ax.set_title('低等级副宠融合时的取整顺序对比表')
    ax.text(0.5, -0.08, '各行给出蛋基础 V/S/T/D。gmsv 会先对每只低等级副宠做折扣，再参与平均。',
            ha='center', va='top', transform=ax.transAxes, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / 'fusion_rounding_table.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


def make_hatch_case_table():
    params = EvolutionParams()
    cases = [
        ('均衡蛋面', [30, 30, 30, 30], [[10, 0, 0, 0, 0]] * 4),
        ('高基础', [45, 40, 35, 30], [[0, 0, 0, 0, 10]] * 4),
        ('压缩压力', [60, 50, 20, 20], [[0, 0, 0, 0, 10]] * 4),
    ]
    rows = []
    for name, base, plan in cases:
        result = incubate_alloc(base, plan, params)
        rows.append([
            name,
            str(sum(result['folded_work_raw'])),
            '是' if result['triggered_work_total_cap'] else '否',
            str(result['final_total']),
            '是' if result['triggered_final_total_cap'] else '否',
            '/'.join(map(str, result['final_alloc'])),
        ])
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    ax.axis('off')
    table = ax.table(
        cellText=rows,
        colLabels=['案例', 'u_i 总和', '触发 50 压缩', '最终总和', '触发 150 压缩', '最终 h'],
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.05, 1.55)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#555555')
        if r == 0:
            cell.set_facecolor('#e6e6e6')
            cell.set_text_props(weight='bold')
    ax.set_title('默认 40 药规则下的孵化案例表')
    ax.text(0.5, -0.08, '默认药效参数下，折算工作值总和最多只有 35，因此 50 压缩在实证上处于休眠状态。',
            ha='center', va='top', transform=ax.transAxes, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / 'hatch_case_table.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


def make_hatch_threshold_table():
    params = EvolutionParams()
    plan = [[0, 0, 0, 0, 0] for _ in range(4)]
    plan[3][4] = 40

    def split_three(total):
        a = total // 3
        b = total // 3
        c = total - a - b
        return [a, b, c]

    rows = []
    for other_total in [30, 45, 60, 75, 90]:
        others = split_three(other_total)
        found = None
        base_d = None
        for trial in range(1, 61):
            base = [others[0], others[1], others[2], trial]
            result = incubate_alloc(base, plan, params)
            if result['final_alloc'][3] >= 60:
                found = result
                base_d = trial
                break
        if found is None:
            rows.append([str(other_total), '-', '-', '-'])
        else:
            rows.append([
                str(other_total),
                str(base_d),
                '/'.join(map(str, found['final_alloc'])),
                str(found['final_total']),
            ])
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    ax.axis('off')
    table = ax.table(
        cellText=rows,
        colLabels=['其余三项总和', 'D 最小基础值', '最终孵化四维', '最终总和'],
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.08, 1.55)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#555555')
        if r == 0:
            cell.set_facecolor('#e6e6e6')
            cell.set_text_props(weight='bold')
    ax.set_title('默认 40 药规则下单项到 60 的基础阈值表')
    ax.text(0.5, -0.08, '固定把 40 颗五级药全部喂给 D，其余三项基础成长尽量均分。',
            ha='center', va='top', transform=ax.transAxes, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / 'hatch_threshold_table.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


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


def make_hit_crit_table():
    y = 200
    xs = [80, 120, 133, 160, 200, 240, 280, 320, 400]

    def hit_sign(x):
        if x < y:
            return '升'
        if x == 2 * y:
            return '平'
        if x < 2 * y:
            return '降'
        return '升'

    def crit_sign(x):
        pivot = (2.0 * y) / 3.0
        if abs(x - pivot) < 1e-9:
            return '平'
        if x < pivot:
            return '升'
        if x < y:
            return '降'
        return '升'

    def counter_sign(x):
        pivot = (2.0 * y) / 3.0
        if abs(x - pivot) < 1e-9:
            return '平'
        if x < pivot:
            return '升'
        if x < y:
            return '降'
        return '升'

    rows = []
    for x in xs:
        rows.append([
            str(x),
            f"{hit_rate(float(x), float(y), 0.0):.2f}",
            f"{crit_rate(float(x), float(y), 0.0, 0.0):.2f}",
            f"{counter_rate(float(x), float(y), 0.0, 10.0):.2f}",
            hit_sign(x),
            crit_sign(float(x)),
            counter_sign(float(x)),
        ])
    fig, ax = plt.subplots(figsize=(10.8, 4.3))
    ax.axis('off')
    table = ax.table(
        cellText=rows,
        colLabels=['攻方 att_dex', '命中率', '会心率', '反击率(F=10)', '命中导数', '会心导数', '反击导数'],
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.8)
    table.scale(1.02, 1.52)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#555555')
        if r == 0:
            cell.set_facecolor('#e6e6e6')
            cell.set_text_props(weight='bold')
    ax.set_title('人打人源码离散概率表: def_dex=200, L=0, C=0, F=10')
    ax.text(0.5, -0.08, '符号列使用连续化主体的一阶导号；数值列按源码离散口径直接计算。',
            ha='center', va='top', transform=ax.transAxes, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / 'hit_crit_table_y200.png', dpi=220, bbox_inches='tight')
    plt.close(fig)


def main():
    make_turn_region_table()
    make_dodge_heatmap()
    make_hit_slice()
    make_crit_slice()
    make_counter_slice()
    make_trans_table()
    make_trans_alloc_loss_table()
    make_fusion_rounding_table()
    make_hatch_case_table()
    make_hatch_threshold_table()
    make_hit_crit_table()
    print('已生成图表到', OUT)


if __name__ == '__main__':
    main()
