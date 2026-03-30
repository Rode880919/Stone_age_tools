"""
main.py — 入口

用法：
    python main.py
    python main.py --demo      # 自动填入巴朵兰恩示例数据
"""

import sys
import os

# 保证从当前项目目录执行时能找到 backend/frontend 包
sys.path.insert(0, os.path.dirname(__file__))

from frontend.app import App


def main():
    app = App()

    if "--demo" in sys.argv:
        # 巴朵兰恩(普通) 示例：lv1 + lv70 + lv140 三组数据
        app._input.set_example([
            (1,   50,   12,   8,   7),
            (70,  683,  170, 115, 100),
            (140, 1316, 330, 222, 195),
        ])

    app.mainloop()


if __name__ == "__main__":
    main()
