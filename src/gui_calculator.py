import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import sys
import os
import json

try:
    import winsound  # type: ignore
except Exception:
    winsound = None  # type: ignore

from calculator import CalculatorEngine


class CalculatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Calculator")
        self.geometry("420x560")
        self.minsize(380, 520)
        self.engine = CalculatorEngine()
        self.enable_sounds = False
        self.theme = "Light"
        self.readable_numbers = True
        self.large_buttons = False
        self._prefs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".calculator_ui.json")
        self._history_index = None  # type: ignore[var-annotated]
        self._build_menu()
        self._build_ui()
        self._bind_keys()
        self._load_ui_prefs()
        self._apply_theme(self.theme)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----------------------------- UI Layout ------------------------------
    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save Session", command=self._save_session)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Copy Result", accelerator="Ctrl+C", command=self._copy_result)
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=self._paste_into_equation)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Toggle Tape", command=self._toggle_tape)
        theme_menu = tk.Menu(view_menu, tearoff=0)
        theme_menu.add_command(label="Light", command=lambda: self._apply_theme("Light"))
        theme_menu.add_command(label="Dark", command=lambda: self._apply_theme("Dark"))
        theme_menu.add_command(label="High Contrast", command=lambda: self._apply_theme("HighContrast"))
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        # Persistent variables for checkbuttons
        self._view_readable_var = getattr(self, "_view_readable_var", tk.BooleanVar(value=self.readable_numbers))
        self._view_large_var = getattr(self, "_view_large_var", tk.BooleanVar(value=self.large_buttons))
        view_menu.add_checkbutton(label="Readable Numbers", onvalue=True, offvalue=False, variable=self._view_readable_var, command=self._toggle_readable_numbers)
        view_menu.add_checkbutton(label="Large Buttons", onvalue=True, offvalue=False, variable=self._view_large_var, command=self._toggle_large_buttons)
        menubar.add_cascade(label="View", menu=view_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Unit Converter", command=self._open_unit_converter)
        tools_menu.add_command(label="Graph Function", command=self._open_graph_window)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_checkbutton(label="Enable Sounds", command=self._toggle_sounds)
        menubar.add_cascade(label="Options", menu=options_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _build_ui(self) -> None:
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(container)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 4))

        self.title_label = ttk.Label(top_frame, text="Scientific Calculator", font=("Segoe UI Semibold", 14))
        self.title_label.pack(side=tk.TOP, anchor="w", pady=(0, 6))

        self.equation_var = tk.StringVar()
        self.result_var = tk.StringVar()

        self.entry_equation = ttk.Entry(top_frame, textvariable=self.equation_var, font=("Segoe UI", 13))
        self.entry_equation.pack(fill=tk.X)
        self.entry_equation.focus_set()

        result_row = ttk.Frame(top_frame)
        result_row.pack(fill=tk.X, pady=(6, 0))

        self.entry_result = ttk.Entry(result_row, textvariable=self.result_var, font=("Segoe UI", 13), state="readonly")
        self.entry_result.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.mem_label = ttk.Label(result_row, text="", width=3, anchor="center")
        self.mem_label.pack(side=tk.RIGHT, padx=(6, 0))

        middle = ttk.Frame(container)
        middle.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Left: keypad
        keypad = ttk.Frame(middle)
        keypad.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right: tape/history
        tape_frame = ttk.Frame(middle)
        tape_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.tape_visible = True
        # Controls above tape
        controls = ttk.Frame(tape_frame)
        controls.pack(side=tk.TOP, fill=tk.X, padx=(6, 0))
        ttk.Label(controls, text="History").pack(side=tk.LEFT)
        self.tape_filter_var = tk.StringVar()
        search = ttk.Entry(controls, textvariable=self.tape_filter_var, width=16)
        search.pack(side=tk.LEFT, padx=4)
        search.bind("<KeyRelease>", lambda e: self._refresh_tape())
        ttk.Button(controls, text="Clear", command=self._clear_tape).pack(side=tk.LEFT)
        # Tape list
        list_wrap = ttk.Frame(tape_frame)
        list_wrap.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.tape_list = tk.Listbox(list_wrap, height=20)
        self.tape_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self.tape_list.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tape_list.config(yscrollcommand=scroll.set)
        self.tape_list.bind("<Double-Button-1>", self._reuse_from_tape)
        self.tape_list.bind("<Button-3>", self._tape_context_menu)
        self._refresh_tape()

        # Buttons
        rows = [
            ["MC", "MR", "M+", "M-", "C", "⌫"],
            ["(", ")", "^", "/", "sqrt", "%"],
            ["7", "8", "9", "*", "sin", "cos"],
            ["4", "5", "6", "-", "tan", "ln"],
            ["1", "2", "3", "+", "log", "factorial"],
            ["0", ".", "ANS", "=", "asin", "acos"],
        ]

        for r, row in enumerate(rows):
            row_frame = ttk.Frame(keypad)
            row_frame.pack(fill=tk.BOTH, expand=True)
            for c, label in enumerate(row):
                style_name = (
                    "Equals.TButton" if label == "=" else ("Danger.TButton" if label in ("C", "⌫") else "TButton")
                )
                btn = ttk.Button(row_frame, text=label, style=style_name)
                btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
                self._wire_button(btn, label)
                self._maybe_add_tooltip(btn, label)

        self._apply_theme(self.theme)

        # Context menus for entries
        self._build_context_menus()

        # Status bar
        status = ttk.Frame(container)
        status.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(status, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=8, pady=4)

    def _wire_button(self, btn: ttk.Button, label: str) -> None:
        if label == "=":
            btn.config(command=self._calculate)
            return
        if label == "C":
            btn.config(command=self._clear)
            return
        if label == "⌫":
            btn.config(command=self._backspace)
            return
        if label == "ANS":
            btn.config(command=self._use_ans)
            return
        if label == "MC":
            btn.config(command=self._mc)
            return
        if label == "MR":
            btn.config(command=self._mr)
            return
        if label == "M+":
            btn.config(command=self._m_plus)
            return
        if label == "M-":
            btn.config(command=self._m_minus)
            return
        # Default is to append the label (functions add opening paren)
        if label in {"sin", "cos", "tan", "asin", "acos", "atan", "sqrt", "log", "ln", "factorial"}:
            btn.config(command=lambda l=label: self._append(l + "("))
        else:
            btn.config(command=lambda l=label: self._append(l))

    # ----------------------------- Actions --------------------------------
    def _append(self, text: str) -> None:
        cur = self.equation_var.get()
        if cur == "Error" or cur.startswith("Error:"):
            cur = ""
        self.equation_var.set(cur + text)

    def _calculate(self, *_: object) -> None:
        expr = self.equation_var.get()
        res = self.engine.evaluate(expr)
        self._display_result(res)
        self._refresh_tape()
        if self.enable_sounds and winsound:
            try:
                winsound.MessageBeep()  # type: ignore[attr-defined]
            except Exception:
                pass
        self._history_index = None

    def _clear(self, *_: object) -> None:
        self.equation_var.set("")
        self.result_var.set("")

    def _backspace(self, *_: object) -> None:
        cur = self.equation_var.get()
        if not cur:
            return
        if cur.endswith("ANS"):
            self.equation_var.set(cur[:-3])
            return
        self.equation_var.set(cur[:-1])

    def _use_ans(self, *_: object) -> None:
        self._append("ANS")

    def _mc(self) -> None:
        self.engine.memory_clear()
        self._status("Memory cleared")
        self._update_memory_indicator()

    def _mr(self) -> None:
        self._append(str(self.engine.memory_recall()))

    def _m_plus(self) -> None:
        value = self._current_result_or_eval()
        self.engine.memory_add(value)
        self._status("Added to memory")
        self._update_memory_indicator()

    def _m_minus(self) -> None:
        value = self._current_result_or_eval()
        self.engine.memory_subtract(value)
        self._status("Subtracted from memory")
        self._update_memory_indicator()

    def _current_result_or_eval(self) -> float:
        text = self.result_var.get()
        if not text:
            text = self.engine.evaluate(self.equation_var.get())
            self.result_var.set(text)
        try:
            return float(text)
        except Exception:
            return 0.0

    # ----------------------------- Tape -----------------------------------
    def _refresh_tape(self) -> None:
        self.tape_list.delete(0, tk.END)
        items = self.engine.history[-200:]
        q = (self.tape_filter_var.get() or "").strip().lower()
        if q:
            items = [(e, r) for (e, r) in items if q in e.lower() or q in r.lower()]
        for expr, result in items:
            self.tape_list.insert(tk.END, f"{expr} = {result}")
        self.tape_list.see(tk.END)

    def _reuse_from_tape(self, _event: object) -> None:
        sel = self.tape_list.curselection()
        if not sel:
            return
        line = self.tape_list.get(sel[0])
        # Extract expression part before ' = '
        if " = " in line:
            expr = line.split(" = ", 1)[0]
            self.equation_var.set(expr)
            self.entry_equation.icursor(tk.END)

    def _toggle_tape(self) -> None:
        if self.tape_visible:
            self.tape_list.master.pack_forget()
            self.tape_visible = False
        else:
            self.tape_list.master.pack(side=tk.RIGHT, fill=tk.BOTH)
            self.tape_visible = True

    # --------------------------- Clipboard --------------------------------
    def _copy_result(self) -> None:
        text = self.result_var.get() or self.equation_var.get()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status("Copied")

    def _paste_into_equation(self) -> None:
        try:
            text = self.clipboard_get()
        except Exception:
            return
        self._append(text)

    # ---------------------------- Keyboard --------------------------------
    def _bind_keys(self) -> None:
        self.bind("<Return>", self._calculate)
        self.bind("<KP_Enter>", self._calculate)
        self.bind("<Escape>", lambda e: self._clear())
        self.bind("<BackSpace>", lambda e: self._backspace())
        self.bind_all("<Control-c>", lambda e: self._copy_result())
        self.bind_all("<Control-C>", lambda e: self._copy_result())
        self.bind_all("<Control-v>", lambda e: self._paste_into_equation())
        self.bind_all("<Control-V>", lambda e: self._paste_into_equation())
        # Navigate history into equation
        self.bind("<Up>", self._history_prev)
        self.bind("<Down>", self._history_next)

    # ----------------------------- Themes ---------------------------------
    def _apply_theme(self, name: str) -> None:
        self.theme = name
        if name == "Dark":
            bg = "#222"
            fg = "#eee"
            btn_bg = "#333"
            btn_active = "#444"
            eq_bg = "#43a047"
            eq_active = "#2e7d32"
            danger_bg = "#e53935"
            danger_active = "#c62828"
            tape_bg = "#1b1b1b"
            tape_fg = "#e0e0e0"
        elif name == "HighContrast":
            bg = "#000"
            fg = "#fff"
            btn_bg = "#111"
            btn_active = "#222"
            eq_bg = "#00ad2f"
            eq_active = "#009225"
            danger_bg = "#ff1f1f"
            danger_active = "#e01616"
            tape_bg = "#000"
            tape_fg = "#fff"
        else:
            bg = "#f3f3f3"
            fg = "#111"
            btn_bg = "#e6e6e6"
            btn_active = "#d9d9d9"
            eq_bg = "#2e7d32"
            eq_active = "#1b5e20"
            danger_bg = "#c62828"
            danger_active = "#b71c1c"
            tape_bg = "#ffffff"
            tape_fg = "#111"

        style = ttk.Style(self)
        # Use a theme that honors background configuration
        try:
            style.theme_use("clam")
        except Exception:
            pass

        pad = 12 if self.large_buttons else 8
        font_btn = ("Segoe UI", 13 if self.large_buttons else 12)
        font_eq = ("Segoe UI", 13 if self.large_buttons else 12, "bold")

        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TEntry", fieldbackground="#fff" if name != "Dark" else "#333", foreground=fg)
        style.configure("Result.TEntry", fieldbackground="#fff" if name != "Dark" else "#333", foreground=fg)
        style.configure("ResultError.TEntry", fieldbackground="#fff" if name != "Dark" else "#333", foreground="#e53935")
        style.configure("TButton", background=btn_bg, foreground=fg, padding=pad, font=font_btn)
        style.map("TButton", background=[("active", btn_active)])

        # Equals button style
        style.configure("Equals.TButton", background=eq_bg, foreground="#ffffff", padding=pad + 2, font=font_eq)
        style.map("Equals.TButton", background=[("active", eq_active)])

        # Danger buttons (Clear, Backspace)
        style.configure("Danger.TButton", background=danger_bg, foreground="#ffffff", padding=pad, font=font_eq)
        style.map("Danger.TButton", background=[("active", danger_active)])

        # Window background
        self.configure(background=bg)

        # Tape list styling
        try:
            self.tape_list.configure(bg=tape_bg, fg=tape_fg, selectbackground="#5c6bc0", selectforeground="#ffffff", highlightthickness=0, borderwidth=0)
        except Exception:
            pass

        # Apply result entry style neutral
        try:
            self.entry_result.configure(style="Result.TEntry")
        except Exception:
            pass

        # Memory indicator contrast
        self._update_memory_indicator()

    # --------------------------- Display helpers --------------------------
    def _display_result(self, text: str) -> None:
        if text.startswith("Error"):
            try:
                self.entry_result.configure(style="ResultError.TEntry")
            except Exception:
                pass
            self.result_var.set(text)
            return
        # Normal
        try:
            self.entry_result.configure(style="Result.TEntry")
        except Exception:
            pass
        display = text
        if self.readable_numbers:
            try:
                if "j" not in text and "(" not in text and ")" not in text and text not in ("inf", "-inf", "nan"):
                    if "." not in text and "e" not in text and "E" not in text:
                        # integer
                        display = f"{int(float(text)):,}"
                    else:
                        val = float(text)
                        # 15 sig figs then group integer part
                        s = ("%.*g" % (15, val))
                        if "e" in s or "E" in s:
                            display = s
                        else:
                            if "." in s:
                                whole, frac = s.split(".", 1)
                                display = f"{int(whole):,}." + frac
                            else:
                                display = f"{int(s):,}"
            except Exception:
                display = text
        self.result_var.set(display)

    # --------------------------- Context menus ----------------------------
    def _build_context_menus(self) -> None:
        self.eq_menu = tk.Menu(self, tearoff=0)
        self.eq_menu.add_command(label="Cut", command=lambda: self._entry_event(self.entry_equation, "<<Cut>>"))
        self.eq_menu.add_command(label="Copy", command=lambda: self._entry_event(self.entry_equation, "<<Copy>>"))
        self.eq_menu.add_command(label="Paste", command=lambda: self._entry_event(self.entry_equation, "<<Paste>>"))
        self.eq_menu.add_separator()
        self.eq_menu.add_command(label="Select All", command=lambda: self._select_all(self.entry_equation))
        self.eq_menu.add_command(label="Clear", command=lambda: self._clear())

        self.res_menu = tk.Menu(self, tearoff=0)
        self.res_menu.add_command(label="Copy Result", command=self._copy_result)

        self.entry_equation.bind("<Button-3>", lambda e: self._popup_menu(self.eq_menu, e))
        self.entry_result.bind("<Button-3>", lambda e: self._popup_menu(self.res_menu, e))

    def _popup_menu(self, menu: tk.Menu, event: tk.Event) -> None:  # type: ignore[valid-type]
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _entry_event(self, entry: ttk.Entry, sequence: str) -> None:
        entry.event_generate(sequence)

    def _select_all(self, entry: ttk.Entry) -> None:
        entry.select_range(0, tk.END)
        entry.icursor(tk.END)

    def _tape_context_menu(self, event: tk.Event) -> None:  # type: ignore[valid-type]
        idx = self.tape_list.nearest(event.y)
        if idx >= 0:
            self.tape_list.selection_clear(0, tk.END)
            self.tape_list.selection_set(idx)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copy Line", command=lambda: self._copy_tape_line(idx))
        menu.add_command(label="Reuse Expression", command=self._reuse_from_tape)
        self._popup_menu(menu, event)

    def _copy_tape_line(self, idx: int) -> None:
        if idx < 0:
            return
        text = self.tape_list.get(idx)
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status("Copied line")

    # ---------------------------- History nav -----------------------------
    def _history_prev(self, _event: object) -> None:
        if not self.engine.history:
            return
        if self._history_index is None:
            self._history_index = len(self.engine.history) - 1
        else:
            self._history_index = max(0, self._history_index - 1)
        expr = self.engine.history[self._history_index][0]
        self.equation_var.set(expr)
        self.entry_equation.icursor(tk.END)

    def _history_next(self, _event: object) -> None:
        if self._history_index is None:
            return
        if self._history_index >= len(self.engine.history) - 1:
            self._history_index = None
            return
        self._history_index += 1
        expr = self.engine.history[self._history_index][0]
        self.equation_var.set(expr)
        self.entry_equation.icursor(tk.END)

    # -------------------------- Memory indicator --------------------------
    def _update_memory_indicator(self) -> None:
        has_mem = bool(self.engine.memory_value)
        self.mem_label.configure(text="M" if has_mem else "")

    # --------------------------- Tools/Windows -----------------------------
    def _open_unit_converter(self) -> None:
        win = tk.Toplevel(self)
        win.title("Unit Converter")
        win.geometry("360x200")

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        value_var = tk.StringVar(value="1")
        from_var = tk.StringVar(value="m")
        to_var = tk.StringVar(value="km")
        result_var = tk.StringVar(value="")

        ttk.Label(frm, text="Value").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=value_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(frm, text="From").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=from_var).grid(row=1, column=1, sticky="ew")
        ttk.Label(frm, text="To").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=to_var).grid(row=2, column=1, sticky="ew")
        ttk.Label(frm, textvariable=result_var, font=("Segoe UI", 11, "bold")).grid(row=3, column=0, columnspan=2, pady=(8, 0))

        def do_convert() -> None:
            try:
                v = float(value_var.get())
                res = self.engine._convert_units(v, from_var.get(), to_var.get())
                result_var.set(str(res))
            except Exception as ex:
                result_var.set(f"Error: {type(ex).__name__}")

        ttk.Button(frm, text="Convert", command=do_convert).grid(row=4, column=0, columnspan=2, pady=(10, 0))
        frm.columnconfigure(1, weight=1)

    def _open_graph_window(self) -> None:
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
        except Exception:
            messagebox.showinfo("Graphing", "Install matplotlib to use graphing (pip install matplotlib)")
            return

        win = tk.Toplevel(self)
        win.title("Graph Function")
        win.geometry("520x420")

        frm = ttk.Frame(win)
        frm.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(frm, text="f(x) =").grid(row=0, column=0, sticky="w")
        fx_var = tk.StringVar(value="sin(x)")
        ttk.Entry(frm, textvariable=fx_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(frm, text="x min").grid(row=1, column=0, sticky="w")
        xmin_var = tk.StringVar(value="-360")
        ttk.Entry(frm, textvariable=xmin_var).grid(row=1, column=1, sticky="ew")
        ttk.Label(frm, text="x max").grid(row=2, column=0, sticky="w")
        xmax_var = tk.StringVar(value="360")
        ttk.Entry(frm, textvariable=xmax_var).grid(row=2, column=1, sticky="ew")

        fig = Figure(figsize=(5, 3), dpi=100)
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=frm)
        canvas.get_tk_widget().grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(8, 0))

        def plot() -> None:
            try:
                xmin = float(xmin_var.get())
                xmax = float(xmax_var.get())
                if xmax <= xmin:
                    raise ValueError("x max must be greater than x min")
                fx = fx_var.get()
                xs = []
                ys = []
                allowed = self.engine._allowed_names()
                steps = 400
                step = (xmax - xmin) / steps
                for i in range(steps + 1):
                    x = xmin + i * step
                    local = dict(allowed)
                    local.update({"x": x})
                    try:
                        y = eval(self.engine._preprocess_expression(fx), {"__builtins__": {}}, local)  # noqa: S307
                        if isinstance(y, complex):
                            y = y.real
                        xs.append(x)
                        ys.append(float(y))
                    except Exception:
                        continue
                ax.clear()
                ax.plot(xs, ys)
                ax.set_xlabel("x")
                ax.set_ylabel("f(x)")
                ax.grid(True, alpha=0.3)
                canvas.draw()
            except Exception as ex:
                messagebox.showerror("Graphing", f"Error: {ex}")

        ttk.Button(frm, text="Plot", command=plot).grid(row=3, column=0, columnspan=2, pady=(6, 0))
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(4, weight=1)

    # ----------------------------- Misc -----------------------------------
    def _toggle_sounds(self) -> None:
        self.enable_sounds = not self.enable_sounds

    def _status(self, msg: str) -> None:
        self.title(f"Calculator — {msg}")
        try:
            self.status_label.configure(text=msg)
        except Exception:
            pass
        self.after(1500, lambda: (self.title("Calculator"), self.status_label.configure(text="Ready") if hasattr(self, "status_label") else None))

    def _save_session(self) -> None:
        self.engine.save_session()
        self._save_ui_prefs()
        self._status("Session saved")

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            "Calculator with scientific functions, memory, tape, unit conversion, and graphing.",
        )

    def _on_close(self) -> None:
        try:
            self.engine.save_session()
            self._save_ui_prefs()
        finally:
            self.destroy()

    # -------------------------- UI preferences ----------------------------
    def _save_ui_prefs(self) -> None:
        try:
            data = {
                "theme": self.theme,
                "enable_sounds": self.enable_sounds,
                "readable_numbers": self.readable_numbers,
                "large_buttons": self.large_buttons,
                "geometry": self.geometry(),
            }
            with open(self._prefs_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_ui_prefs(self) -> None:
        try:
            if os.path.exists(self._prefs_path):
                with open(self._prefs_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.theme = data.get("theme", self.theme)
                self.enable_sounds = bool(data.get("enable_sounds", self.enable_sounds))
                self.readable_numbers = bool(data.get("readable_numbers", self.readable_numbers))
                self.large_buttons = bool(data.get("large_buttons", self.large_buttons))
                geo = data.get("geometry")
                if isinstance(geo, str):
                    try:
                        self.geometry(geo)
                    except Exception:
                        pass
                # Sync menu vars if present
                if hasattr(self, "_view_readable_var"):
                    self._view_readable_var.set(self.readable_numbers)
                if hasattr(self, "_view_large_var"):
                    self._view_large_var.set(self.large_buttons)
        except Exception:
            pass

    def _toggle_readable_numbers(self) -> None:
        self.readable_numbers = not self.readable_numbers if not hasattr(self, "_view_readable_var") else bool(self._view_readable_var.get())
        # Re-render displayed result
        txt = self.result_var.get()
        if txt:
            self._display_result(txt if not txt.startswith("Error") else txt)

    def _toggle_large_buttons(self) -> None:
        self.large_buttons = not self.large_buttons if not hasattr(self, "_view_large_var") else bool(self._view_large_var.get())
        self._apply_theme(self.theme)

    def _show_shortcuts(self) -> None:
        messagebox.showinfo(
            "Shortcuts",
            """
Enter: Evaluate
Esc: Clear
Backspace: Delete (erases entire ANS token)
Ctrl+C / Ctrl+V: Copy / Paste
Up / Down: Browse history into input
Double-click history: Reuse expression
            """.strip(),
        )

    def _clear_tape(self) -> None:
        self.engine.history.clear()
        self._refresh_tape()
        self._status("History cleared")

    # ------------------------------- Tooltip ------------------------------
    def _maybe_add_tooltip(self, widget: ttk.Button, label: str) -> None:
        tips = {
            "=": "Evaluate (Enter)",
            "C": "Clear (Esc)",
            "⌫": "Backspace",
            "ANS": "Insert last answer",
            "sin": "Sine (degrees)",
            "cos": "Cosine (degrees)",
            "tan": "Tangent (degrees)",
            "asin": "Arcsine (degrees)",
            "acos": "Arccosine (degrees)",
            "ln": "Natural log",
            "log": "Log base 10",
            "sqrt": "Square root",
            "factorial": "n! (integers only)",
            "MC": "Memory clear",
            "MR": "Memory recall",
            "M+": "Memory add",
            "M-": "Memory subtract",
        }
        tip = tips.get(label)
        if not tip:
            return
        Tooltip(widget, tip)


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tipwindow: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event: object = None) -> None:
        if self.tipwindow is not None:
            return
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0, 0, 0, 0)
        x = x + self.widget.winfo_rootx() + 20
        y = y + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", 9))
        label.pack(ipadx=6, ipady=3)

    def hide(self, _event: object = None) -> None:
        tw = self.tipwindow
        self.tipwindow = None
        if tw is not None:
            tw.destroy()


def main() -> int:
    app = CalculatorApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())


