"""
trans_panel.py — 宠物转生模拟面板

输入转生参数，模拟转生后宠物升到 140 级的属性分布。
结果展示格式与 sim_panel 相同：5 行 × 8 列分位数表。
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from backend.simulator import simulate_transmigration, calc_transmigration

_ROW_TAGS = {
    "生命": ("hp", "#dbeeff"),
    "攻击": ("atk", "#fff4d6"),
    "防御": ("def", "#d6f5e0"),
    "敏捷": ("spd", "#fde8e8"),
    "成长": ("gro", "#ede8fd"),
}


class TransPanel(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, padding=8, **kwargs)
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_input()
        self._build_result()

    def _build_input(self):
        inp = ttk.LabelFrame(self, text="转生参数", padding=10)
        inp.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for col in range(14):
            inp.columnconfigure(col, weight=0)
        inp.columnconfigure(13, weight=1)

        self._vars: dict[str, tk.StringVar] = {}

        ttk.Label(inp, text="宠物", font=("", 9, "bold")).grid(row=0, column=0, padx=(0, 8), sticky="e")
        pet_params = [("INITNUM", "ini"), ("V", "pv"), ("S", "ps"), ("T", "pt"), ("D", "pd")]
        for i, (label, key) in enumerate(pet_params):
            ttk.Label(inp, text=label).grid(row=0, column=1 + i * 2, padx=(8 if i > 0 else 0, 4), sticky="e")
            var = tk.StringVar()
            ttk.Entry(inp, textvariable=var, width=6, justify="center").grid(row=0, column=2 + i * 2)
            self._vars[key] = var

        ttk.Label(inp, text="MM", font=("", 9, "bold")).grid(row=1, column=0, padx=(0, 8), sticky="e", pady=(8, 0))
        mm_params = [("V", "mv"), ("S", "ms"), ("T", "mt"), ("D", "md")]
        for i, (label, key) in enumerate(mm_params):
            col_offset = 1
            ttk.Label(inp, text=label).grid(
                row=1,
                column=col_offset + (i + 1) * 2,
                padx=(8 if i > 0 else 0, 4),
                sticky="e",
                pady=(8, 0),
            )
            var = tk.StringVar()
            ttk.Entry(inp, textvariable=var, width=6, justify="center").grid(
                row=1, column=col_offset + (i + 1) * 2 + 1, pady=(8, 0)
            )
            self._vars[key] = var

        ttk.Label(inp, text="宠物等级").grid(row=2, column=0, sticky="e", pady=(10, 0))
        self._lv_var = tk.StringVar(value="140")
        ttk.Entry(inp, textvariable=self._lv_var, width=5, justify="center").grid(row=2, column=1, sticky="w", pady=(10, 0))

        ttk.Label(inp, text="转生次数").grid(row=2, column=2, sticky="e", padx=(12, 4), pady=(10, 0))
        self._trans_var = tk.StringVar(value="第1次")
        trans_combo = ttk.Combobox(
            inp,
            textvariable=self._trans_var,
            width=6,
            values=["第1次", "第2次"],
            state="readonly",
        )
        trans_combo.grid(row=2, column=3, sticky="w", pady=(10, 0))
        trans_combo.bind("<<ComboboxSelected>>", self._on_trans_change)

        ttk.Label(inp, text="转生能力上限").grid(row=2, column=4, sticky="e", padx=(12, 4), pady=(10, 0))
        self._ans_cap_var = tk.StringVar(value="150")
        ttk.Entry(inp, textvariable=self._ans_cap_var, width=6, justify="center").grid(row=2, column=5, sticky="w", pady=(10, 0))

        ttk.Label(inp, text="模拟次数").grid(row=2, column=6, sticky="e", padx=(12, 4), pady=(10, 0))
        self._n_var = tk.StringVar(value="2000")
        ttk.Entry(inp, textvariable=self._n_var, width=8, justify="center").grid(row=2, column=7, sticky="w", pady=(10, 0))

        ttk.Button(inp, text="开始模拟", width=12, command=self._on_simulate).grid(
            row=2, column=12, columnspan=2, sticky="e", pady=(10, 0)
        )

        self._info_var = tk.StringVar(value="")
        ttk.Label(inp, textvariable=self._info_var, foreground="#0055aa", wraplength=920, justify="left").grid(
            row=3, column=0, columnspan=14, sticky="w", pady=(8, 0)
        )

    def _default_ans_cap(self) -> int:
        return 150 if self._trans_var.get() == "第1次" else 200

    def _on_trans_change(self, _event=None):
        self._ans_cap_var.set(str(self._default_ans_cap()))

    def _build_result(self):
        result = ttk.LabelFrame(self, text="转生后 140 级模拟结果", padding=8)
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

        self._status_var = tk.StringVar(value="请填入转生参数后点击「开始模拟」")
        ttk.Label(self, textvariable=self._status_var, foreground="gray").grid(row=2, column=0, sticky="w", pady=(6, 0))

    def _parse(self):
        try:
            ini = int(self._vars["ini"].get())
            pv = int(self._vars["pv"].get())
            ps = int(self._vars["ps"].get())
            pt = int(self._vars["pt"].get())
            pd = int(self._vars["pd"].get())
            mv = int(self._vars["mv"].get())
            ms = int(self._vars["ms"].get())
            mt = int(self._vars["mt"].get())
            md = int(self._vars["md"].get())
            lv = int(self._lv_var.get())
            ans_cap = int(self._ans_cap_var.get())
            n = int(self._n_var.get())
        except ValueError:
            messagebox.showerror("输入错误", "所有字段必须为整数")
            return None

        if not (5 <= ini <= 60):
            messagebox.showerror("输入错误", "INITNUM 范围：5~60")
            return None
        if any(x < 1 for x in (pv, ps, pt, pd)):
            messagebox.showerror("输入错误", "宠物 V/S/T/D 必须 ≥ 1")
            return None
        if any(not (0 <= x <= 50) for x in (mv, ms, mt, md)):
            messagebox.showerror("输入错误", "MM V/S/T/D 范围：0~50")
            return None
        if not (1 <= lv <= 140):
            messagebox.showerror("输入错误", "宠物等级范围：1~140")
            return None
        if ans_cap < 1:
            messagebox.showerror("输入错误", "转生能力上限必须 ≥ 1")
            return None
        if not (1 <= n <= 50000):
            messagebox.showerror("输入错误", "模拟次数范围：1~50000")
            return None

        trans_count = 0 if self._trans_var.get() == "第1次" else 1
        pet_alloc = [pv, ps, pt, pd]
        stone_alloc = [mv, ms, mt, md]
        return ini, pet_alloc, stone_alloc, lv, trans_count, ans_cap, n

    def _on_simulate(self):
        params = self._parse()
        if params is None:
            return

        ini, pet_alloc, stone_alloc, lv, trans_count, ans_cap, n = params
        info = calc_transmigration(pet_alloc, stone_alloc, lv, trans_count, ans_cap=ans_cap)
        na = info["new_alloc"]
        self._info_var.set(
            f"转生能力值={info['ans']} / 转生能力上限={info['ans_cap']}  新成长率=[{na[0]},{na[1]},{na[2]},{na[3]}]  VSTD={sum(na)}  原Rank {info['petrank']}  Fx={info['Fx']}"
        )

        self._tree.delete(*self._tree.get_children())
        self._status_var.set("模拟中，请稍候…")
        threading.Thread(
            target=self._sim_thread,
            args=(ini, pet_alloc, stone_alloc, lv, trans_count, ans_cap, n),
            daemon=True,
        ).start()

    def _sim_thread(self, ini, pet_alloc, stone_alloc, lv, trans_count, ans_cap, n):
        try:
            _, rows = simulate_transmigration(
                ini, pet_alloc, stone_alloc, lv, trans_count, ans_cap=ans_cap, n=n
            )
            self.after(0, self._show_results, rows, n)
        except Exception as e:
            self.after(0, lambda: self._status_var.set(f"⚠ {e}"))

    def _show_results(self, rows: list[tuple], n: int):
        self._tree.delete(*self._tree.get_children())
        for row in rows:
            name = row[0]
            tag = _ROW_TAGS[name][0]
            self._tree.insert("", "end", values=row, tags=(tag,))
        self._status_var.set(f"{n} 次转生模拟完成（lv140）")
