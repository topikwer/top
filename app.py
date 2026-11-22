import tkinter as tk
from datetime import date, datetime, timedelta

from models import ApplicationForm, Expert, Material, Slot, Student
from modules import (
    ComplaintModule,
    KnowledgeBaseModule,
    PaymentModule,
    ProfileModule,
    ReviewModule,
    ScheduleAndConsultationsModule,
)
from storage import Storage
from ui import COLORS, ModernButton, ExpertUI, ModeratorUI, StudentUI


class Application:
    def __init__(self):
        self.root: tk.Tk | None = None
        self.current_frame: tk.Frame | None = None

        self.storage: Storage | None = None
        self.profiles: ProfileModule | None = None
        self.knowledge_base: KnowledgeBaseModule | None = None
        self.schedule: ScheduleAndConsultationsModule | None = None
        self.payment: PaymentModule | None = None
        self.reviews: ReviewModule | None = None
        self.complaints: ComplaintModule | None = None

        self.student_ui: StudentUI | None = None
        self.expert_ui: ExpertUI | None = None
        self.moderator_ui: ModeratorUI | None = None

    def assemble_components(self) -> None:
        self.storage = Storage("platform.db")
        self._seed_initial_data_if_empty()

        self.profiles = ProfileModule(self.storage)
        self.knowledge_base = KnowledgeBaseModule(self.storage, self.profiles)
        self.schedule = ScheduleAndConsultationsModule(self.storage, self.profiles)
        self.payment = PaymentModule(self.storage, self.schedule)
        self.reviews = ReviewModule(self.storage, self.profiles)
        self.complaints = ComplaintModule(self.storage, self.profiles)

        self.student_ui = StudentUI(
            app=self,
            storage=self.storage,
            profiles=self.profiles,
            knowledge_base=self.knowledge_base,
            schedule=self.schedule,
            payment=self.payment,
            reviews=self.reviews,
            complaints=self.complaints,
        )
        self.expert_ui = ExpertUI(
            app=self,
            storage=self.storage,
            profiles=self.profiles,
            knowledge_base=self.knowledge_base,
            schedule=self.schedule,
        )
        self.moderator_ui = ModeratorUI(
            app=self,
            storage=self.storage,
            profiles=self.profiles,
            complaints=self.complaints,
        )

    def _seed_initial_data_if_empty(self) -> None:
        assert self.storage is not None
        if self.storage.get_latest_expert() is not None:
            return

        expert1 = self.storage.save_expert(
            Expert(
                id=0,
                name="Алексей Петров",
                specialization="Python и backend",
                qualification="Senior Python разработчик, 7 лет опыта",
                rating=4.8,
                verification_status="verified",
            )
        )
        expert2 = self.storage.save_expert(
            Expert(
                id=0,
                name="Мария Смирнова",
                specialization="Базы данных и SQL",
                qualification="Архитектор БД, PostgreSQL / SQLite",
                rating=4.6,
                verification_status="verified",
            )
        )
        expert3 = self.storage.save_expert(
            Expert(
                id=0,
                name="Дмитрий Орлов",
                specialization="Разработка API",
                qualification="Tech Lead, FastAPI и микросервисы",
                rating=4.7,
                verification_status="pending",
            )
        )

        self.storage.save_application_form(
            ApplicationForm(
                id=0,
                specialization="Разработка API",
                qualification="Tech Lead, FastAPI и микросервисы",
                status="pending",
                expert=expert3,
            )
        )

        self.storage.save_material(
            Material(
                id=0,
                type="Статья",
                title="Основы Python",
                publication_date=date.today(),
                content="Подробное руководство по архитектуре приложений на Python, типизации и работе с SQLite.\n\n"
                        "1. Разделяйте слои данных (models), хранения (storage) и бизнес-логики (modules).\n"
                        "2. Используйте внедрение зависимостей для удобного тестирования.",
                author=expert1,
            )
        )
        self.storage.save_material(
            Material(
                id=0,
                type="Видео",
                title="Разработка REST API с нуля",
                publication_date=date.today(),
                content="https://video.platform.local/watch/rest-api-guide",
                author=expert1,
            )
        )

        tomorrow = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=1)
        day_after = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=2)
        self.storage.save_slot(Slot(id=0, date_time=tomorrow, status="free", expert=expert1))
        self.storage.save_slot(Slot(id=0, date_time=day_after, status="free", expert=expert1))
        self.storage.save_slot(Slot(id=0, date_time=tomorrow, status="free", expert=expert2))

        self.storage.save_student(Student(id=0, name="Анна Иванова", email="anna@example.com"))

    def show_frame(self, new_frame: tk.Frame) -> None:
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = new_frame
        self.current_frame.pack(fill="both", expand=True)
        self._animate_accent_bar(new_frame)

    def _animate_accent_bar(self, parent: tk.Frame) -> None:
        assert self.root is not None
        bar = tk.Frame(parent, bg=COLORS["primary"], height=3)
        bar.place(x=0, y=0, width=1)
        target_w = max(self.root.winfo_width(), 1020)

        def step(current_w: int) -> None:
            if not bar.winfo_exists():
                return
            next_w = min(target_w, current_w + int(target_w / 10))
            bar.place(x=0, y=0, width=next_w)
            if next_w < target_w:
                self.root.after(14, lambda: step(next_w))

        self.root.after(10, lambda: step(40))

    def open_role_selection(self) -> None:
        assert self.root is not None
        frame = tk.Frame(self.root, bg=COLORS["bg"], padx=36, pady=28)

        # Top navigation bar
        nav = tk.Frame(frame, bg=COLORS["bg"])
        nav.pack(fill="x", pady=(0, 22))
        tk.Label(
            nav,
            text="KNOWLEDGE HUB",
            font=("SF Pro Display", 12, "bold"),
            fg=COLORS["primary"],
            bg=COLORS["bg"],
        ).pack(side="left")

        ModernButton(
            nav,
            text="Закрыть приложение",
            command=self.root.destroy,
            variant="danger",
            padx=14,
            pady=6,
        ).pack(side="right")

        # Hero banner
        hero = tk.Frame(
            frame,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            padx=28,
            pady=24,
        )
        hero.pack(fill="x", pady=(0, 24))
        tk.Label(
            hero,
            text="Платформа обмена знаниями и опытом",
            font=("SF Pro Display", 22, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
        ).pack(anchor="w")
        tk.Label(
            hero,
            text="Находите проверенных наставников, изучайте материалы и проводите персональные консультации.\nВыберите рабочий раздел для начала работы:",
            font=("SF Pro Text", 13),
            fg=COLORS["muted"],
            bg=COLORS["card"],
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        # Role cards
        cards = tk.Frame(frame, bg=COLORS["bg"])
        cards.pack(fill="both", expand=True)

        roles = [
            (
                "🎓  Ученик",
                "Поиск и обучение",
                "Ищите верифицированных экспертов, читайте бесплатные статьи, записывайтесь на слоты и оставляйте отзывы.",
                "student",
                COLORS["primary"],
            ),
            (
                "💼  Эксперт",
                "Наставничество и контент",
                "Заполните анкету для верификации, публикуйте статьи и видео, открывайте слоты расписания и проводите встречи.",
                "expert",
                "#0D9488",
            ),
            (
                "🛡️  Модератор",
                "Контроль качества",
                "Проверяйте анкеты новых экспертов, верифицируйте специалистов и рассматривайте обращения пользователей.",
                "moderator",
                "#7C3AED",
            ),
        ]

        for idx, (title, subtitle, desc, role_code, accent_color) in enumerate(roles):
            card = tk.Frame(
                cards,
                bg=COLORS["card"],
                highlightbackground=COLORS["border"],
                highlightthickness=1,
            )
            card.grid(row=0, column=idx, sticky="nsew", padx=10)
            cards.columnconfigure(idx, weight=1)
            cards.rowconfigure(0, weight=1)

            # Colored top strip
            tk.Frame(card, bg=accent_color, height=5).pack(fill="x")

            inner = tk.Frame(card, bg=COLORS["card"], padx=22, pady=20)
            inner.pack(fill="both", expand=True)

            tk.Label(
                inner,
                text=subtitle.upper(),
                font=("SF Pro Text", 10, "bold"),
                fg=accent_color,
                bg=COLORS["card"],
            ).pack(anchor="w")

            tk.Label(
                inner,
                text=title,
                font=("SF Pro Display", 17, "bold"),
                fg=COLORS["text"],
                bg=COLORS["card"],
            ).pack(anchor="w", pady=(4, 10))

            tk.Label(
                inner,
                text=desc,
                font=("SF Pro Text", 12),
                fg=COLORS["muted"],
                bg=COLORS["card"],
                justify="left",
                wraplength=245,
            ).pack(anchor="w", pady=(0, 20))

            btn_wrap = tk.Frame(inner, bg=COLORS["card"])
            btn_wrap.pack(side="bottom", fill="x")
            ModernButton(
                btn_wrap,
                text="Открыть раздел  →",
                command=lambda r=role_code: self.open_interface(r),
                bg_color=accent_color,
                padx=16,
                pady=9,
            ).pack(anchor="w")

        self.show_frame(frame)

    def open_interface(self, role: str) -> None:
        role = role.lower()
        if role == "student" and self.student_ui:
            self.student_ui.open_start()
        elif role == "expert" and self.expert_ui:
            self.expert_ui.open_start()
        elif role == "moderator" and self.moderator_ui:
            self.moderator_ui.open_pending_forms()

    def main(self) -> None:
        self.assemble_components()
        self.root = tk.Tk()
        self.root.title("Платформа обмена знаниями и опытом")
        self.root.geometry("1040x700")
        self.root.minsize(920, 620)
        self.root.configure(bg=COLORS["bg"])
        self.open_role_selection()
        self.root.mainloop()


if __name__ == "__main__":
    Application().main()