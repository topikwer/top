from datetime import date, datetime
from typing import Optional

from models import (
    ApplicationForm,
    Complaint,
    Consultation,
    Expert,
    Material,
    Payment,
    Review,
    Slot,
    Student,
)
from storage import Storage


class ProfileModule:
    def __init__(self, storage: Storage):
        self.storage: Storage = storage

    def register_student(self, name: str, email: str) -> Student:
        name = name.strip()
        email = email.strip()
        if not name:
            raise ValueError("Имя ученика не может быть пустым.")
        if not email or "@" not in email or "." not in email:
            raise ValueError("Введите корректный email.")
        student = Student(id=0, name=name, email=email)
        return self.storage.save_student(student)

    def register_expert(self, name: str) -> Expert:
        name = name.strip()
        if not name:
            raise ValueError("Имя эксперта не может быть пустым.")
        expert = Expert(
            id=0,
            name=name,
            specialization="не указана",
            qualification="не указана",
            rating=0.0,
            verification_status="not_submitted",
        )
        return self.storage.save_expert(expert)

    def fill_application_form(
        self,
        expert: Expert,
        specialization: str,
        qualification: str,
    ) -> ApplicationForm:
        specialization = specialization.strip()
        qualification = qualification.strip()
        if not specialization or not qualification:
            raise ValueError("Специализация и квалификация обязательны для заполнения.")
        expert.specialization = specialization
        expert.qualification = qualification
        expert.verification_status = "pending"
        self.storage.save_expert(expert)

        form = ApplicationForm(
            id=0,
            specialization=specialization,
            qualification=qualification,
            status="pending",
            expert=expert,
        )
        return self.storage.save_application_form(form)

    def find_experts(self, topic: str) -> list[Expert]:
        return self.storage.find_verified_experts(topic)

    def get_profile(self, expert_id: int) -> Optional[Expert]:
        return self.storage.find_expert(expert_id)

    def get_pending_forms(self) -> list[ApplicationForm]:
        return self.storage.find_application_forms_by_status("pending")

    def verify_expert(self, form: ApplicationForm) -> None:
        moderator = self.storage.get_moderator()
        form.status = "verified"
        form.rejection_reason = None
        form.moderator = moderator
        self.storage.save_application_form(form)

        if form.expert:
            form.expert.verification_status = "verified"
            form.expert.specialization = form.specialization
            form.expert.qualification = form.qualification
            self.storage.save_expert(form.expert)

    def reject_application_form(self, form: ApplicationForm, reason: str) -> None:
        reason = reason.strip()
        if not reason:
            raise ValueError("Укажите причину отклонения анкеты.")
        moderator = self.storage.get_moderator()
        form.status = "rejected"
        form.rejection_reason = reason
        form.moderator = moderator
        self.storage.save_application_form(form)

        if form.expert:
            form.expert.verification_status = "rejected"
            self.storage.save_expert(form.expert)

    def update_rating(self, expert: Expert, rating: float) -> None:
        expert.rating = round(rating, 2)
        self.storage.save_expert(expert)

    def block_expert(self, expert: Expert) -> None:
        expert.verification_status = "blocked"
        self.storage.save_expert(expert)


class KnowledgeBaseModule:
    def __init__(self, storage: Storage, profiles: ProfileModule):
        self.storage: Storage = storage
        self.profiles: ProfileModule = profiles

    def get_expert_materials(self, expert_id: int) -> list[Material]:
        return self.storage.find_materials_by_expert(expert_id)

    def open_material(self, student: Optional[Student], material_id: int) -> Optional[Material]:
        return self.storage.find_material(material_id)

    def publish_material(
        self,
        expert: Expert,
        material_type: str,
        title: str,
        content: str = "",
    ) -> Material:
        if expert.verification_status != "verified":
            raise PermissionError("Публикация доступна только верифицированным и незаблокированным экспертам.")
        title = title.strip()
        content = content.strip()
        if not title or not content:
            raise ValueError("Заполните заголовок и содержимое материала.")

        material = Material(
            id=0,
            type=material_type,
            title=title,
            publication_date=date.today(),
            content=content,
            author=expert,
        )
        return self.storage.save_material(material)


class ScheduleAndConsultationsModule:
    def __init__(self, storage: Storage, profiles: ProfileModule):
        self.storage: Storage = storage
        self.profiles: ProfileModule = profiles
        self._pending_invoices: dict[int, tuple[Student, Slot]] = {}

    def get_free_slots(self, expert: Expert) -> list[Slot]:
        return self.storage.find_free_slots(expert.id)

    def open_slot(self, expert: Expert, date_time: datetime) -> Slot:
        if expert.verification_status != "verified":
            raise PermissionError("Открытие слотов доступно только верифицированным экспертам.")
        slot = Slot(
            id=0,
            date_time=date_time,
            status="free",
            expert=expert,
        )
        return self.storage.save_slot(slot)

    def check_slot(self, slot: Optional[Slot]) -> bool:
        if slot is None:
            return False
        current = self.storage.find_slot(slot.id)
        return current is not None and current.status == "free"

    def create_invoice(self, student: Student, slot: Slot) -> Payment:
        invoice = Payment(
            id=0,
            amount=2500.0,
            status="pending",
            student=student,
            slot=slot,
        )
        invoice = self.storage.save_payment(invoice)
        self._pending_invoices[invoice.id] = (student, slot)
        return invoice

    def book_consultation(self, student: Student, slot_id: int) -> Optional[Payment]:
        slot = self.storage.find_slot(slot_id)
        if not self.check_slot(slot):
            return None
        return self.create_invoice(student, slot)

    def confirm_booking(self, invoice: Payment) -> Consultation:
        student = invoice.student
        slot = invoice.slot
        if (not student or not slot) and invoice.id in self._pending_invoices:
            student, slot = self._pending_invoices[invoice.id]
        if not student or not slot:
            raise ValueError("Не найдены данные ученика или слота для счёта.")
        if not self.check_slot(slot):
            raise ValueError("Это время уже занято. Выберите другой слот.")

        consultation = self.storage.occupy_slot_and_save_consultation(slot, student, invoice)
        self._pending_invoices.pop(invoice.id, None)
        return consultation

    def complete_consultation(self, consultation_id: int) -> Consultation:
        consultation = self.storage.find_consultation(consultation_id)
        if not consultation:
            raise ValueError("Консультация не найдена.")
        if consultation.status != "confirmed":
            raise ValueError("Завершить можно только подтверждённую консультацию.")
        consultation.status = "completed"
        return self.storage.save_consultation(consultation)


class PaymentModule:
    def __init__(
        self,
        storage: Storage,
        schedule: ScheduleAndConsultationsModule,
        payment_gateway_url: str = "https://pay.sandbox.local/api",
    ):
        self.storage: Storage = storage
        self.schedule: ScheduleAndConsultationsModule = schedule
        self.payment_gateway_url: str = payment_gateway_url

    def pay_consultation(self, invoice: Payment, payment_details: str) -> bool:
        payment_details = payment_details.strip()
        if not payment_details or len(payment_details) < 4:
            raise ValueError("Введите корректные платёжные реквизиты (минимум 4 символа).")
        if (
                "ошибка" in payment_details.lower()
                or "fail" in payment_details.lower()
                or payment_details == "0000"
        ):
            self.storage.save_payment_status(invoice, "declined")
            return False

        self.storage.save_payment_status(invoice, "paid")
        self.schedule.confirm_booking(invoice)
        return True


class ReviewModule:
    def __init__(self, storage: Storage, profiles: ProfileModule):
        self.storage: Storage = storage
        self.profiles: ProfileModule = profiles

    def recalculate_rating(self, expert: Expert) -> float:
        reviews = self.storage.find_reviews(expert)
        if not reviews:
            return 0.0
        avg = sum(r.rating for r in reviews) / len(reviews)
        self.profiles.update_rating(expert, avg)
        return round(avg, 2)

    def leave_review(
        self,
        student: Student,
        consultation_id: int,
        rating: int,
        comment: Optional[str] = None,
    ) -> Review:
        if rating not in (1, 2, 3, 4, 5):
            raise ValueError("Выберите допустимую оценку от 1 до 5.")
        consultation = self.storage.find_consultation(consultation_id)
        if not consultation:
            raise ValueError("Консультация не найдена.")
        if consultation.status != "completed":
            raise ValueError("Оставить отзыв можно только после завершения консультации.")
        if self.storage.find_review_by_consultation(consultation_id) is not None:
            raise ValueError("Отзыв на эту консультацию уже оставлен.")

        review = Review(
            id=0,
            rating=rating,
            comment=comment.strip() if comment else None,
            consultation=consultation,
            author=student,
        )
        review = self.storage.save_review(review)

        if consultation.expert:
            self.recalculate_rating(consultation.expert)
        return review


class ComplaintModule:
    def __init__(self, storage: Storage, profiles: ProfileModule):
        self.storage: Storage = storage
        self.profiles: ProfileModule = profiles

    def submit_complaint(
        self,
        student: Student,
        expert_id: int,
        material_id: Optional[int],
        reason: str,
    ) -> Complaint:
        reason = reason.strip()
        if not reason:
            raise ValueError("Укажите причину жалобы.")
        expert = self.storage.find_expert(expert_id)
        if not expert:
            raise ValueError("Эксперт не найден.")
        material = self.storage.find_material(material_id) if material_id else None

        complaint = Complaint(
            id=0,
            reason=reason,
            status="pending",
            author=student,
            expert=expert,
            material=material,
        )
        return self.storage.save_complaint(complaint)

    def get_pending_complaints(self) -> list[Complaint]:
        return self.storage.find_complaints_by_status("pending")

    def reject_complaint(self, complaint: Complaint, decision: str) -> None:
        decision = decision.strip()
        if not decision:
            raise ValueError("Укажите обоснование принятого решения.")
        moderator = self.storage.get_moderator()
        complaint.status = "rejected"
        complaint.decision = decision
        complaint.moderator = moderator
        self.storage.save_complaint(complaint)

    def block_expert(self, complaint: Complaint, decision: str) -> None:
        decision = decision.strip()
        if not decision:
            raise ValueError("Укажите обоснование принятого решения.")
        moderator = self.storage.get_moderator()
        complaint.status = "resolved"
        complaint.decision = decision
        complaint.moderator = moderator
        self.storage.save_complaint(complaint)

        if complaint.expert:
            self.profiles.block_expert(complaint.expert)