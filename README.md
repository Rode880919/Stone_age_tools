# sa_pet_assistant

`sa_pet_assistant` 是一个基于 `tkinter` 的桌面工具，用于石器时代宠物相关计算。

当前项目提供 4 份说明文档：

- [README_user.md](./README_user.md)：偏玩家 / 普通使用者
- [README_dev.md](./README_dev.md)：偏开发者 / 维护者
- [fusion_opt.md](./fusion_opt.md)：融合蛋喂药页面的两种优化方式与孵化公式说明
- [pet_basics.md](./pet_basics.md)：宠物成长、转生、融合、喂药与随机机制的基础知识说明

## 快速开始

在项目目录下运行：

```bash
python main.py
```

或使用演示数据启动：

```bash
python main.py --demo
```

## 页面一览

当前界面包含 5 个页面：

- 反推计算
- 成长模拟
- 转生模拟
- 融合成蛋
- 融合蛋喂药

## 术语约定

为避免歧义，项目内文档统一使用下面这组术语：

- `成长率`：宠物的 `V / S / T / D` 四项成长数值
- `VSTD`：四项成长率之和，即 `V + S + T + D`
- `蛋基础成长`：融合完成后、喂药前的蛋面 `V / S / T / D`
- `孵化后成长` 或 `孵化后成长档`：按 `PET_getEvolutionAns()` 计算后的四项结果，不含出生后 10 点随机加点
- `出生后 10 点随机`：宠物出生时额外分配的 10 点随机加点，不属于成长档本身

在“融合蛋喂药”页面中，优化目标统一指：`孵化后成长`，不是 `蛋基础成长`。

## 打包

项目内含 `PyInstaller` 打包脚本：

```bash
bash build.sh
```

默认输出：

```text
dist/sa_pet_assistant.exe
```
