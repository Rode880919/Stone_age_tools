"""
result_panel.py — 反推结果展示区

列结构：
    概率条 | Rank | VSTD(成长率和) | 成长率V/S/T/D | 成长误差 | INIT残差 | INITNUM | 置信度
"""

import tkinter as tk
from tkinter import ttk
from backend.reverse import ReverseCandidate

MAX_ROWS = 30


class ResultPanel(ttk.LabelFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, text="反推结果（按概率排序）", padding=10, **kwargs)
        self._build()

    def _build(self):
        cols = (
            "prob_bar",
            "rank", "vstd_alloc", "alloc",
            "alloc_err", "ini_res", "ini", "pct",
        )
        self._tree = ttk.Treeview(
            self, columns=cols, show="headings",
            height=14, selectmode="browse",
        )

        headings = {
            "prob_bar": "概率",
            "rank": "Rank",
            "vstd_alloc": "VSTD",
            "alloc": "成长率 V / S / T / D",
            "alloc_err": "成长误差",
            "ini_res": "INIT残差",
            "ini": "INITNUM",
            "pct": "置信度",
        }
        col_w = 112
        for col, heading in headings.items():
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=col_w, minwidth=col_w, anchor="center", stretch=True)

        sb_y = ttk.Scrollbar(self, orient="vertical",   command=self._tree.yview)
        sb_x = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._status_var = tk.StringVar(value="请输入宠物状态后点击「反推计算」")
        ttk.Label(self, textvariable=self._status_var,
                  foreground="gray").grid(row=2, column=0, columnspan=2,
                                          sticky="w", pady=(4, 0))
        self._progress = ttk.Progressbar(self, mode="determinate", length=200)

    # ──────────────────────────────────────────
    def show_calculating(self):
        self._status_var.set("计算中，请稍候…")
        self._tree.delete(*self._tree.get_children())
        self._progress.grid(row=3, column=0, sticky="w", pady=(4, 0))
        self._progress["value"] = 0

    def update_progress(self, done: int, total: int):
        if total > 0:
            self._progress["value"] = done / total * 100

    def show_results(self, candidates: list[ReverseCandidate]):
        self._progress.grid_remove()
        self._tree.delete(*self._tree.get_children())

        if not candidates:
            self._status_var.set("未找到满足条件的候选（请检查输入是否合理）")
            return

        total_score = sum(
            ic.score for c in candidates for ic in c.ini_candidates
        )

        row_count = 0
        for cand in candidates:
            if row_count >= MAX_ROWS:
                break
            for ic in cand.ini_candidates:
                if row_count >= MAX_ROWS:
                    break

                rel_pct = ic.score / total_score * 100 if total_score > 0 else 0
                bar     = _make_bar(rel_pct)
                alloc_s = " / ".join(str(a) for a in cand.alloc)
                vstd_s  = str(sum(cand.alloc))

                iid = self._tree.insert(
                    "", "end",
                    values=(
                        bar,
                        cand.rank, vstd_s, alloc_s,
                        f"{cand.alloc_err:.2f}", f"{ic.residual:.0f}", ic.ini, f"{rel_pct:.1f}%",
                    ),
                )
                if   rel_pct >= 20: self._tree.item(iid, tags=("high",))
                elif rel_pct >= 5:  self._tree.item(iid, tags=("mid",))

                row_count += 1

        self._tree.tag_configure("high", background="#d4edda")
        self._tree.tag_configure("mid",  background="#fff3cd")

        n_total = sum(len(c.ini_candidates) for c in candidates)
        self._status_var.set(
            f"{len(candidates)} 个成长率候选，{n_total} 个 (成长率, INITNUM) 组合"
            f"（显示前 {row_count} 条）"
        )

    def show_error(self, msg: str):
        self._progress.grid_remove()
        self._tree.delete(*self._tree.get_children())
        self._status_var.set(f"⚠ {msg}")


def _make_bar(pct: float, width: int = 12) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)
