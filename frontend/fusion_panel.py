"""
fusion_panel.py — 宠物融合与蛋孵化成长计算面板
"""

import tkinter as tk
from tkinter import ttk, messagebox

from backend.fusion import calc_fusion_egg_base


def _fmt_alloc(values) -> str:
    return f"{values[0]} / {values[1]} / {values[2]} / {values[3]}"


class FusionPanel(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, padding=8, **kwargs)
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_input()
        self._build_result()

    def _build_input(self):
        frame = ttk.LabelFrame(self, text="融合宠物参数", padding=10)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for col in range(7):
            frame.columnconfigure(col, weight=0)
        frame.columnconfigure(6, weight=1)

        self._vars: dict[str, tk.StringVar] = {}
        headers = [("对象", 7), ("等级", 7), ("V", 6), ("S", 6), ("T", 6), ("D", 6)]
        for col, (label_text, width) in enumerate(headers):
            ttk.Label(frame, text=label_text, font=("", 9, "bold"), width=width, anchor="center").grid(
                row=0, column=col, padx=4, pady=(0, 6), sticky="w"
            )

        for row, (label_text, prefix) in enumerate((("主宠", "main"), ("副宠1", "sub1"), ("副宠2", "sub2")), start=1):
            ttk.Label(frame, text=label_text, width=7, anchor="e").grid(row=row, column=0, padx=4, pady=3, sticky="w")
            for col, suffix in enumerate(("lv", "v", "s", "t", "d"), start=1):
                var = tk.StringVar()
                ttk.Entry(frame, textvariable=var, width=7, justify="center").grid(
                    row=row, column=col, padx=4, pady=3, sticky="w"
                )
                self._vars[f"{prefix}_{suffix}"] = var

        ttk.Button(frame, text="计算融合蛋", width=12, command=self._on_calculate).grid(
            row=4, column=0, columnspan=2, padx=(4, 8), pady=(10, 0), sticky="w"
        )
        ttk.Label(
            frame,
            text="副宠2整行留空表示只使用 1 只副宠；结果会同时展示蛋基础成长与孵化后成长（均不含 +-2 随机与 10 点分配）。",
            foreground="gray",
            wraplength=760,
            justify="left",
        ).grid(row=4, column=2, columnspan=5, sticky="w", padx=4, pady=(10, 0))

    def _build_result(self):
        frame = ttk.LabelFrame(self, text="融合步骤", padding=8)
        frame.grid(row=1, column=0, sticky="nsew", pady=(0, 4))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = ("stage", "lv", "input_alloc", "adjusted", "contrib", "note")
        self._tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        headings = {
            "stage": ("阶段", 72),
            "lv": ("等级", 52),
            "input_alloc": ("输入 V/S/T/D", 120),
            "adjusted": ("中间值", 120),
            "contrib": ("贡献", 120),
            "note": ("源码顺序 / 取整", 300),
        }
        for col, (title, width) in headings.items():
            self._tree.heading(col, text=title)
            anchor = "w" if col == "note" else "center"
            self._tree.column(col, width=width, minwidth=width, anchor=anchor, stretch=(col == "note"))

        ysb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        xsb = ttk.Scrollbar(frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        self._summary_var = tk.StringVar(value="请填入主宠/副宠参数后点击「计算融合蛋」")
        ttk.Label(self, textvariable=self._summary_var, foreground="#0055aa").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )

        self._notes_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self._notes_var, foreground="gray", justify="left", wraplength=860).grid(
            row=3, column=0, sticky="w", pady=(4, 0)
        )

    def _parse_pet(self, prefix: str, label: str, required: bool):
        fields = [self._vars[f"{prefix}_{suffix}"].get().strip() for suffix in ("lv", "v", "s", "t", "d")]
        if not any(fields):
            if required:
                raise ValueError(f"{label}必须填写等级和 V/S/T/D")
            return None
        if not all(fields):
            raise ValueError(f"{label}必须同时填写等级和 V/S/T/D，或全部留空")
        return int(fields[0]), [int(v) for v in fields[1:]]

    def _on_calculate(self):
        try:
            main = self._parse_pet("main", "主宠", required=True)
            sub1 = self._parse_pet("sub1", "副宠1", required=True)
            sub2 = self._parse_pet("sub2", "副宠2", required=False)
            kwargs = {
                "main_level": main[0],
                "main_alloc": main[1],
                "sub1_level": sub1[0],
                "sub1_alloc": sub1[1],
            }
            if sub2 is not None:
                kwargs["sub2_level"] = sub2[0]
                kwargs["sub2_alloc"] = sub2[1]
            result = calc_fusion_egg_base(**kwargs)
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))
            return
        except Exception as exc:
            self._summary_var.set(f"⚠ {exc}")
            return

        self._show_result(result)

    def _show_result(self, result: dict):
        self._tree.delete(*self._tree.get_children())

        main = result["main"]
        self._tree.insert(
            "",
            "end",
            values=(
                "主宠",
                main["level"],
                _fmt_alloc(main["input_alloc"]),
                _fmt_alloc(main["adjusted_alloc"]),
                _fmt_alloc(main["contrib"]),
                "若等级 < 80，先做 value*8//10；之后再做 value*6//10",
            ),
        )

        for sub in result["subs"]:
            self._tree.insert(
                "",
                "end",
                values=(
                    sub["name"],
                    sub["level"],
                    _fmt_alloc(sub["input_alloc"]),
                    _fmt_alloc(sub["adjusted_alloc"]),
                    "-",
                    "若等级 < 80，先做 value*8//10",
                ),
            )

        self._tree.insert(
            "",
            "end",
            values=(
                f"副宠和/{result['sub_count']}",
                "-",
                _fmt_alloc(result["sub_sum"]),
                _fmt_alloc(result["sub_avg"]),
                _fmt_alloc(result["sub_contrib"]),
                "严格按源码先做 sum//count，再做 value*4//10，不合并步骤",
            ),
        )
        self._tree.insert(
            "",
            "end",
            values=(
                "蛋基础成长",
                1,
                "-",
                _fmt_alloc(result["egg_base"]),
                _fmt_alloc(result["egg_base"]),
                "这里只是融合后基础值；未做 +-2 随机，也未做 10 点分配",
            ),
        )
        self._tree.insert(
            "",
            "end",
            values=(
                "孵化后成长",
                1,
                _fmt_alloc(result["egg_base"]),
                _fmt_alloc(result["hatch_alloc"]),
                _fmt_alloc(result["hatch_alloc"]),
                "按 PET_getEvolutionAns 无喂药情形继续计算；不含 +-2 随机，不含出生后 10 点分配",
            ),
        )

        self._summary_var.set(
            f"蛋基础成长={_fmt_alloc(result['egg_base'])}  VSTD={result['egg_vstd']}；"
            f"孵化后成长={_fmt_alloc(result['hatch_alloc'])}  VSTD={result['hatch_vstd']}  "
            f"（均不含 +-2 随机 / 10 点分配）"
        )
        self._notes_var.set("；".join(result["rounding_steps"]))
