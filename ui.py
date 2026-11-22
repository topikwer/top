from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Callable, Optional

from models import (
    ApplicationForm,
    Complaint,
    Consultation,
    Expert,
    Material,
    Payment,
    Slot,
    Student,
)
from modules import (
    ComplaintModule,
    KnowledgeBaseModule,
    PaymentModule,
    ProfileModule,
    ReviewModule,
    ScheduleAndConsultationsModule,
)
from storage import Storage

if TYPE_CHECKING:
    from app import Application


COLORS = {
    "bg": "#F4F6FA",
    "card": "#FFFFFF",
    "border": "#E2E8F0",
    "text": "#0F172A",
    "muted": "#64748B",
    "primary": "#4F46E5",
    "primary_hover": "#4338CA",
    "secondary": "#E2E8F0",
    "secondary_hover": "#CBD5E1",
    "success": "#10B981",
    "success_bg": "#DCFCE7",
    "success_fg": "#166534",
    "danger": "#EF4444",
    "danger_bg": "#FEE2E2",
    "danger_fg": "#991B1B",
    "warning_bg": "#FEF3C7",
    "warning_fg": "#92400E",
    "input_bg": "#F8FAFC",
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _darken_hex(hex_color: str, factor: float = 0.85) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex((int(r * factor), int(g * factor), int(b * factor)))


class ModernButton(tk.Label):
    """Кнопка с современным плоским стилем и плавной анимацией наведения (hover)."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command: Optional[Callable[[], None]] = None,
        variant: str = "primary",
        bg_color: Optional[str] = None,
        padx: int = 16,
        pady: int = 8,
        font_size: int = 12,
    ):
        self._command = command
        self._enabled = True
        self._anim_id: Optional[str] = None

        if bg_color:
            self._base_bg = bg_color
            self._hover_bg = _darken_hex(bg_color, 0.86)
            fg = "#FFFFFF"
        elif variant == "secondary":
            self._base_bg = COLORS["secondary"]
            self._hover_bg = COLORS["secondary_hover"]
            fg = COLORS["text"]
        elif variant == "danger":
            self._base_bg = COLORS["danger_bg"]
            self._hover_bg = "#FECACA"
            fg = COLORS["danger_fg"]
        elif variant == "success":
            self._base_bg = COLORS["success"]
            self._hover_bg = _darken_hex(COLORS["success"], 0.86)
            fg = "#FFFFFF"
        else:
            self._base_bg = COLORS["primary"]
            self._hover_bg = COLORS["primary_hover"]
            fg = "#FFFFFF"

        self._fg = fg
        super().__init__(
            parent,
            text=text,
            bg=self._base_bg,
            fg=fg,
            font=("SF Pro Text", font_size, "bold"),
            padx=padx,
            pady=pady,
            cursor="hand2",
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def config_state(self, state: str) -> None:
        if state == "disabled":
            self._enabled = False
            self.configure(bg="#CBD5E1", fg="#94A3B8", cursor="arrow")
        else:
            self._enabled = True
            self.configure(bg=self._base_bg, fg=self._fg, cursor="hand2")

    def _animate_bg(self, target_hex: str, steps: int = 5) -> None:
        if not self._enabled or not self.winfo_exists():
            return
        if self._anim_id:
            self.after_cancel(self._anim_id)
        start_rgb = _hex_to_rgb(self.cget("bg"))
        end_rgb = _hex_to_rgb(target_hex)

        def step(i: int) -> None:
            if not self.winfo_exists() or not self._enabled:
                return
            t = i / steps
            cur = (
                int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t),
                int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t),
                int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t),
            )
            self.configure(bg=_rgb_to_hex(cur))
            if i < steps:
                self._anim_id = self.after(16, lambda: step(i + 1))

        step(1)

    def _on_enter(self, _event: tk.Event) -> None:
        if self._enabled:
            self._animate_bg(self._hover_bg)

    def _on_leave(self, _event: tk.Event) -> None:
        if self._enabled:
            self._animate_bg(self._base_bg)

    def _on_click(self, _event: tk.Event) -> None:
        if self._enabled and self._command:
            self._command()


STATUS_LABELS = {
    "not_submitted": "Анкета не заполнена",
    "pending": "На проверке",
    "verified": "Верифицирован",
    "rejected": "Отклонена",
    "blocked": "Заблокирован",
    "confirmed": "Подтверждена",
    "completed": "Завершена",
    "free": "Свободен",
    "occupied": "Занят",
    "resolved": "Удовлетворена",
}


class BaseUI:
    def __init__(self, app: Application, storage: Storage):
        self.app = app
        self.storage = storage
        self._setup_ttk_styles()

    def _setup_ttk_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Modern.Treeview",
            background=COLORS["card"],
            foreground=COLORS["text"],
            fieldbackground=COLORS["card"],
            rowheight=32,
            borderwidth=0,
            font=("SF Pro Text", 12),
        )
        style.configure(
            "Modern.Treeview.Heading",
            background="#F1F5F9",
            foreground=COLORS["muted"],
            font=("SF Pro Text", 11, "bold"),
            relief="flat",
            padding=(8, 6),
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", "#E0E7FF")],
            foreground=[("selected", COLORS["primary"])],
        )

    def _create_card(self, parent: tk.Widget, padx: int = 22, pady: int = 18) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            padx=padx,
            pady=pady,
        )

    def _create_entry(self, parent: tk.Widget, textvariable: tk.StringVar, width: int = 42) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=textvariable,
            width=width,
            bg=COLORS["input_bg"],
            fg=COLORS["text"],
            font=("SF Pro Text", 12),
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["primary"],
        )

    def _create_text(self, parent: tk.Widget, height: int = 5, width: int = 56) -> tk.Text:
        return tk.Text(
            parent,
            height=height,
            width=width,
            bg=COLORS["input_bg"],
            fg=COLORS["text"],
            font=("SF Pro Text", 12),
            relief="solid",
            bd=1,
            wrap="word",
            padx=8,
            pady=6,
        )

    def _build_header(self, parent: tk.Frame, title: str, role_badge: str, badge_color: str = "#4F46E5") -> None:
        top = tk.Frame(parent, bg=COLORS["bg"])
        top.pack(fill="x", pady=(0, 14))

        left_nav = tk.Frame(top, bg=COLORS["bg"])
        left_nav.pack(side="left")
        tk.Label(
            left_nav,
            text="KNOWLEDGE HUB",
            font=("SF Pro Display", 11, "bold"),
            fg=COLORS["muted"],
            bg=COLORS["bg"],
        ).pack(side="left", padx=(0, 10))
        tk.Label(
            left_nav,
            text=f"  {role_badge.upper()}  ",
            font=("SF Pro Text", 10, "bold"),
            fg="#FFFFFF",
            bg=badge_color,
            pady=3,
        ).pack(side="left")

        right_nav = tk.Frame(top, bg=COLORS["bg"])
        right_nav.pack(side="right")
        ModernButton(
            right_nav,
            text="← Сменить раздел",
            command=self.app.open_role_selection,
            variant="secondary",
            padx=12,
            pady=5,
            font_size=11,
        ).pack(side="left", padx=(0, 8))
        if self.app.root:
            ModernButton(
                right_nav,
                text="✕",
                command=self.app.root.destroy,
                variant="danger",
                padx=10,
                pady=5,
                font_size=11,
            ).pack(side="left")

        tk.Label(
            parent,
            text=title,
            font=("SF Pro Display", 20, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        ).pack(anchor="w", pady=(0, 14))

    def _show_invalid_input(self, message: str = "Неверный ввод. Проверьте корректность заполнения полей.") -> None:
        messagebox.showerror("Неверный ввод", message)


class StudentUI(BaseUI):
    BADGE_COLOR = "#4F46E5"

    def __init__(
        self,
        app: Application,
        storage: Storage,
        profiles: ProfileModule,
        knowledge_base: KnowledgeBaseModule,
        schedule: ScheduleAndConsultationsModule,
        payment: PaymentModule,
        reviews: ReviewModule,
        complaints: ComplaintModule,
    ):
        super().__init__(app, storage)
        self.profiles = profiles
        self.knowledge_base = knowledge_base
        self.schedule = schedule
        self.payment = payment
        self.reviews = reviews
        self.complaints = complaints

        self.current_student: Optional[Student] = self.storage.get_latest_student()
        self.selected_expert: Optional[Expert] = None
        self.selected_material: Optional[Material] = None
        self.current_invoice: Optional[Payment] = None
        self.selected_consultation: Optional[Consultation] = None

    # SStart: Начало работы ученика
    def open_start(self) -> None:
        assert self.app.root is not None
        self.current_student = self.storage.get_latest_student()
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Начало работы ученика", "Ученик", self.BADGE_COLOR)

        cols = tk.Frame(frame, bg=COLORS["bg"])
        cols.pack(fill="both", expand=True, pady=6)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        left = self._create_card(cols, padx=24, pady=24)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tk.Label(
            left,
            text="✨  Новый пользователь",
            font=("SF Pro Display", 16, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Создайте новый профиль ученика, чтобы искать экспертов, изучать материалы и записываться на консультации.",
            wraplength=340,
            justify="left",
            font=("SF Pro Text", 12),
            fg=COLORS["muted"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(10, 22))
        ModernButton(left, text="Регистрация", command=self.open_registration, variant="secondary").pack(anchor="w")

        right = self._create_card(cols, padx=24, pady=24)
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        tk.Label(
            right,
            text="👤  Профиль уже создан",
            font=("SF Pro Display", 16, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w")

        if self.current_student:
            info = f"Текущий пользователь: {self.current_student.name}\nEmail: {self.current_student.email}"
            can_continue = True
        else:
            info = "Зарегистрированного профиля пока нет.\nНажмите «Регистрация» слева."
            can_continue = False

        tk.Label(
            right,
            text=info,
            wraplength=340,
            justify="left",
            font=("SF Pro Text", 12),
            fg=COLORS["text"] if can_continue else COLORS["muted"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(10, 22))
        btn_cont = ModernButton(right, text="Продолжить  →", command=self.open_search, bg_color=self.BADGE_COLOR)
        if not can_continue:
            btn_cont.config_state("disabled")
        btn_cont.pack(anchor="w")

        self.app.show_frame(frame)

    # SReg: Регистрация ученика
    def open_registration(self) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Регистрация ученика", "Ученик", self.BADGE_COLOR)

        card = self._create_card(frame, padx=28, pady=24)
        card.pack(anchor="w", fill="x")

        tk.Label(card, text="Имя *", font=("SF Pro Text", 12, "bold"), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        name_var = tk.StringVar()
        self._create_entry(card, name_var, width=44).pack(anchor="w", pady=(4, 14))

        tk.Label(card, text="Email *", font=("SF Pro Text", 12, "bold"), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        email_var = tk.StringVar()
        self._create_entry(card, email_var, width=44).pack(anchor="w", pady=(4, 8))

        err_label = tk.Label(card, text="", fg=COLORS["danger"], bg=COLORS["card"], font=("SF Pro Text", 11))
        err_label.pack(anchor="w", pady=(0, 14))

        def on_register() -> None:
            try:
                self.current_student = self.profiles.register_student(name_var.get(), email_var.get())
                self.open_search()
            except ValueError as e:
                err_label.config(text=str(e))
                self._show_invalid_input(str(e))

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(anchor="w")
        ModernButton(btns, text="Зарегистрироваться", command=on_register, bg_color=self.BADGE_COLOR).pack(
            side="left", padx=(0, 10)
        )
        ModernButton(btns, text="Назад", command=self.open_start, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # SSearch: Поиск экспертов
    def open_search(self, initial_query: str = "") -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Поиск экспертов", "Ученик", self.BADGE_COLOR)

        card = self._create_card(frame)
        card.pack(fill="both", expand=True)

        search_bar = tk.Frame(card, bg=COLORS["card"])
        search_bar.pack(fill="x", pady=(0, 10))
        tk.Label(
            search_bar,
            text="Тема или специализация:",
            font=("SF Pro Text", 12, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(side="left", padx=(0, 10))
        query_var = tk.StringVar(value=initial_query)
        self._create_entry(search_bar, query_var, width=36).pack(side="left", padx=(0, 10))

        status_lbl = tk.Label(card, text="", fg=COLORS["muted"], bg=COLORS["card"], font=("SF Pro Text", 11))
        status_lbl.pack(anchor="w", pady=(0, 8))

        columns = ("id", "name", "specialization", "rating")
        tree = ttk.Treeview(card, columns=columns, show="headings", height=9, style="Modern.Treeview")
        tree.heading("id", text="ID")
        tree.heading("name", text="Эксперт")
        tree.heading("specialization", text="Специализация")
        tree.heading("rating", text="Рейтинг")
        tree.column("id", width=55, anchor="center")
        tree.column("name", width=230)
        tree.column("specialization", width=350)
        tree.column("rating", width=110, anchor="center")
        tree.pack(fill="both", expand=True, pady=(0, 14))

        experts_map: dict[str, Expert] = {}

        def do_search() -> None:
            for item in tree.get_children():
                tree.delete(item)
            experts_map.clear()
            found = self.profiles.find_experts(query_var.get())
            if not found:
                status_lbl.config(text="По этой теме эксперты не найдены. Измените запрос.")
            else:
                status_lbl.config(text=f"Найдено верифицированных экспертов: {len(found)}")
                for exp in found:
                    iid = str(exp.id)
                    experts_map[iid] = exp
                    tree.insert(
                        "",
                        "end",
                        iid=iid,
                        values=(exp.id, exp.name, exp.specialization, f"★ {exp.rating:.1f}"),
                    )

        ModernButton(search_bar, text="Найти", command=do_search, bg_color=self.BADGE_COLOR, pady=6).pack(side="left")
        do_search()

        def on_open_profile() -> None:
            sel = tree.selection()
            if not sel:
                self._show_invalid_input("Выберите эксперта из списка.")
                return
            self.selected_expert = experts_map[sel[0]]
            self.open_expert_profile(self.selected_expert.id)

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(fill="x")
        ModernButton(btns, text="Открыть профиль", command=on_open_profile, bg_color=self.BADGE_COLOR).pack(
            side="left", padx=(0, 10)
        )
        ModernButton(btns, text="Мои консультации", command=self.open_my_consultations, variant="secondary").pack(
            side="left"
        )

        self.app.show_frame(frame)

    # SProfile: Профиль эксперта
    def open_expert_profile(self, expert_id: int, conflict_msg: str = "") -> None:
        assert self.app.root is not None
        expert = self.profiles.get_profile(expert_id)
        if not expert:
            self._show_invalid_input("Эксперт не найден.")
            self.open_search()
            return
        self.selected_expert = expert

        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, f"Профиль эксперта: {expert.name}", "Ученик", self.BADGE_COLOR)

        info_card = self._create_card(frame, padx=20, pady=14)
        info_card.pack(fill="x", pady=(0, 14))
        info_text = (
            f"Специализация: {expert.specialization}    •    "
            f"Квалификация: {expert.qualification}    •    "
            f"Рейтинг: ★ {expert.rating:.1f}"
        )
        tk.Label(info_card, text=info_text, font=("SF Pro Text", 12, "bold"), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )

        if conflict_msg:
            tk.Label(
                frame,
                text=f"⚠ {conflict_msg}",
                fg=COLORS["danger_fg"],
                bg=COLORS["danger_bg"],
                font=("SF Pro Text", 12, "bold"),
                padx=12,
                pady=6,
            ).pack(anchor="w", pady=(0, 10))

        panes = tk.Frame(frame, bg=COLORS["bg"])
        panes.pack(fill="both", expand=True, pady=(0, 14))
        panes.columnconfigure(0, weight=1)
        panes.columnconfigure(1, weight=1)

        # Left: Materials
        mat_box = self._create_card(panes, padx=16, pady=14)
        mat_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(
            mat_box,
            text="📚 Материалы эксперта",
            font=("SF Pro Display", 14, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 8))

        mat_tree = ttk.Treeview(mat_box, columns=("title", "type", "date"), show="headings", height=7, style="Modern.Treeview")
        mat_tree.heading("title", text="Название")
        mat_tree.heading("type", text="Тип")
        mat_tree.heading("date", text="Дата")
        mat_tree.column("title", width=210)
        mat_tree.column("type", width=85, anchor="center")
        mat_tree.column("date", width=95, anchor="center")
        mat_tree.pack(fill="both", expand=True, pady=(0, 10))

        for m in self.knowledge_base.get_expert_materials(expert.id):
            mat_tree.insert("", "end", iid=str(m.id), values=(m.title, m.type, m.publication_date.strftime("%d.%m.%Y")))

        def on_open_material() -> None:
            sel = mat_tree.selection()
            if not sel:
                self._show_invalid_input("Выберите материал из списка.")
                return
            mat = self.knowledge_base.open_material(self.current_student, int(sel[0]))
            if mat:
                self.selected_material = mat
                self.open_material_view(mat)

        ModernButton(mat_box, text="Открыть материал", command=on_open_material, variant="secondary").pack(anchor="w")

        # Right: Free slots
        slot_box = self._create_card(panes, padx=16, pady=14)
        slot_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        tk.Label(
            slot_box,
            text="🗓️ Свободные слоты",
            font=("SF Pro Display", 14, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 8))

        slot_tree = ttk.Treeview(slot_box, columns=("date", "time"), show="headings", height=7, style="Modern.Treeview")
        slot_tree.heading("date", text="Дата")
        slot_tree.heading("time", text="Время")
        slot_tree.column("date", width=160, anchor="center")
        slot_tree.column("time", width=130, anchor="center")
        slot_tree.pack(fill="both", expand=True, pady=(0, 10))

        for s in self.schedule.get_free_slots(expert):
            slot_tree.insert(
                "",
                "end",
                iid=str(s.id),
                values=(s.date_time.strftime("%d.%m.%Y"), s.date_time.strftime("%H:%M")),
            )

        def on_select_slot() -> None:
            if not self.current_student:
                self._show_invalid_input("Сначала зарегистрируйте профиль ученика.")
                return
            sel = slot_tree.selection()
            if not sel:
                self._show_invalid_input("Выберите свободный слот в расписании.")
                return
            slot_id = int(sel[0])
            invoice = self.schedule.book_consultation(self.current_student, slot_id)
            if invoice is None:
                self.open_expert_profile(expert.id, conflict_msg="Это время уже занято. Выберите другой слот.")
                return
            self.current_invoice = invoice
            self.open_payment(invoice)

        ModernButton(slot_box, text="Выбрать слот  →", command=on_select_slot, bg_color=self.BADGE_COLOR).pack(anchor="w")

        footer = tk.Frame(frame, bg=COLORS["bg"])
        footer.pack(fill="x")
        ModernButton(footer, text="← К поиску", command=self.open_search, variant="secondary").pack(side="left")
        ModernButton(
            footer,
            text="Пожаловаться на эксперта",
            command=lambda: self.open_complaint_form(expert=expert, material=None),
            variant="danger",
        ).pack(side="right")

        self.app.show_frame(frame)

    # SMaterial: Просмотр материала
    def open_material_view(self, material: Material) -> None:
        assert self.app.root is not None
        self.selected_material = material
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, material.title, "Ученик", self.BADGE_COLOR)

        card = self._create_card(frame)
        card.pack(fill="both", expand=True, pady=(0, 14))

        author_name = material.author.name if material.author else "Неизвестен"
        meta = f"Автор: {author_name}   •   Тип: {material.type}   •   Опубликовано: {material.publication_date.strftime('%d.%m.%Y')}"
        tk.Label(card, text=meta, font=("SF Pro Text", 11, "bold"), fg=COLORS["muted"], bg=COLORS["card"]).pack(
            anchor="w", pady=(0, 12)
        )

        text_box = tk.Text(
            card,
            height=14,
            wrap="word",
            font=("SF Pro Text", 12),
            bg=COLORS["input_bg"],
            fg=COLORS["text"],
            relief="flat",
            padx=14,
            pady=12,
        )
        text_box.insert("1.0", material.content)
        text_box.config(state="disabled")
        text_box.pack(fill="both", expand=True)

        footer = tk.Frame(frame, bg=COLORS["bg"])
        footer.pack(fill="x")
        back_id = material.author.id if material.author else (self.selected_expert.id if self.selected_expert else 0)
        ModernButton(footer, text="← Назад к профилю", command=lambda: self.open_expert_profile(back_id), variant="secondary").pack(
            side="left"
        )
        if material.author:
            ModernButton(
                footer,
                text="Жалоба на материал",
                command=lambda: self.open_complaint_form(expert=material.author, material=material),
                variant="danger",
            ).pack(side="right")

        self.app.show_frame(frame)

    # SPay: Оплата консультации (с проверкой ввода и анимированным прогресс-баром)
    def open_payment(self, invoice: Payment) -> None:
        assert self.app.root is not None
        self.current_invoice = invoice
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Оплата консультации", "Ученик", self.BADGE_COLOR)

        slot = invoice.slot
        expert_name = slot.expert.name if (slot and slot.expert) else "Эксперт"
        dt_str = slot.date_time.strftime("%d.%m.%Y %H:%M") if slot else "-"

        info = self._create_card(frame, padx=22, pady=16)
        info.pack(fill="x", pady=(0, 14))
        tk.Label(info, text="Детали бронирования", font=("SF Pro Display", 14, "bold"), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w", pady=(0, 6)
        )
        tk.Label(info, text=f"Эксперт: {expert_name}", font=("SF Pro Text", 12), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        tk.Label(info, text=f"Дата и время: {dt_str}", font=("SF Pro Text", 12), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        tk.Label(
            info,
            text=f"К оплате: {invoice.amount:.2f} руб.",
            font=("SF Pro Display", 15, "bold"),
            fg=self.BADGE_COLOR,
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(6, 0))

        pay_box = self._create_card(frame, padx=22, pady=18)
        pay_box.pack(fill="x", pady=(0, 14))
        tk.Label(
            pay_box,
            text="Платёжные реквизиты (учебная имитация)",
            font=("SF Pro Display", 14, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            pay_box,
            text="Введите номер карты (например, 4276 5500 1234 5678). Введите 0000 для проверки ветви отказа:",
            font=("SF Pro Text", 11),
            fg=COLORS["muted"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 8))
        details_var = tk.StringVar(value="4276 5500 1234 5678")
        self._create_entry(pay_box, details_var, width=38).pack(anchor="w", pady=(0, 10))

        status_lbl = tk.Label(pay_box, text="", fg=self.BADGE_COLOR, bg=COLORS["card"], font=("SF Pro Text", 12, "bold"))
        status_lbl.pack(anchor="w")

        progress_track = tk.Frame(pay_box, bg="#E2E8F0", height=6, width=320)
        progress_fill = tk.Frame(progress_track, bg=self.BADGE_COLOR, height=6, width=0)

        pay_btn = ModernButton(frame, text="Оплатить консультацию", bg_color=self.BADGE_COLOR)
        back_btn = ModernButton(
            frame,
            text="Назад",
            command=lambda: self.open_expert_profile(slot.expert.id) if (slot and slot.expert) else self.open_search(),
            variant="secondary",
        )

        def on_pay() -> None:
            details = details_var.get().strip()
            if not details or len(details) < 4:
                self._show_invalid_input("Введите корректные платёжные реквизиты (минимум 4 символа).")
                return

            pay_btn.config_state("disabled")
            back_btn.config_state("disabled")
            status_lbl.config(text="Ожидаем результат оплаты от шлюза...")
            progress_track.pack(anchor="w", pady=(8, 0))
            progress_fill.place(x=0, y=0, width=0)

            def animate_progress(w: int) -> None:
                if not progress_fill.winfo_exists():
                    return
                if w < 320:
                    next_w = min(320, w + 32)
                    progress_fill.place(x=0, y=0, width=next_w)
                    self.app.root.after(30, lambda: animate_progress(next_w))
                else:
                    try:
                        success = self.payment.pay_consultation(invoice, details)
                    except ValueError as e:
                        pay_btn.config_state("normal")
                        back_btn.config_state("normal")
                        status_lbl.config(text="")
                        self._show_invalid_input(str(e))
                        return
                    if success:
                        self.open_booking_confirmed(invoice)
                    else:
                        self.open_payment_error(invoice, "Платёжная система отклонила операцию.")

            animate_progress(0)

        pay_btn._command = on_pay

        btns = tk.Frame(frame, bg=COLORS["bg"])
        btns.pack(anchor="w")
        pay_btn.pack(in_=btns, side="left", padx=(0, 10))
        back_btn.pack(in_=btns, side="left")

        self.app.show_frame(frame)

    # SPayError: Ошибка оплаты
    def open_payment_error(self, invoice: Payment, error_msg: str) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Ошибка оплаты", "Ученик", self.BADGE_COLOR)

        card = self._create_card(frame, padx=26, pady=24)
        card.pack(fill="x", pady=(0, 16))
        tk.Label(
            card,
            text="✕  Оплата не прошла",
            font=("SF Pro Display", 16, "bold"),
            fg=COLORS["danger"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            card,
            text="Запись на консультацию не подтверждена, выбранный слот остался свободным.\nПроверьте способ оплаты или выберите другое время.",
            justify="left",
            font=("SF Pro Text", 12),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(card, text=f"Причина отказа: {error_msg}", fg=COLORS["muted"], bg=COLORS["card"]).pack(anchor="w")

        slot = invoice.slot
        expert_id = slot.expert.id if (slot and slot.expert) else 0

        btns = tk.Frame(frame, bg=COLORS["bg"])
        btns.pack(anchor="w")
        ModernButton(btns, text="Другой способ оплаты", command=lambda: self.open_payment(invoice), bg_color=self.BADGE_COLOR).pack(
            side="left", padx=(0, 10)
        )
        ModernButton(
            btns,
            text="Другое время",
            command=lambda: self.open_expert_profile(expert_id) if expert_id else self.open_search(),
            variant="secondary",
        ).pack(side="left")

        self.app.show_frame(frame)

    # SConfirmed: Запись подтверждена
    def open_booking_confirmed(self, invoice: Payment) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Запись подтверждена", "Ученик", self.BADGE_COLOR)

        slot = invoice.slot
        expert_name = slot.expert.name if (slot and slot.expert) else "Эксперт"
        dt_str = slot.date_time.strftime("%d.%m.%Y %H:%M") if slot else "-"

        card = self._create_card(frame, padx=26, pady=24)
        card.pack(fill="x", pady=(0, 16))
        tk.Label(
            card,
            text="✓  Вы успешно записаны на консультацию!",
            font=("SF Pro Display", 16, "bold"),
            fg=COLORS["success_fg"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(card, text=f"Эксперт: {expert_name}", font=("SF Pro Text", 12), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        tk.Label(
            card,
            text=f"Дата и время: {dt_str}",
            font=("SF Pro Text", 12),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w")
        tk.Label(
            card,
            text="Статус: Подтверждена",
            font=("SF Pro Text", 12, "bold"),
            fg=COLORS["success_fg"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(4, 10))
        tk.Label(
            card,
            text="Уведомления о записи отправлены ученику и эксперту. Запись доступна в разделе «Мои консультации».",
            justify="left",
            font=("SF Pro Text", 11),
            fg=COLORS["muted"],
            bg=COLORS["card"],
        ).pack(anchor="w")

        btns = tk.Frame(frame, bg=COLORS["bg"])
        btns.pack(anchor="w")
        ModernButton(btns, text="Мои консультации", command=self.open_my_consultations, bg_color=self.BADGE_COLOR).pack(
            side="left", padx=(0, 10)
        )
        ModernButton(btns, text="К поиску", command=self.open_search, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # SList: Мои консультации (ученик)
    def open_my_consultations(self) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Мои консультации", "Ученик", self.BADGE_COLOR)

        card = self._create_card(frame)
        card.pack(fill="both", expand=True)

        if not self.current_student:
            tk.Label(card, text="Сначала создайте профиль ученика.", bg=COLORS["card"]).pack(anchor="w", pady=10)
            ModernButton(card, text="Назад", command=self.open_start, variant="secondary").pack(anchor="w")
            self.app.show_frame(frame)
            return

        consultations = self.storage.find_consultations_by_student(self.current_student.id)
        if not consultations:
            tk.Label(card, text="У вас пока нет записей на консультации.", fg=COLORS["muted"], bg=COLORS["card"]).pack(
                anchor="w", pady=(0, 10)
            )

        tree = ttk.Treeview(card, columns=("expert", "date", "time", "status"), show="headings", height=9, style="Modern.Treeview")
        tree.heading("expert", text="Эксперт")
        tree.heading("date", text="Дата")
        tree.heading("time", text="Время")
        tree.heading("status", text="Статус")
        tree.column("expert", width=260)
        tree.column("date", width=130, anchor="center")
        tree.column("time", width=110, anchor="center")
        tree.column("status", width=160, anchor="center")
        tree.pack(fill="both", expand=True, pady=(0, 14))

        cons_map: dict[str, Consultation] = {}
        for c in consultations:
            iid = str(c.id)
            cons_map[iid] = c
            exp_name = c.expert.name if c.expert else "Эксперт"
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    exp_name,
                    c.date_time.strftime("%d.%m.%Y"),
                    c.date_time.strftime("%H:%M"),
                    STATUS_LABELS.get(c.status, c.status),
                ),
            )

        def on_open() -> None:
            sel = tree.selection()
            if not sel:
                self._show_invalid_input("Выберите консультацию из списка.")
                return
            self.selected_consultation = cons_map[sel[0]]
            self.open_selected_consultation(self.selected_consultation)

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(fill="x")
        ModernButton(btns, text="Открыть", command=on_open, bg_color=self.BADGE_COLOR).pack(side="left", padx=(0, 10))
        ModernButton(btns, text="К поиску", command=self.open_search, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # SConsult: Выбранная консультация
    def open_selected_consultation(self, consultation: Consultation) -> None:
        assert self.app.root is not None
        fresh = self.storage.find_consultation(consultation.id) or consultation
        self.selected_consultation = fresh

        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Выбранная консультация", "Ученик", self.BADGE_COLOR)

        card = self._create_card(frame, padx=24, pady=22)
        card.pack(fill="x", pady=(0, 16))

        exp_name = fresh.expert.name if fresh.expert else "Эксперт"
        spec = fresh.expert.specialization if fresh.expert else "-"
        tk.Label(
            card,
            text=f"Консультация с экспертом: {exp_name}",
            font=("SF Pro Display", 15, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            card,
            text=f"Дата и время: {fresh.date_time.strftime('%d.%m.%Y %H:%M')}",
            font=("SF Pro Text", 12),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w")
        tk.Label(card, text=f"Специализация: {spec}", font=("SF Pro Text", 12), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        tk.Label(
            card,
            text=f"Статус: {STATUS_LABELS.get(fresh.status, fresh.status)}",
            font=("SF Pro Text", 12, "bold"),
            fg=self.BADGE_COLOR,
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(4, 12))

        existing_review = self.storage.find_review_by_consultation(fresh.id)
        if existing_review:
            tk.Label(
                card,
                text=f"★ Ваш отзыв: оценка {existing_review.rating}/5 — {existing_review.comment or 'без комментария'}",
                fg=COLORS["success_fg"],
                bg=COLORS["success_bg"],
                font=("SF Pro Text", 12),
                padx=10,
                pady=6,
            ).pack(anchor="w")
        else:
            tk.Label(
                card,
                text="Отзыв: ещё не оставлен (доступен после завершения консультации экспертом)",
                fg=COLORS["muted"],
                bg=COLORS["card"],
            ).pack(anchor="w")

        btns = tk.Frame(frame, bg=COLORS["bg"])
        btns.pack(anchor="w")
        review_btn = ModernButton(btns, text="Оставить отзыв", command=lambda: self.open_review_form(fresh), bg_color=self.BADGE_COLOR)
        if fresh.status != "completed" or existing_review is not None:
            review_btn.config_state("disabled")
        review_btn.pack(side="left", padx=(0, 10))
        ModernButton(btns, text="← К списку", command=self.open_my_consultations, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # SReview: Отзыв о консультации
    def open_review_form(self, consultation: Consultation) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Отзыв о консультации", "Ученик", self.BADGE_COLOR)

        card = self._create_card(frame, padx=24, pady=22)
        card.pack(fill="x")

        exp_name = consultation.expert.name if consultation.expert else "Эксперт"
        tk.Label(
            card,
            text=f"{exp_name}  •  {consultation.date_time.strftime('%d.%m.%Y %H:%M')}  •  Завершена",
            font=("SF Pro Text", 12, "bold"),
            fg=COLORS["muted"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 14))

        tk.Label(card, text="Оценка (от 1 до 5) *", font=("SF Pro Text", 12, "bold"), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        rating_var = tk.StringVar(value="5")
        ttk.Combobox(card, textvariable=rating_var, values=["5", "4", "3", "2", "1"], state="readonly", width=10).pack(
            anchor="w", pady=(4, 14)
        )

        tk.Label(card, text="Комментарий", font=("SF Pro Text", 12, "bold"), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        comment_text = self._create_text(card, height=5, width=58)
        comment_text.pack(anchor="w", pady=(4, 8))

        err_lbl = tk.Label(card, text="", fg=COLORS["danger"], bg=COLORS["card"], font=("SF Pro Text", 11))
        err_lbl.pack(anchor="w", pady=(0, 12))

        def on_submit() -> None:
            if not self.current_student:
                self._show_invalid_input("Профиль ученика не найден.")
                return
            try:
                rating_val = int(rating_var.get())
                self.reviews.leave_review(
                    student=self.current_student,
                    consultation_id=consultation.id,
                    rating=rating_val,
                    comment=comment_text.get("1.0", "end"),
                )
                self.open_selected_consultation(consultation)
            except ValueError as e:
                err_lbl.config(text=str(e))
                self._show_invalid_input(str(e))

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(anchor="w")
        ModernButton(btns, text="Оставить отзыв", command=on_submit, bg_color=self.BADGE_COLOR).pack(side="left", padx=(0, 10))
        ModernButton(btns, text="Отмена", command=lambda: self.open_selected_consultation(consultation), variant="secondary").pack(
            side="left"
        )

        self.app.show_frame(frame)

    # SComplaint / SComplaintMaterial: Форма жалобы
    def open_complaint_form(self, expert: Expert, material: Optional[Material]) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        title = "Жалоба на материал" if material else "Жалоба на эксперта"
        self._build_header(frame, title, "Ученик", self.BADGE_COLOR)

        card = self._create_card(frame, padx=24, pady=22)
        card.pack(fill="x")

        tk.Label(card, text=f"Эксперт: {expert.name}", font=("SF Pro Text", 12, "bold"), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        if material:
            tk.Label(
                card,
                text=f"Материал: «{material.title}»",
                font=("SF Pro Text", 12),
                fg=COLORS["muted"],
                bg=COLORS["card"],
            ).pack(anchor="w", pady=(2, 12))
        else:
            tk.Label(card, text="Объект: поведение эксперта", font=("SF Pro Text", 12), fg=COLORS["muted"], bg=COLORS["card"]).pack(
                anchor="w", pady=(2, 12)
            )

        tk.Label(card, text="Причина жалобы *", font=("SF Pro Text", 12, "bold"), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        reason_text = self._create_text(card, height=6, width=60)
        reason_text.pack(anchor="w", pady=(4, 8))

        err_lbl = tk.Label(card, text="", fg=COLORS["danger"], bg=COLORS["card"], font=("SF Pro Text", 11))
        err_lbl.pack(anchor="w", pady=(0, 12))

        def on_back() -> None:
            if material:
                self.open_material_view(material)
            else:
                self.open_expert_profile(expert.id)

        def on_send() -> None:
            if not self.current_student:
                self._show_invalid_input("Сначала зарегистрируйте профиль ученика.")
                return
            try:
                self.complaints.submit_complaint(
                    student=self.current_student,
                    expert_id=expert.id,
                    material_id=material.id if material else None,
                    reason=reason_text.get("1.0", "end"),
                )
                self.open_complaint_sent(expert, material)
            except ValueError as e:
                err_lbl.config(text=str(e))
                self._show_invalid_input(str(e))

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(anchor="w")
        ModernButton(btns, text="Отправить жалобу", command=on_send, variant="danger").pack(side="left", padx=(0, 10))
        ModernButton(btns, text="Отмена", command=on_back, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # SComplaintSent / SComplaintSentMaterial: Жалоба отправлена
    def open_complaint_sent(self, expert: Expert, material: Optional[Material]) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        title = "Жалоба на материал отправлена" if material else "Жалоба отправлена"
        self._build_header(frame, title, "Ученик", self.BADGE_COLOR)

        card = self._create_card(frame, padx=24, pady=22)
        card.pack(fill="x", pady=(0, 16))
        tk.Label(
            card,
            text="✓  Обращение принято",
            font=("SF Pro Display", 16, "bold"),
            fg=COLORS["success_fg"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(card, text="Жалоба передана модератору на рассмотрение.", font=("SF Pro Text", 12), bg=COLORS["card"]).pack(
            anchor="w"
        )
        tk.Label(card, text=f"Эксперт: {expert.name}", font=("SF Pro Text", 12), bg=COLORS["card"]).pack(anchor="w")
        if material:
            tk.Label(card, text=f"Материал: «{material.title}»", font=("SF Pro Text", 12), bg=COLORS["card"]).pack(anchor="w")
        else:
            tk.Label(card, text="Объект: поведение эксперта", font=("SF Pro Text", 12), bg=COLORS["card"]).pack(anchor="w")

        def on_done() -> None:
            if material:
                self.open_material_view(material)
            else:
                self.open_expert_profile(expert.id)

        ModernButton(frame, text="Готово", command=on_done, bg_color=self.BADGE_COLOR).pack(anchor="w")
        self.app.show_frame(frame)


class ExpertUI(BaseUI):
    BADGE_COLOR = "#0D9488"

    def __init__(
        self,
        app: Application,
        storage: Storage,
        profiles: ProfileModule,
        knowledge_base: KnowledgeBaseModule,
        schedule: ScheduleAndConsultationsModule,
    ):
        super().__init__(app, storage)
        self.profiles = profiles
        self.knowledge_base = knowledge_base
        self.schedule = schedule

        self.current_expert: Optional[Expert] = self.storage.get_latest_expert()
        self.selected_consultation: Optional[Consultation] = None

    # EStart: Начало работы эксперта
    def open_start(self) -> None:
        assert self.app.root is not None
        self.current_expert = self.storage.get_latest_expert()
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Начало работы эксперта", "Эксперт", self.BADGE_COLOR)

        cols = tk.Frame(frame, bg=COLORS["bg"])
        cols.pack(fill="both", expand=True, pady=6)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        left = self._create_card(cols, padx=24, pady=24)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tk.Label(
            left,
            text="✨  Новый эксперт",
            font=("SF Pro Display", 16, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Создайте новый профиль эксперта, затем заполните анкету для прохождения верификации модератором.",
            wraplength=340,
            justify="left",
            font=("SF Pro Text", 12),
            fg=COLORS["muted"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(10, 22))
        ModernButton(left, text="Регистрация", command=self.open_registration, variant="secondary").pack(anchor="w")

        right = self._create_card(cols, padx=24, pady=24)
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        tk.Label(
            right,
            text="💼  Профиль уже создан",
            font=("SF Pro Display", 16, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w")
        if self.current_expert:
            st = STATUS_LABELS.get(self.current_expert.verification_status, self.current_expert.verification_status)
            info = f"Текущий эксперт: {self.current_expert.name}\nСтатус: {st}"
            can_continue = True
        else:
            info = "Зарегистрированного профиля эксперта пока нет."
            can_continue = False
        tk.Label(
            right,
            text=info,
            wraplength=340,
            justify="left",
            font=("SF Pro Text", 12),
            fg=COLORS["text"] if can_continue else COLORS["muted"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(10, 22))
        btn_cont = ModernButton(right, text="Продолжить  →", command=self.open_cabinet, bg_color=self.BADGE_COLOR)
        if not can_continue:
            btn_cont.config_state("disabled")
        btn_cont.pack(anchor="w")

        self.app.show_frame(frame)

    # EReg: Регистрация эксперта
    def open_registration(self) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Регистрация эксперта", "Эксперт", self.BADGE_COLOR)

        card = self._create_card(frame, padx=28, pady=24)
        card.pack(anchor="w", fill="x")

        tk.Label(card, text="Имя *", font=("SF Pro Text", 12, "bold"), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w"
        )
        name_var = tk.StringVar()
        self._create_entry(card, name_var, width=44).pack(anchor="w", pady=(4, 8))

        err_lbl = tk.Label(card, text="", fg=COLORS["danger"], bg=COLORS["card"], font=("SF Pro Text", 11))
        err_lbl.pack(anchor="w", pady=(0, 14))

        def on_register() -> None:
            try:
                self.current_expert = self.profiles.register_expert(name_var.get())
                self.open_cabinet()
            except ValueError as e:
                err_lbl.config(text=str(e))
                self._show_invalid_input(str(e))

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(anchor="w")
        ModernButton(btns, text="Зарегистрироваться", command=on_register, bg_color=self.BADGE_COLOR).pack(
            side="left", padx=(0, 10)
        )
        ModernButton(btns, text="Назад", command=self.open_start, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # ECabinet: Кабинет эксперта
    def open_cabinet(self) -> None:
        assert self.app.root is not None
        if self.current_expert:
            self.current_expert = self.storage.find_expert(self.current_expert.id) or self.current_expert

        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Кабинет эксперта", "Эксперт", self.BADGE_COLOR)

        if not self.current_expert:
            tk.Label(frame, text="Профиль эксперта не выбран.", bg=COLORS["bg"]).pack(anchor="w")
            self.app.show_frame(frame)
            return

        exp = self.current_expert
        form = self.storage.find_expert_application_form(exp.id)
        is_blocked = exp.verification_status == "blocked"
        is_verified = exp.verification_status == "verified"

        card = self._create_card(frame, padx=26, pady=22)
        card.pack(fill="x", pady=(0, 16))

        tk.Label(card, text=exp.name, font=("SF Pro Display", 18, "bold"), fg=COLORS["text"], bg=COLORS["card"]).pack(
            anchor="w", pady=(0, 6)
        )
        tk.Label(card, text=f"Специализация: {exp.specialization}", font=("SF Pro Text", 12), bg=COLORS["card"]).pack(anchor="w")
        tk.Label(card, text=f"Квалификация: {exp.qualification}", font=("SF Pro Text", 12), bg=COLORS["card"]).pack(anchor="w")
        tk.Label(card, text=f"Рейтинг: ★ {exp.rating:.1f}", font=("SF Pro Text", 12), bg=COLORS["card"]).pack(
            anchor="w", pady=(0, 8)
        )

        st_label = STATUS_LABELS.get(exp.verification_status, exp.verification_status)
        st_bg = COLORS["success_bg"] if is_verified else (COLORS["danger_bg"] if is_blocked else COLORS["warning_bg"])
        st_fg = COLORS["success_fg"] if is_verified else (COLORS["danger_fg"] if is_blocked else COLORS["warning_fg"])

        badges = tk.Frame(card, bg=COLORS["card"])
        badges.pack(anchor="w", pady=(2, 6))
        tk.Label(badges, text=f"  Статус: {st_label}  ", bg=st_bg, fg=st_fg, font=("SF Pro Text", 11, "bold"), pady=4).pack(
            side="left", padx=(0, 10)
        )
        tk.Label(
            badges,
            text=f"  Доступ: {'заблокирован' if is_blocked else 'открыт'}  ",
            bg=COLORS["danger_bg"] if is_blocked else "#E0F2FE",
            fg=COLORS["danger_fg"] if is_blocked else "#0369A1",
            font=("SF Pro Text", 11, "bold"),
            pady=4,
        ).pack(side="left")

        if form and form.status == "rejected" and form.rejection_reason:
            tk.Label(
                card,
                text=f"Причина отклонения анкеты: {form.rejection_reason}",
                fg=COLORS["danger"],
                bg=COLORS["card"],
                font=("SF Pro Text", 12, "bold"),
            ).pack(anchor="w", pady=(8, 0))

        btns = tk.Frame(frame, bg=COLORS["bg"])
        btns.pack(anchor="w")
        ModernButton(btns, text="Заполнить анкету", command=self.open_form_editor, variant="secondary").pack(
            side="left", padx=(0, 10)
        )

        work_btn = ModernButton(
            btns,
            text="Материалы и расписание",
            command=self.open_materials_and_schedule,
            bg_color=self.BADGE_COLOR,
        )
        if not is_verified or is_blocked:
            work_btn.config_state("disabled")
        work_btn.pack(side="left", padx=(0, 10))

        ModernButton(btns, text="Мои консультации", command=self.open_expert_consultations, variant="secondary").pack(
            side="left"
        )

        self.app.show_frame(frame)

    # EForm: Редактирование анкеты
    def open_form_editor(self) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Редактирование анкеты", "Эксперт", self.BADGE_COLOR)

        card = self._create_card(frame, padx=26, pady=22)
        card.pack(fill="x")

        tk.Label(card, text="Специализация *", font=("SF Pro Text", 12, "bold"), bg=COLORS["card"]).pack(anchor="w")
        spec_var = tk.StringVar(
            value=""
            if (not self.current_expert or self.current_expert.specialization == "не указана")
            else self.current_expert.specialization
        )
        self._create_entry(card, spec_var, width=52).pack(anchor="w", pady=(4, 14))

        tk.Label(card, text="Квалификация *", font=("SF Pro Text", 12, "bold"), bg=COLORS["card"]).pack(anchor="w")
        qual_text = self._create_text(card, height=5, width=58)
        if self.current_expert and self.current_expert.qualification != "не указана":
            qual_text.insert("1.0", self.current_expert.qualification)
        qual_text.pack(anchor="w", pady=(4, 8))

        err_lbl = tk.Label(card, text="", fg=COLORS["danger"], bg=COLORS["card"], font=("SF Pro Text", 11))
        err_lbl.pack(anchor="w", pady=(0, 12))

        def on_submit() -> None:
            if not self.current_expert:
                return
            try:
                self.profiles.fill_application_form(
                    expert=self.current_expert,
                    specialization=spec_var.get(),
                    qualification=qual_text.get("1.0", "end"),
                )
                self.open_cabinet()
            except ValueError as e:
                err_lbl.config(text=str(e))
                self._show_invalid_input(str(e))

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(anchor="w")
        ModernButton(btns, text="Отправить анкету", command=on_submit, bg_color=self.BADGE_COLOR).pack(side="left", padx=(0, 10))
        ModernButton(btns, text="Отмена", command=self.open_cabinet, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # EWork: Материалы и расписание
    def open_materials_and_schedule(self) -> None:
        assert self.app.root is not None
        if not self.current_expert:
            return
        self.current_expert = self.storage.find_expert(self.current_expert.id) or self.current_expert
        exp = self.current_expert

        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Материалы и расписание", "Эксперт", self.BADGE_COLOR)

        panes = tk.Frame(frame, bg=COLORS["bg"])
        panes.pack(fill="both", expand=True, pady=(0, 14))
        panes.columnconfigure(0, weight=1)
        panes.columnconfigure(1, weight=1)

        # Left: Published materials
        left = self._create_card(panes, padx=16, pady=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(left, text="📚 Опубликованные материалы", font=("SF Pro Display", 14, "bold"), bg=COLORS["card"]).pack(
            anchor="w", pady=(0, 8)
        )
        mat_tree = ttk.Treeview(left, columns=("title", "type"), show="headings", height=7, style="Modern.Treeview")
        mat_tree.heading("title", text="Заголовок")
        mat_tree.heading("type", text="Тип")
        mat_tree.column("title", width=270)
        mat_tree.column("type", width=95, anchor="center")
        mat_tree.pack(fill="both", expand=True, pady=(0, 10))

        for m in self.knowledge_base.get_expert_materials(exp.id):
            mat_tree.insert("", "end", values=(m.title, m.type))

        ModernButton(left, text="+ Добавить материал", command=self.open_publish_material, bg_color=self.BADGE_COLOR).pack(
            anchor="w"
        )

        # Right: Free slots
        right = self._create_card(panes, padx=16, pady=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        tk.Label(right, text="🗓️ Свободные слоты", font=("SF Pro Display", 14, "bold"), bg=COLORS["card"]).pack(
            anchor="w", pady=(0, 8)
        )
        slot_tree = ttk.Treeview(right, columns=("date", "time"), show="headings", height=5, style="Modern.Treeview")
        slot_tree.heading("date", text="Дата")
        slot_tree.heading("time", text="Время")
        slot_tree.column("date", width=150, anchor="center")
        slot_tree.column("time", width=120, anchor="center")
        slot_tree.pack(fill="both", expand=True, pady=(0, 10))

        for s in self.schedule.get_free_slots(exp):
            slot_tree.insert("", "end", values=(s.date_time.strftime("%d.%m.%Y"), s.date_time.strftime("%H:%M")))

        tk.Label(right, text="Новый слот (ДД.ММ.ГГГГ ЧЧ:ММ):", font=("SF Pro Text", 11, "bold"), bg=COLORS["card"]).pack(
            anchor="w"
        )
        dt_var = tk.StringVar(value=datetime.now().strftime("%d.%m.%Y 18:00"))
        self._create_entry(right, dt_var, width=22).pack(anchor="w", pady=(4, 4))
        slot_err = tk.Label(right, text="", fg=COLORS["danger"], bg=COLORS["card"], font=("SF Pro Text", 10))
        slot_err.pack(anchor="w", pady=(0, 6))

        def on_open_slot() -> None:
            try:
                parsed = datetime.strptime(dt_var.get().strip(), "%d.%m.%Y %H:%M")
                if parsed < datetime.now():
                    msg = "Нельзя открыть слот в прошлом. Укажите будущую дату и время."
                    slot_err.config(text=msg)
                    self._show_invalid_input(msg)
                    return
                self.schedule.open_slot(exp, parsed)
                self.open_materials_and_schedule()
            except ValueError:
                msg = "Неверный формат даты. Используйте ДД.ММ.ГГГГ ЧЧ:ММ"
                slot_err.config(text=msg)
                self._show_invalid_input(msg)
            except PermissionError as e:
                slot_err.config(text=str(e))
                self._show_invalid_input(str(e))

        ModernButton(right, text="+ Открыть слот", command=on_open_slot, bg_color=self.BADGE_COLOR).pack(anchor="w")

        ModernButton(frame, text="← Назад в кабинет", command=self.open_cabinet, variant="secondary").pack(anchor="w")
        self.app.show_frame(frame)

    # EPublish: Публикация материала
    def open_publish_material(self) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Публикация материала", "Эксперт", self.BADGE_COLOR)

        card = self._create_card(frame, padx=26, pady=22)
        card.pack(fill="x")

        tk.Label(card, text="Тип материала *", font=("SF Pro Text", 12, "bold"), bg=COLORS["card"]).pack(anchor="w")
        type_var = tk.StringVar(value="Статья")
        radio_row = tk.Frame(card, bg=COLORS["card"])
        radio_row.pack(anchor="w", pady=(4, 12))
        tk.Radiobutton(radio_row, text="Статья", variable=type_var, value="Статья", bg=COLORS["card"]).pack(
            side="left", padx=(0, 14)
        )
        tk.Radiobutton(radio_row, text="Видео", variable=type_var, value="Видео", bg=COLORS["card"]).pack(side="left")

        tk.Label(card, text="Заголовок *", font=("SF Pro Text", 12, "bold"), bg=COLORS["card"]).pack(anchor="w")
        title_var = tk.StringVar()
        self._create_entry(card, title_var, width=54).pack(anchor="w", pady=(4, 12))

        tk.Label(card, text="Текст статьи / ссылка на видео *", font=("SF Pro Text", 12, "bold"), bg=COLORS["card"]).pack(
            anchor="w"
        )
        content_text = self._create_text(card, height=8, width=62)
        content_text.pack(anchor="w", pady=(4, 8))

        err_lbl = tk.Label(card, text="", fg=COLORS["danger"], bg=COLORS["card"], font=("SF Pro Text", 11))
        err_lbl.pack(anchor="w", pady=(0, 12))

        def on_publish() -> None:
            if not self.current_expert:
                return
            try:
                self.knowledge_base.publish_material(
                    expert=self.current_expert,
                    material_type=type_var.get(),
                    title=title_var.get(),
                    content=content_text.get("1.0", "end"),
                )
                self.open_materials_and_schedule()
            except (ValueError, PermissionError) as e:
                err_lbl.config(text=str(e))
                self._show_invalid_input(str(e))

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(anchor="w")
        ModernButton(btns, text="Опубликовать", command=on_publish, bg_color=self.BADGE_COLOR).pack(side="left", padx=(0, 10))
        ModernButton(btns, text="Отмена", command=self.open_materials_and_schedule, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # EList: Консультации эксперта
    def open_expert_consultations(self) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Консультации эксперта", "Эксперт", self.BADGE_COLOR)

        card = self._create_card(frame)
        card.pack(fill="both", expand=True)

        if not self.current_expert:
            return

        consultations = self.storage.find_consultations_by_expert(self.current_expert.id)
        if not consultations:
            tk.Label(card, text="Записей на ваши консультации пока нет.", fg=COLORS["muted"], bg=COLORS["card"]).pack(
                anchor="w", pady=(0, 10)
            )

        tree = ttk.Treeview(card, columns=("student", "date", "time", "status"), show="headings", height=9, style="Modern.Treeview")
        tree.heading("student", text="Ученик")
        tree.heading("date", text="Дата")
        tree.heading("time", text="Время")
        tree.heading("status", text="Статус")
        tree.column("student", width=260)
        tree.column("date", width=130, anchor="center")
        tree.column("time", width=110, anchor="center")
        tree.column("status", width=160, anchor="center")
        tree.pack(fill="both", expand=True, pady=(0, 14))

        cons_map: dict[str, Consultation] = {}
        for c in consultations:
            iid = str(c.id)
            cons_map[iid] = c
            st_name = c.student.name if c.student else "Ученик"
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    st_name,
                    c.date_time.strftime("%d.%m.%Y"),
                    c.date_time.strftime("%H:%M"),
                    STATUS_LABELS.get(c.status, c.status),
                ),
            )

        def on_open() -> None:
            sel = tree.selection()
            if not sel:
                self._show_invalid_input("Выберите консультацию из списка.")
                return
            self.selected_consultation = cons_map[sel[0]]
            self.open_selected_consultation(self.selected_consultation)

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(fill="x")
        ModernButton(btns, text="Открыть", command=on_open, bg_color=self.BADGE_COLOR).pack(side="left", padx=(0, 10))
        ModernButton(btns, text="← Назад", command=self.open_cabinet, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # EConsult: Выбранная консультация (эксперт)
    def open_selected_consultation(self, consultation: Consultation) -> None:
        assert self.app.root is not None
        fresh = self.storage.find_consultation(consultation.id) or consultation
        self.selected_consultation = fresh

        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Выбранная консультация", "Эксперт", self.BADGE_COLOR)

        card = self._create_card(frame, padx=24, pady=22)
        card.pack(fill="x", pady=(0, 16))

        st_name = fresh.student.name if fresh.student else "Ученик"
        tk.Label(
            card,
            text=f"Консультация с учеником: {st_name}",
            font=("SF Pro Display", 15, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(card, text=f"Дата и время: {fresh.date_time.strftime('%d.%m.%Y %H:%M')}", bg=COLORS["card"]).pack(anchor="w")
        tk.Label(
            card,
            text=f"Статус: {STATUS_LABELS.get(fresh.status, fresh.status)}",
            font=("SF Pro Text", 12, "bold"),
            fg=self.BADGE_COLOR,
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(4, 0))

        def on_complete() -> None:
            try:
                updated = self.schedule.complete_consultation(fresh.id)
                self.open_selected_consultation(updated)
            except ValueError as e:
                self._show_invalid_input(str(e))

        btns = tk.Frame(frame, bg=COLORS["bg"])
        btns.pack(anchor="w")
        complete_btn = ModernButton(btns, text="✓ Завершить консультацию", command=on_complete, variant="success")
        if fresh.status != "confirmed":
            complete_btn.config_state("disabled")
        complete_btn.pack(side="left", padx=(0, 10))
        ModernButton(btns, text="← К списку", command=self.open_expert_consultations, variant="secondary").pack(side="left")

        self.app.show_frame(frame)


class ModeratorUI(BaseUI):
    BADGE_COLOR = "#7C3AED"

    def __init__(
        self,
        app: Application,
        storage: Storage,
        profiles: ProfileModule,
        complaints: ComplaintModule,
    ):
        super().__init__(app, storage)
        self.profiles = profiles
        self.complaints = complaints

    # MForms: Анкеты на проверке
    def open_pending_forms(self) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Анкеты на проверке", "Модератор", self.BADGE_COLOR)

        card = self._create_card(frame)
        card.pack(fill="both", expand=True)

        forms = self.profiles.get_pending_forms()
        if not forms:
            tk.Label(card, text="Анкет на проверке нет.", fg=COLORS["muted"], bg=COLORS["card"]).pack(anchor="w", pady=(0, 8))

        tree = ttk.Treeview(card, columns=("expert", "specialization", "status"), show="headings", height=9, style="Modern.Treeview")
        tree.heading("expert", text="Эксперт")
        tree.heading("specialization", text="Специализация")
        tree.heading("status", text="Статус")
        tree.column("expert", width=250)
        tree.column("specialization", width=340)
        tree.column("status", width=160, anchor="center")
        tree.pack(fill="both", expand=True, pady=(0, 14))

        form_map: dict[str, ApplicationForm] = {}
        for f in forms:
            iid = str(f.id)
            form_map[iid] = f
            exp_name = f.expert.name if f.expert else "Эксперт"
            tree.insert("", "end", iid=iid, values=(exp_name, f.specialization, STATUS_LABELS.get(f.status, f.status)))

        def on_open_form() -> None:
            sel = tree.selection()
            if not sel:
                self._show_invalid_input("Выберите анкету из очереди.")
                return
            self.open_form_review(form_map[sel[0]])

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(fill="x")
        open_btn = ModernButton(btns, text="Открыть анкету", command=on_open_form, bg_color=self.BADGE_COLOR)
        if not forms:
            open_btn.config_state("disabled")
        open_btn.pack(side="left", padx=(0, 10))
        ModernButton(btns, text="Перейти к жалобам →", command=self.open_pending_complaints, variant="secondary").pack(
            side="left"
        )

        self.app.show_frame(frame)

    # MForm: Проверка анкеты
    def open_form_review(self, form: ApplicationForm) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Проверка анкеты", "Модератор", self.BADGE_COLOR)

        card = self._create_card(frame, padx=26, pady=22)
        card.pack(fill="x")

        exp_name = form.expert.name if form.expert else "Эксперт"
        tk.Label(card, text=f"Эксперт: {exp_name}", font=("SF Pro Display", 15, "bold"), bg=COLORS["card"]).pack(
            anchor="w", pady=(0, 6)
        )
        tk.Label(card, text=f"Специализация: {form.specialization}", font=("SF Pro Text", 12), bg=COLORS["card"]).pack(anchor="w")
        tk.Label(
            card,
            text=f"Квалификация: {form.qualification}",
            wraplength=680,
            justify="left",
            font=("SF Pro Text", 12),
            bg=COLORS["card"],
        ).pack(anchor="w", pady=(2, 14))

        tk.Label(
            card,
            text="Причина отклонения (обязательна при отклонении):",
            font=("SF Pro Text", 12, "bold"),
            bg=COLORS["card"],
        ).pack(anchor="w")
        reason_var = tk.StringVar()
        self._create_entry(card, reason_var, width=58).pack(anchor="w", pady=(4, 8))

        err_lbl = tk.Label(card, text="", fg=COLORS["danger"], bg=COLORS["card"], font=("SF Pro Text", 11))
        err_lbl.pack(anchor="w", pady=(0, 12))

        def on_verify() -> None:
            self.profiles.verify_expert(form)
            self.open_pending_forms()

        def on_reject() -> None:
            try:
                self.profiles.reject_application_form(form, reason_var.get())
                self.open_pending_forms()
            except ValueError as e:
                err_lbl.config(text=str(e))
                self._show_invalid_input(str(e))

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(anchor="w")
        ModernButton(btns, text="✓ Верифицировать", command=on_verify, variant="success").pack(side="left", padx=(0, 10))
        ModernButton(btns, text="✕ Отклонить анкету", command=on_reject, variant="danger").pack(side="left", padx=(0, 10))
        ModernButton(btns, text="Назад", command=self.open_pending_forms, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # MComplaints: Жалобы на рассмотрении
    def open_pending_complaints(self) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Жалобы на рассмотрении", "Модератор", self.BADGE_COLOR)

        card = self._create_card(frame)
        card.pack(fill="both", expand=True)

        complaints_list = self.complaints.get_pending_complaints()
        if not complaints_list:
            tk.Label(card, text="Жалоб на рассмотрении нет.", fg=COLORS["muted"], bg=COLORS["card"]).pack(anchor="w", pady=(0, 8))

        tree = ttk.Treeview(card, columns=("author", "expert", "target", "status"), show="headings", height=9, style="Modern.Treeview")
        tree.heading("author", text="Автор")
        tree.heading("expert", text="Эксперт")
        tree.heading("target", text="Объект")
        tree.heading("status", text="Статус")
        tree.column("author", width=170)
        tree.column("expert", width=190)
        tree.column("target", width=240)
        tree.column("status", width=150, anchor="center")
        tree.pack(fill="both", expand=True, pady=(0, 14))

        comp_map: dict[str, Complaint] = {}
        for c in complaints_list:
            iid = str(c.id)
            comp_map[iid] = c
            author_name = c.author.name if c.author else "Ученик"
            exp_name = c.expert.name if c.expert else "Эксперт"
            target = f"Материал «{c.material.title}»" if c.material else "Поведение эксперта"
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(author_name, exp_name, target, STATUS_LABELS.get(c.status, c.status)),
            )

        def on_open() -> None:
            sel = tree.selection()
            if not sel:
                self._show_invalid_input("Выберите жалобу из очереди.")
                return
            self.open_complaint_review(comp_map[sel[0]])

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(fill="x")
        open_btn = ModernButton(btns, text="Открыть жалобу", command=on_open, bg_color=self.BADGE_COLOR)
        if not complaints_list:
            open_btn.config_state("disabled")
        open_btn.pack(side="left", padx=(0, 10))
        ModernButton(btns, text="← Перейти к анкетам", command=self.open_pending_forms, variant="secondary").pack(side="left")

        self.app.show_frame(frame)

    # MComplaint: Рассмотрение жалобы
    def open_complaint_review(self, complaint: Complaint) -> None:
        assert self.app.root is not None
        frame = tk.Frame(self.app.root, bg=COLORS["bg"], padx=36, pady=24)
        self._build_header(frame, "Рассмотрение жалобы", "Модератор", self.BADGE_COLOR)

        card = self._create_card(frame, padx=26, pady=22)
        card.pack(fill="x")

        author_name = complaint.author.name if complaint.author else "Ученик"
        exp_name = complaint.expert.name if complaint.expert else "Эксперт"
        target = f"материал «{complaint.material.title}»" if complaint.material else "поведение эксперта"

        tk.Label(card, text=f"Автор: {author_name}   •   Эксперт: {exp_name}", font=("SF Pro Text", 12, "bold"), bg=COLORS["card"]).pack(
            anchor="w"
        )
        tk.Label(card, text=f"Объект: {target}", font=("SF Pro Text", 12), fg=COLORS["muted"], bg=COLORS["card"]).pack(
            anchor="w", pady=(2, 10)
        )
        tk.Label(card, text="Причина жалобы:", font=("SF Pro Text", 12, "bold"), bg=COLORS["card"]).pack(anchor="w")
        tk.Label(card, text=complaint.reason, wraplength=680, justify="left", bg=COLORS["card"]).pack(anchor="w", pady=(2, 14))

        tk.Label(card, text="Решение и пояснение *", font=("SF Pro Text", 12, "bold"), bg=COLORS["card"]).pack(anchor="w")
        decision_text = self._create_text(card, height=4, width=62)
        decision_text.pack(anchor="w", pady=(4, 8))

        err_lbl = tk.Label(card, text="", fg=COLORS["danger"], bg=COLORS["card"], font=("SF Pro Text", 11))
        err_lbl.pack(anchor="w", pady=(0, 12))

        def on_reject() -> None:
            try:
                self.complaints.reject_complaint(complaint, decision_text.get("1.0", "end"))
                self.open_pending_complaints()
            except ValueError as e:
                err_lbl.config(text=str(e))
                self._show_invalid_input(str(e))

        def on_block() -> None:
            try:
                self.complaints.block_expert(complaint, decision_text.get("1.0", "end"))
                self.open_pending_complaints()
            except ValueError as e:
                err_lbl.config(text=str(e))
                self._show_invalid_input(str(e))

        btns = tk.Frame(card, bg=COLORS["card"])
        btns.pack(anchor="w")
        ModernButton(btns, text="Отклонить жалобу", command=on_reject, variant="secondary").pack(side="left", padx=(0, 10))
        ModernButton(btns, text="Заблокировать эксперта", command=on_block, variant="danger").pack(side="left", padx=(0, 10))
        ModernButton(btns, text="Назад", command=self.open_pending_complaints, variant="secondary").pack(side="left")

        self.app.show_frame(frame)