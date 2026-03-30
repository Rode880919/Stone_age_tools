"""
evolution_panel.py — 融合蛋喂药与孵化后成长优化面板
"""

import tkinter as tk
from tkinter import ttk, messagebox

from backend.evolution import (
    DIM_NAMES,
    LEVEL_NAMES,
    EvolutionParams,
    analyze_evolution_feeding,
    format_plan_summary,
    incubate_alloc,
)


def _fmt_alloc(values: list[int]) -> str:
    return f"{values[0]} / {values[1]} / {values[2]} / {values[3]}"


def _fmt_score(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


class EvolutionPanel(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, padding=8, **kwargs)
        self._top_entry_map: dict[str, dict] = {}
        self._vars: dict[str, tk.StringVar] = {}
        self._weight_entries: list[ttk.Entry] = []
        self._priority_widgets: list[ttk.Combobox] = []
        self._custom_plan_var_names: list[str] = []
        self._last_result: dict | None = None
        self._last_params: EvolutionParams | None = None
        self._last_status_base: str = ""
        self._custom_refresh_job: str | None = None
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_input()
        self._build_result()
        self._refresh_mode_ui()

    def _build_input(self):
        frame = ttk.LabelFrame(self, text="蛋参数 / 目标 / 规则", padding=10)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for col in range(18):
            frame.columnconfigure(col, weight=0)
        frame.columnconfigure(17, weight=1)

        ttk.Label(frame, text="蛋基础成长", font=("", 9, "bold"), width=10, anchor="e").grid(
            row=0, column=0, padx=(0, 8), sticky="w"
        )
        for idx, key in enumerate(("v", "s", "t", "d")):
            ttk.Label(frame, text=DIM_NAMES[idx], width=2, anchor="e").grid(row=0, column=1 + idx * 2, sticky="e", padx=(8, 2))
            var = tk.StringVar(value="0")
            ttk.Entry(frame, textvariable=var, width=6, justify="center").grid(row=0, column=2 + idx * 2, sticky="w", padx=(0, 6))
            self._vars[key] = var

        method = ttk.LabelFrame(frame, text="计算方式", padding=8)
        method.grid(row=1, column=0, columnspan=18, sticky="ew", pady=(8, 0))
        for col in range(14):
            method.columnconfigure(col, weight=0)
        method.columnconfigure(13, weight=1)

        self._mode_var = tk.StringVar(value="linear")
        ttk.Radiobutton(
            method,
            text="计算方式1：线性目标",
            variable=self._mode_var,
            value="linear",
            command=self._refresh_mode_ui,
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        for idx, key in enumerate(("xv", "xs", "xt", "xd")):
            base_col = 2 + idx * 2
            ttk.Label(method, text=f"x{DIM_NAMES[idx]}", width=3, anchor="e").grid(
                row=0, column=base_col, sticky="e", padx=(8, 2)
            )
            var = tk.StringVar(value="1")
            entry = ttk.Entry(method, textvariable=var, width=6, justify="center")
            entry.grid(row=0, column=base_col + 1, sticky="w", padx=(0, 8))
            self._vars[key] = var
            self._weight_entries.append(entry)

        ttk.Radiobutton(
            method,
            text="计算方式2：主目标 + 次目标",
            variable=self._mode_var,
            value="priority",
            command=self._refresh_mode_ui,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Label(method, text="主目标", width=6, anchor="e").grid(row=1, column=2, sticky="e", padx=(8, 2), pady=(8, 0))
        self._primary_dim_var = tk.StringVar(value="V")
        primary_combo = ttk.Combobox(
            method,
            textvariable=self._primary_dim_var,
            values=("V", "S", "T", "D"),
            width=6,
            state="readonly",
        )
        primary_combo.grid(row=1, column=3, sticky="w", pady=(8, 0))
        self._priority_widgets.append(primary_combo)

        ttk.Label(method, text="次目标", width=6, anchor="e").grid(row=1, column=4, sticky="e", padx=(8, 2), pady=(8, 0))
        self._secondary_dim_var = tk.StringVar(value="无")
        secondary_combo = ttk.Combobox(
            method,
            textvariable=self._secondary_dim_var,
            values=("无", "V", "S", "T", "D"),
            width=6,
            state="readonly",
        )
        secondary_combo.grid(row=1, column=5, sticky="w", pady=(8, 0))
        self._priority_widgets.append(secondary_combo)

        ttk.Button(frame, text="开始计算", width=12, command=self._on_calculate).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

        rule_specs = [
            ("总喂食颗数", "total_feeds", "40"),
            ("Lv1 原始值", "eff1", "25"),
            ("Lv2 原始值", "eff2", "50"),
            ("Lv3 原始值", "eff3", "75"),
            ("Lv4 原始值", "eff4", "100"),
            ("Lv5 原始值", "eff5", "125"),
            ("折算分子", "fold_num", "7"),
            ("折算分母", "fold_den", "1000"),
            ("折算单项上限", "effective_single_cap", "60"),
            ("折算总和上限", "work_total_cap", "50"),
            ("蛋单项上限", "base_single_max", "60"),
            ("孵化单项上限", "final_single_cap", "60"),
            ("孵化总和上限", "final_total_cap", "150"),
            ("候选解显示条数", "top_n", "12"),
        ]
        for idx, (label, key, default) in enumerate(rule_specs):
            row = 3 + (idx // 7)
            col = (idx % 7) * 2
            ttk.Label(frame, text=label, width=12, anchor="e").grid(row=row, column=col, sticky="e", padx=(0, 6), pady=2)
            var = tk.StringVar(value=default)
            ttk.Entry(frame, textvariable=var, width=8, justify="center").grid(
                row=row, column=col + 1, sticky="w", padx=(0, 8), pady=2
            )
            self._vars[key] = var

        custom = ttk.LabelFrame(frame, text="自定义喂法（4 × 5，可由候选解回填）", padding=8)
        custom.grid(row=5, column=0, columnspan=18, sticky="ew", pady=(8, 0))
        for col in range(6):
            custom.columnconfigure(col, weight=0)

        ttk.Label(custom, text="属性", width=6, anchor="center").grid(row=0, column=0, padx=6)
        for idx, level in enumerate(LEVEL_NAMES, start=1):
            ttk.Label(custom, text=level, font=("", 9, "bold"), width=6, anchor="center").grid(row=0, column=idx, padx=3)

        for row_idx, dim in enumerate(DIM_NAMES, start=1):
            ttk.Label(custom, text=dim, font=("", 9, "bold"), width=6, anchor="center").grid(row=row_idx, column=0, padx=(0, 6))
            for level_idx in range(5):
                key = f"plan_{row_idx - 1}_{level_idx}"
                var = tk.StringVar(value="")
                ttk.Entry(custom, textvariable=var, width=6, justify="center").grid(
                    row=row_idx, column=level_idx + 1, padx=3, pady=2
                )
                var.trace_add("write", self._schedule_custom_refresh)
                self._vars[key] = var
                self._custom_plan_var_names.append(key)

        self._info_var = tk.StringVar(
            value="两种计算方式互斥。两者都以孵化后成长（不含 10 点随机）作为优化对象；自定义喂法结果会插入下面的候选解表。"
        )
        ttk.Label(frame, textvariable=self._info_var, foreground="#0055aa", wraplength=980, justify="left").grid(
            row=6, column=0, columnspan=18, sticky="w", pady=(8, 0)
        )

    def _build_result(self):
        container = ttk.Frame(self)
        container.grid(row=1, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        top_frame = ttk.LabelFrame(container, text="候选最优解（点选后回填到自定义喂法）", padding=8)
        top_frame.grid(row=0, column=0, sticky="nsew")
        top_frame.columnconfigure(0, weight=1)
        top_frame.rowconfigure(0, weight=1)
        self._top_tree = ttk.Treeview(
            top_frame,
            columns=("rank", "score", "final_alloc", "final_total", "raw", "work", "pills", "flags", "plan"),
            show="headings",
            height=16,
        )
        for col, title, width in [
            ("rank", "排名", 60),
            ("score", "目标值", 72),
            ("final_alloc", "孵化后成长", 120),
            ("final_total", "总和", 56),
            ("raw", "原始值", 120),
            ("work", "折算后", 120),
            ("pills", "各维颗数", 90),
            ("flags", "压缩", 88),
            ("plan", "方案", 380),
        ]:
            self._top_tree.heading(col, text=title)
            self._top_tree.column(col, width=width, anchor="center", stretch=(col == "plan"))
        self._top_tree.bind("<<TreeviewSelect>>", self._on_pick_solution)
        self._top_tree.tag_configure("custom", background="#fff3c4")
        ysb = ttk.Scrollbar(top_frame, orient="vertical", command=self._top_tree.yview)
        xsb = ttk.Scrollbar(top_frame, orient="horizontal", command=self._top_tree.xview)
        self._top_tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self._top_tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        self._status_var = tk.StringVar(value="请填入蛋基础成长、选择计算方式后点击『开始计算』")
        ttk.Label(self, textvariable=self._status_var, foreground="gray").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )

    def _refresh_mode_ui(self):
        linear_enabled = self._mode_var.get() == "linear"
        linear_state = "normal" if linear_enabled else "disabled"
        priority_state = "readonly" if not linear_enabled else "disabled"
        for entry in self._weight_entries:
            entry.configure(state=linear_state)
        for widget in self._priority_widgets:
            widget.configure(state=priority_state)

    def _parse_custom_plan(self, total_feeds: int):
        status, plan = self._parse_custom_plan_silent(total_feeds)
        if status == "empty":
            return None
        if status == "invalid":
            raise ValueError("自定义喂法中每个格子都必须是 ≥ 0 的整数")
        if status == "incomplete":
            total = sum(
                int(self._vars[f"plan_{dim_idx}_{level_idx}"].get().strip() or 0)
                for dim_idx in range(4)
                for level_idx in range(5)
                if (self._vars[f"plan_{dim_idx}_{level_idx}"].get().strip() or "0").lstrip("-").isdigit()
            )
            raise ValueError(f"自定义喂法必须刚好喂满 {total_feeds} 颗，当前是 {total} 颗")
        return plan

    def _parse_custom_plan_silent(self, total_feeds: int):
        plan: list[list[int]] = []
        has_any = False
        total = 0
        for dim_idx in range(4):
            row: list[int] = []
            for level_idx in range(5):
                text = self._vars[f"plan_{dim_idx}_{level_idx}"].get().strip()
                if text:
                    has_any = True
                    try:
                        value = int(text)
                    except ValueError:
                        return "invalid", None
                else:
                    value = 0
                if value < 0:
                    return "invalid", None
                row.append(value)
                total += value
            plan.append(row)

        if not has_any or total == 0:
            return "empty", None
        if total != total_feeds:
            return "incomplete", None
        return "ok", plan

    def _parse(self):
        try:
            base_alloc = [
                int(self._vars["v"].get()),
                int(self._vars["s"].get()),
                int(self._vars["t"].get()),
                int(self._vars["d"].get()),
            ]
            params = EvolutionParams(
                total_feeds=int(self._vars["total_feeds"].get()),
                medicine_effects=(
                    int(self._vars["eff1"].get()),
                    int(self._vars["eff2"].get()),
                    int(self._vars["eff3"].get()),
                    int(self._vars["eff4"].get()),
                    int(self._vars["eff5"].get()),
                ),
                fold_scale_num=int(self._vars["fold_num"].get()),
                fold_scale_den=int(self._vars["fold_den"].get()),
                effective_single_cap=int(self._vars["effective_single_cap"].get()),
                work_total_cap=int(self._vars["work_total_cap"].get()),
                base_single_min=0,
                base_single_max=int(self._vars["base_single_max"].get()),
                final_single_cap=int(self._vars["final_single_cap"].get()),
                final_total_cap=int(self._vars["final_total_cap"].get()),
                top_n=int(self._vars["top_n"].get()),
            )
            custom_plan = self._parse_custom_plan(params.total_feeds)
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))
            return None

        if any(x < 0 for x in base_alloc):
            messagebox.showerror("输入错误", "蛋的 V/S/T/D 必须 ≥ 0")
            return None
        if params.total_feeds != 40:
            messagebox.showerror("输入错误", "当前优化器按你的约束要求，必须喂满 40 颗")
            return None
        if params.fold_scale_den <= 0:
            messagebox.showerror("输入错误", "折算分母必须 ≥ 1")
            return None
        if params.top_n < 1:
            messagebox.showerror("输入错误", "候选解显示条数必须 ≥ 1")
            return None

        mode = self._mode_var.get()
        if mode == "linear":
            weights = [
                float(self._vars["xv"].get()),
                float(self._vars["xs"].get()),
                float(self._vars["xt"].get()),
                float(self._vars["xd"].get()),
            ]
            target_dim = ""
            objective_text = " / ".join(f"x{DIM_NAMES[idx]}={weights[idx]:g}" for idx in range(4))
        else:
            primary_dim = self._primary_dim_var.get().strip().upper()
            secondary_dim = self._secondary_dim_var.get().strip().upper()
            if primary_dim not in DIM_NAMES:
                messagebox.showerror("输入错误", "主目标必须是 V/S/T/D")
                return None
            if secondary_dim == "无" or secondary_dim == primary_dim:
                secondary_dim = ""
            elif secondary_dim not in DIM_NAMES:
                messagebox.showerror("输入错误", "次目标必须是 V/S/T/D 或『无』")
                return None
            weights = [1.0 if name == primary_dim else 0.0 for name in DIM_NAMES]
            target_dim = secondary_dim
            objective_text = f"主目标={primary_dim}" + (f"  次目标={secondary_dim}" if secondary_dim else "")

        return {
            "base_alloc": base_alloc,
            "weights": weights,
            "params": params,
            "mode": mode,
            "target_dim": target_dim,
            "objective_text": objective_text,
            "custom_plan": custom_plan,
        }

    def _flags(self, entry: dict) -> str:
        flags: list[str] = []
        if entry.get("triggered_work_total_cap"):
            flags.append("50压缩")
        if entry.get("triggered_final_total_cap"):
            flags.append("150压缩")
        return "/".join(flags) if flags else "-"

    def _fill_plan(self, entry: dict):
        for dim_idx in range(4):
            for level_idx in range(5):
                value = entry["plan"][dim_idx][level_idx]
                self._vars[f"plan_{dim_idx}_{level_idx}"].set("" if value == 0 else str(value))
        self._status_var.set("已将候选解回填到自定义喂法；自定义结果会随修改自动刷新")

    def _on_pick_solution(self, _event=None):
        selection = self._top_tree.selection()
        if not selection:
            return
        entry = self._top_entry_map.get(selection[0])
        if entry is None:
            return
        self._fill_plan(entry)

    def _insert_candidate(self, rank_label: str, entry: dict):
        tags = ("custom",) if rank_label == "自定义" else ()
        item_id = self._top_tree.insert(
            "",
            "end",
            values=(
                rank_label,
                _fmt_score(entry["score"]),
                _fmt_alloc(entry["final_alloc"]),
                entry["final_total"],
                _fmt_alloc(entry["raw_totals"]),
                _fmt_alloc(entry["effective_work"]),
                _fmt_alloc(entry["dim_feed_counts"]),
                self._flags(entry),
                format_plan_summary(entry["plan"]),
            ),
            tags=tags,
        )
        self._top_entry_map[item_id] = entry

    def _render_candidate_list(self, result: dict, custom_result: dict | None):
        self._top_tree.delete(*self._top_tree.get_children())
        self._top_entry_map.clear()
        if custom_result is not None:
            self._insert_candidate("自定义", custom_result)
        for idx, entry in enumerate(result["top_results"], start=1):
            self._insert_candidate(str(idx), entry)

    def _schedule_custom_refresh(self, *_args):
        if self._custom_refresh_job is not None:
            self.after_cancel(self._custom_refresh_job)
        self._custom_refresh_job = self.after(120, self._refresh_custom_candidate)

    def _refresh_custom_candidate(self):
        self._custom_refresh_job = None
        if self._last_result is None or self._last_params is None:
            return

        status, plan = self._parse_custom_plan_silent(self._last_params.total_feeds)
        custom_result = None
        if status == "ok" and plan is not None:
            custom_result = incubate_alloc(self._last_result["base_alloc"], plan, self._last_params)
            weights = self._last_result["weights"]
            custom_result["score"] = sum(custom_result["final_alloc"][idx] * weights[idx] for idx in range(4))

        self._render_candidate_list(self._last_result, custom_result)

        if status == "ok":
            self._status_var.set(self._last_status_base + "；自定义方案已刷新")
        elif status == "empty":
            self._status_var.set(self._last_status_base + "；自定义方案为空，未显示自定义行")
        elif status == "incomplete":
            self._status_var.set(self._last_status_base + "；自定义方案未满 40 颗，未显示自定义行")
        else:
            self._status_var.set(self._last_status_base + "；自定义方案含无效输入，未显示自定义行")

    def _on_calculate(self):
        parsed = self._parse()
        if parsed is None:
            return

        base_alloc = parsed["base_alloc"]
        weights = parsed["weights"]
        params = parsed["params"]
        target_dim = parsed["target_dim"]
        custom_plan = parsed["custom_plan"]

        try:
            result = analyze_evolution_feeding(base_alloc, weights, params, target_dim=target_dim)
            result["mode"] = parsed["mode"]
            result["objective_text"] = parsed["objective_text"]
            custom_result = incubate_alloc(base_alloc, custom_plan, params) if custom_plan else None
            if custom_result is not None:
                custom_result["score"] = sum(custom_result["final_alloc"][idx] * weights[idx] for idx in range(4))
        except Exception as exc:
            messagebox.showerror("计算失败", str(exc))
            return

        result["params"] = params
        self._show_results(result, custom_result)

    def _show_results(self, result: dict, custom_result: dict | None):
        self._last_result = result
        self._last_params = result["params"]

        base_alloc = result["base_alloc"]
        mode_text = "计算方式1：线性目标" if result["mode"] == "linear" else "计算方式2：主目标 + 次目标"
        self._info_var.set(
            f"蛋基础成长={_fmt_alloc(base_alloc)}  优化目标=孵化后成长（不含 10 点随机）  {mode_text}  {result['objective_text']}  搜索状态={result['searched_states']}"
        )

        self._render_candidate_list(result, custom_result)

        custom_text = "；自定义方案结果已插入候选解表" if custom_result is not None else ""
        self._last_status_base = (
            f"计算完成：扫描 {result['searched_states']} 个可达状态，显示 {len(result['top_results'])} 个候选解{custom_text}"
        )
        self._status_var.set(self._last_status_base)
