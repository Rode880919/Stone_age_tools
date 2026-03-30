"""
input_panel.py — 动态多等级四维输入表格

支持用户填入任意数量（≥2）的等级数据行：
    等级 | HP | ATK | DEF | SPD | [删除]
"""

import tkinter as tk
from tkinter import ttk, messagebox


_FIELDS = ["等级", "HP", "ATK", "DEF", "SPD"]
_COL_WIDTHS = [7, 7, 7, 7, 7]
_DEFAULT_ROWS = [
    (1, "", "", "", ""),
    (140, "", "", "", ""),
]


class InputPanel(ttk.LabelFrame):
    def __init__(self, master, on_calculate, **kwargs):
        super().__init__(master, text="输入宠物状态（至少填写两个不同等级）", padding=10, **kwargs)
        self._on_calculate = on_calculate
        self._rows: list[_InputRow] = []
        for col in range(7):
            self.columnconfigure(col, weight=0)
        self.columnconfigure(6, weight=1)
        self._build_header()
        self._build_controls()
        for lv, *vals in _DEFAULT_ROWS:
            self._add_row(lv, *vals)

    def _build_header(self):
        for col, (name, w) in enumerate(zip(_FIELDS, _COL_WIDTHS)):
            ttk.Label(self, text=name, font=("", 9, "bold"), anchor="center", width=w).grid(
                row=0, column=col, padx=4, pady=(0, 4)
            )
        ttk.Label(self, text="删除", font=("", 9, "bold"), anchor="center", width=4).grid(row=0, column=5, padx=4, pady=(0, 4))

    def _build_controls(self):
        self._ctrl_frame = ttk.Frame(self)
        self._ctrl_frame.grid(row=999, column=0, columnspan=7, sticky="ew", pady=(10, 0))
        self._ctrl_frame.columnconfigure(3, weight=1)

        ttk.Button(self._ctrl_frame, text="添加行", width=10, command=self._add_row).grid(
            row=0, column=0, sticky="w"
        )
        self._trans_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self._ctrl_frame, text="转生宠物", variable=self._trans_var).grid(
            row=0, column=1, sticky="w", padx=(10, 0)
        )
        self._hint_var = tk.StringVar(value="支持填写任意多个等级，回车可直接触发计算")
        ttk.Label(self._ctrl_frame, textvariable=self._hint_var, foreground="#0055aa").grid(
            row=0, column=2, sticky="w", padx=(12, 0)
        )
        ttk.Button(self._ctrl_frame, text="开始计算", width=12, command=self._on_calculate).grid(
            row=0, column=4, sticky="e"
        )

    @property
    def transmigrated(self) -> bool:
        return self._trans_var.get()

    def _add_row(self, lv="", hp="", atk="", df="", spd=""):
        row_idx = len(self._rows) + 1
        row = _InputRow(self, row_idx, lv, hp, atk, df, spd, on_delete=self._delete_row, on_enter=self._on_calculate)
        self._rows.append(row)
        self._repack_controls()

    def _delete_row(self, row: "_InputRow"):
        if len(self._rows) <= 2:
            messagebox.showwarning("提示", "至少保留两行数据")
            return
        row.destroy()
        self._rows.remove(row)
        for i, r in enumerate(self._rows):
            r.reposition(i + 1)
        self._repack_controls()

    def _repack_controls(self):
        self._ctrl_frame.grid(row=len(self._rows) + 1, column=0, columnspan=7, sticky="ew", pady=(10, 0))

    def get_values(self) -> list[tuple[int, int, int, int, int]] | None:
        result = []
        for row in self._rows:
            vals = row.get()
            if vals is None:
                return None
            result.append(vals)

        levels = [v[0] for v in result]
        if len(set(levels)) < len(levels):
            messagebox.showerror("输入错误", "存在重复的等级，请确保每行等级唯一")
            return None
        if len(result) < 2:
            messagebox.showerror("输入错误", "至少需要两行数据")
            return None

        for lv, hp, atk, df, spd in result:
            if not (1 <= lv <= 140):
                messagebox.showerror("输入错误", f"等级必须在 1~140 之间（当前：{lv}）")
                return None
            if any(v < 0 for v in (hp, atk, df, spd)):
                messagebox.showerror("输入错误", "属性值不能为负数")
                return None

        return sorted(result, key=lambda x: x[0])

    def set_example(self, rows: list[tuple]):
        for r in list(self._rows):
            r.destroy()
        self._rows.clear()
        for lv, hp, atk, df, spd in rows:
            self._add_row(lv, hp, atk, df, spd)


class _InputRow:
    def __init__(self, parent, row_idx, lv, hp, atk, df, spd, on_delete, on_enter):
        self._parent = parent
        self._on_delete = on_delete
        self._widgets: list[tk.Widget] = []
        self._vars = [tk.StringVar(value=str(v)) for v in (lv, hp, atk, df, spd)]

        for col, (var, w) in enumerate(zip(self._vars, _COL_WIDTHS)):
            e = ttk.Entry(parent, textvariable=var, width=w, justify="center")
            e.grid(row=row_idx, column=col, padx=4, pady=3, sticky="w")
            e.bind("<Return>", lambda _: on_enter())
            self._widgets.append(e)

        btn = ttk.Button(parent, text="删", width=3, command=lambda: on_delete(self))
        btn.grid(row=row_idx, column=5, padx=4, pady=3, sticky="w")
        self._widgets.append(btn)
        self._row_idx = row_idx

    def reposition(self, row_idx: int):
        self._row_idx = row_idx
        for col, w in enumerate(self._widgets):
            w.grid(row=row_idx, column=col, sticky="w")

    def get(self) -> tuple[int, int, int, int, int] | None:
        try:
            vals = [int(v.get()) for v in self._vars]
            return tuple(vals)
        except (ValueError, tk.TclError):
            messagebox.showerror("输入错误", "请确保所有字段为整数")
            return None

    def destroy(self):
        for w in self._widgets:
            w.destroy()
        self._widgets.clear()
