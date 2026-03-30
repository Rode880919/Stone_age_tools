#!/bin/bash
cd "$(dirname "$0")"

echo "清理旧文件..."
rm -f build/*.aux build/*.log build/*.out build/*.toc build/*.pdf

echo "开始编译..."
xelatex -output-directory=build main.tex
xelatex -output-directory=build main.tex

if [ -f "build/main.pdf" ]; then
    cp build/main.pdf "build/石器时代战斗系统与宠物养成机制.pdf"
    echo "✓ PDF生成成功: build/石器时代战斗系统与宠物养成机制.pdf"
    ls -lh "build/石器时代战斗系统与宠物养成机制.pdf"
else
    echo "✗ PDF生成失败"
    exit 1
fi
