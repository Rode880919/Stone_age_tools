# 玩家对玩家敏捷热力图

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
