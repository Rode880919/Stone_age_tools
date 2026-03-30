#!/usr/bin/env bash
# build.sh — 用 PyInstaller 打包成 Windows 单 exe
# 需要在 conda 环境（sacalc）或含 numpy + pyinstaller 的环境中执行

set -e
cd "$(dirname "$0")"

ENV_PYTHON="${CONDA_PREFIX:-}/bin/python"
if [ ! -f "$ENV_PYTHON" ]; then
    ENV_PYTHON="python"
fi

echo ">>> 检查依赖..."
$ENV_PYTHON -c "import numpy, tkinter" || {
    echo "缺少 numpy，尝试安装..."
    pip install numpy
}

echo ">>> 开始打包..."
$ENV_PYTHON -m PyInstaller \
    --onefile \
    --windowed \
    --name "sa_pet_assistant" \
    --add-data "backend:backend" \
    --add-data "frontend:frontend" \
    --add-data "pet_basics.md:." \
    --add-data "README_user.md:." \
    main.py

echo ">>> 完成：dist/sa_pet_assistant.exe"
