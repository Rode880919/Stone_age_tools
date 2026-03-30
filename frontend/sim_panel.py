"""
sim_panel.py — 宠物成长正向模拟面板

只展示 140 级时的结果，5 行 × 8 列紧凑表格：
    属性  | 最弱 | P5 | P25 | P50 | P75 | P95 | 最强
    生命  |  …   | …  |  …  |  …  |  …  |  …  |  …
    攻击  |  …   | …  |  …  |  …  |  …  |  …  |  …
    防御  |  …   | …  |  …  |  …  |  …  |  …  |  …
    敏捷  |  …   | …  |  …  |  …  |  …  |  …  |  …
    成长  |  …   | …  |  …  |  …  |  …  |  …  |  …
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from backend.simulator import simulate_lv140, get_rank_normal, RANK_RAND_TBL

_ROW_TAGS = {
    "生命": ("hp", "#dbeeff"),
    "攻击": ("atk", "#fff4d6"),
    "防御": ("def", "#d6f5e0"),
    "敏捷": ("spd", "#fde8e8"),
    "成长": ("gro", "#ede8fd"),
}


class SimPanel(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, padding=8, **kwargs)
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_input()
        self._build_result()

    def _build_input(self):
        inp = ttk.LabelFrame(self, text="宠物参数（enemybase 原始数值）", padding=10)
        inp.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for col in range(12):
            inp.columnconfigure(col, weight=0)
        inp.columnconfigure(11, weight=1)

        params = [("INITNUM", "ini"), ("V", "v"), ("S", "s"), ("T", "t"), ("D", "d")]
        self._vars: dict[str, tk.StringVar] = {}
        for i, (label, key) in enumerate(params):
            ttk.Label(inp, text=label, font=("", 9, "bold")).grid(
                row=0, column=i * 2, padx=(0 if i == 0 else 12, 4), sticky="e"
            )
            var = tk.StringVar()
            ttk.Entry(inp, textvariable=var, width=6, justify="center").grid(row=0, column=i * 2 + 1)
            self._vars[key] = var

        ttk.Label(inp, text="模拟次数").grid(row=1, column=0, sticky="e", pady=(10, 0))
        self._n_var = tk.StringVar(value="2000")
        ttk.Entry(inp, textvariable=self._n_var, width=8, justify="center").grid(
            row=1, column=1, sticky="w", pady=(10, 0)
        )

        ttk.Button(inp, text="开始模拟", width=12, command=self._on_simulate).grid(
            row=1, column=10, columnspan=2, sticky="e", pady=(10, 0)
        )

        self._info_var = tk.StringVar(value="")
        ttk.Label(inp, textvariable=self._info_var, foreground="#0055aa", wraplength=920, justify="left").grid(
            row=2, column=0, columnspan=12, sticky="w", pady=(8, 0)
        )

    def _build_result(self):
        result = ttk.LabelFrame(self, text="140 级模拟结果", padding=8)
        result.grid(row=1, column=0, sticky="nsew")
        result.columnconfigure(0, weight=1)
        result.rowconfigure(0, weight=1)

        pct_cols = ["最弱", "P5", "P25", "P50", "P75", "P95", "最强"]
        all_cols = ["stat"] + [f"p{i}" for i in range(7)]

        self._tree = ttk.Treeview(result, columns=all_cols, show="headings", height=6, selectmode="none")
        col_w = 108
        self._tree.heading("stat", text="属性")
        self._tree.column("stat", width=col_w, minwidth=col_w, anchor="center", stretch=True)

        for j, hd in enumerate(pct_cols):
            cid = f"p{j}"
            self._tree.heading(cid, text=hd)
            self._tree.column(cid, width=col_w, minwidth=col_w, anchor="center", stretch=True)

        for _, (tag, bg) in _ROW_TAGS.items():
            self._tree.tag_configure(tag, background=bg)

        self._tree.grid(row=0, column=0, sticky="nsew")

        self._status_var = tk.StringVar(value="请填入参数后点击「开始模拟」")
        ttk.Label(self, textvariable=self._status_var, foreground="gray").grid(row=2, column=0, sticky="w", pady=(6, 0))

    def _parse(self):
        try:
            ini = int(self._vars["ini"].get())
            v = int(self._vars["v"].get())
            s = int(self._vars["s"].get())
            t = int(self._vars["t"].get())
            d = int(self._vars["d"].get())
            n = int(self._n_var.get())
        except ValueError:
            messagebox.showerror("输入错误", "所有字段必须为整数")
            return None

        if not (5 <= ini <= 60):
            messagebox.showerror("输入错误", "INITNUM 范围：5~60")
            return None
        if any(x < 1 for x in (v, s, t, d)):
            messagebox.showerror("输入错误", "V/S/T/D 必须 ≥ 1")
            return None
        if not (1 <= n <= 50000):
            messagebox.showerror("输入错误", "模拟次数范围：1~50000")
            return None
        return ini, [v, s, t, d], n

    def _on_simulate(self):
        params = self._parse()
        if params is None:
            return

        ini, alloc, n = params
        vstd = sum(alloc)
        rank = get_rank_normal(vstd)
        flo, fhi = RANK_RAND_TBL[rank]
        self._info_var.set(f"VSTD={vstd}  Rank {rank}  fRand∈[{flo/100:.2f}, {fhi/100:.2f}]")

        self._tree.delete(*self._tree.get_children())
        self._status_var.set("模拟中，请稍候…")

        threading.Thread(target=self._sim_thread, args=(ini, alloc, n), daemon=True).start()

    def _sim_thread(self, ini, alloc, n):
        try:
            rows = simulate_lv140(ini, alloc, n=n)
            self.after(0, self._show_results, rows, n)
        except Exception as e:
            self.after(0, lambda: self._status_var.set(f"⚠ {e}"))

    def _show_results(self, rows: list[tuple], n: int):
        self._tree.delete(*self._tree.get_children())
        for row in rows:
            name = row[0]
            tag = _ROW_TAGS[name][0]
            self._tree.insert("", "end", values=row, tags=(tag,))
        self._status_var.set(f"{n} 次模拟完成（lv140）")
