"""
app.py — 主窗口：标签页结构（反推计算 + 成长模拟）
"""

import os
import re
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from backend.reverse import reverse_engineer_multi
from backend.scorer import score_candidates_multi
from frontend.evolution_panel import EvolutionPanel
from frontend.fusion_panel import FusionPanel
from frontend.input_panel import InputPanel
from frontend.result_panel import ResultPanel
from frontend.sim_panel import SimPanel
from frontend.trans_panel import TransPanel

_INLINE_RE = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*)")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("石器时代·宠物工具箱")
        self.resizable(True, True)
        self.minsize(1140, 820)
        self._help_windows: dict[str, tk.Toplevel] = {}
        self._build()
        self._center()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_menu()

        nb = ttk.Notebook(self)
        nb.grid(row=0, column=0, sticky="nsew", padx=6, pady=(6, 4))

        ttk.Label(self, text="作者: Rode   QQ: 81881788", foreground="gray").grid(
            row=1, column=0, sticky="e", padx=8, pady=(0, 4)
        )

        tab_rev = ttk.Frame(nb, padding=8)
        nb.add(tab_rev, text="反推计算")
        tab_rev.columnconfigure(0, weight=1)
        tab_rev.rowconfigure(1, weight=1)

        self._input = InputPanel(tab_rev, on_calculate=self._on_calculate)
        self._input.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 2))

        self._result = ResultPanel(tab_rev)
        self._result.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0, 2))

        note = (
            "说明：VSTD = 各维成长率之和（决定 Rank）｜"
            "普通捕捉：≥100=R0, ≥95=R1, ≥90=R2, ≥85=R3, ≥80=R4, <80=R5 ｜"
            "转生宠物：≥130=R0, ≥100=R1, ≥95=R2, ≥85=R3, ≥80=R4, <80=R5"
        )
        ttk.Label(
            tab_rev,
            text=note,
            foreground="gray",
            wraplength=920,
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=2, pady=(0, 2))

        tab_sim = SimPanel(nb)
        nb.add(tab_sim, text="成长模拟")

        tab_trans = TransPanel(nb)
        nb.add(tab_trans, text="转生模拟")

        tab_fusion = FusionPanel(nb)
        nb.add(tab_fusion, text="融合成蛋")

        tab_evo = EvolutionPanel(nb)
        nb.add(tab_evo, text="融合蛋喂药")

    def _build_menu(self):
        menu_bar = tk.Menu(self)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="使用说明", command=self._show_readme_user)
        help_menu.add_command(label="宠物基础知识", command=self._show_pet_basics)
        menu_bar.add_cascade(label="帮助", menu=help_menu)

        self.config(menu=menu_bar)

    def _resource_path(self, relative_path: str) -> str:
        base_dir = getattr(
            sys,
            "_MEIPASS",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        )
        return os.path.join(base_dir, relative_path)

    def _load_text_resource(self, relative_path: str) -> str:
        path = self._resource_path(relative_path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _create_help_text(self, parent) -> tk.Text:
        text = tk.Text(
            parent,
            wrap="word",
            padx=18,
            pady=14,
            relief="flat",
            borderwidth=0,
            background="#fcfbf7",
            foreground="#1e2430",
            insertwidth=0,
        )
        text.configure(font=("Microsoft YaHei UI", 10))
        text.tag_configure("body", spacing1=3, spacing3=7)
        text.tag_configure("h1", font=("Microsoft YaHei UI", 20, "bold"), spacing1=10, spacing3=12)
        text.tag_configure("h2", font=("Microsoft YaHei UI", 16, "bold"), spacing1=10, spacing3=10)
        text.tag_configure("h3", font=("Microsoft YaHei UI", 13, "bold"), spacing1=8, spacing3=8)
        text.tag_configure("bullet", lmargin1=16, lmargin2=36, spacing1=2, spacing3=3)
        text.tag_configure("number", lmargin1=16, lmargin2=40, spacing1=2, spacing3=3)
        text.tag_configure(
            "code_block",
            font=("Consolas", 10),
            background="#eef1f6",
            lmargin1=22,
            lmargin2=22,
            rmargin=18,
            spacing1=6,
            spacing3=8,
        )
        text.tag_configure(
            "code_inline",
            font=("Consolas", 10),
            background="#eef1f6",
            foreground="#16324f",
        )
        text.tag_configure("strong", font=("Microsoft YaHei UI", 10, "bold"))
        return text

    def _insert_inline_markdown(self, text: tk.Text, raw: str, base_tag: str):
        last = 0
        for match in _INLINE_RE.finditer(raw):
            if match.start() > last:
                text.insert("end", raw[last:match.start()], (base_tag,))
            token = match.group(0)
            if token.startswith("`"):
                text.insert("end", token[1:-1], (base_tag, "code_inline"))
            else:
                text.insert("end", token[2:-2], (base_tag, "strong"))
            last = match.end()
        if last < len(raw):
            text.insert("end", raw[last:], (base_tag,))

    def _render_markdown(self, text: tk.Text, content: str):
        in_code = False
        for line in content.splitlines():
            stripped = line.rstrip()

            if stripped.startswith("```"):
                in_code = not in_code
                text.insert("end", "\n")
                continue

            if in_code:
                text.insert("end", f"{stripped}\n", ("code_block",))
                continue

            if not stripped:
                text.insert("end", "\n")
                continue

            if stripped.startswith("# "):
                text.insert("end", stripped[2:] + "\n", ("h1",))
                continue
            if stripped.startswith("## "):
                text.insert("end", stripped[3:] + "\n", ("h2",))
                continue
            if stripped.startswith("### "):
                text.insert("end", stripped[4:] + "\n", ("h3",))
                continue

            bullet = re.match(r"^[-*]\s+(.*)$", stripped)
            if bullet:
                text.insert("end", "• ", ("bullet",))
                self._insert_inline_markdown(text, bullet.group(1), "bullet")
                text.insert("end", "\n")
                continue

            number = re.match(r"^(\d+)\.\s+(.*)$", stripped)
            if number:
                text.insert("end", f"{number.group(1)}. ", ("number",))
                self._insert_inline_markdown(text, number.group(2), "number")
                text.insert("end", "\n")
                continue

            self._insert_inline_markdown(text, stripped, "body")
            text.insert("end", "\n")

    def _show_help_text(self, key: str, title: str, relative_path: str):
        existing = self._help_windows.get(key)
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_force()
            return

        try:
            content = self._load_text_resource(relative_path)
        except OSError as exc:
            messagebox.showerror("帮助加载失败", f"无法读取帮助文件：{relative_path}\n{exc}")
            return

        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("1020x780")
        win.minsize(800, 560)
        win.transient(self)

        frame = ttk.Frame(win, padding=8)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="内置帮助已按阅读视图渲染，内容来源于项目中的 markdown 文件。",
            foreground="gray",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        text_frame = ttk.Frame(frame)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        text = self._create_help_text(text_frame)
        text.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scroll.set)

        self._render_markdown(text, content)
        text.configure(state="disabled")

        def _on_close():
            self._help_windows.pop(key, None)
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_close)
        self._help_windows[key] = win

    def _show_readme_user(self):
        self._show_help_text("readme_user", "帮助 - 使用说明", "README_user.md")

    def _show_pet_basics(self):
        self._show_help_text("pet_basics", "帮助 - 宠物基础知识", "pet_basics.md")

    def _center(self):
        self.update_idletasks()
        w, h = 1220, 860
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _on_calculate(self):
        level_data = self._input.get_values()
        if level_data is None:
            return
        self._result.show_calculating()
        threading.Thread(
            target=self._calc_thread,
            args=(level_data,),
            daemon=True,
        ).start()

    def _calc_thread(self, level_data):
        try:
            cands = reverse_engineer_multi(
                level_data, transmigrated=self._input.transmigrated
            )

            def progress(done, total):
                self.after(0, self._result.update_progress, done, total)

            scored = score_candidates_multi(
                cands, level_data, progress_cb=progress
            )
            self.after(0, self._result.show_results, scored)

        except Exception as exc:
            self.after(0, self._result.show_error, str(exc))
