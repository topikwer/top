import sqlite3
from datetime import date, datetime
from typing import Optional

from models import (
    ApplicationForm,
    Complaint,
    Consultation,
    Expert,
    Material,
    Moderator,
    Payment,
    Review,
    Slot,
    Student,
)


class Storage:
    def __init__(self, db_path: str = "platform.db"):
        self.db_path: str = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS experts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    specialization TEXT NOT NULL,
                    qualification TEXT NOT NULL,
                    rating REAL NOT NULL DEFAULT 0.0,
                    verification_status TEXT NOT NULL DEFAULT 'not_submitted'
                );

                CREATE TABLE IF NOT EXISTS moderators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS application_forms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expert_id INTEGER NOT NULL,
                    moderator_id INTEGER,
                    specialization TEXT NOT NULL,
                    qualification TEXT NOT NULL,
                    status TEXT NOT NULL,
                    rejection_reason TEXT,
                    FOREIGN KEY (expert_id) REFERENCES experts(id),
                    FOREIGN KEY (moderator_id) REFERENCES moderators(id)
                );

                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expert_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    publication_date TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (expert_id) REFERENCES experts(id)
                );

                CREATE TABLE IF NOT EXISTS slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expert_id INTEGER NOT NULL,
                    date_time TEXT NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY (expert_id) REFERENCES experts(id)
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    slot_id INTEGER,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES students(id),
                    FOREIGN KEY (slot_id) REFERENCES slots(id)
                );

                CREATE TABLE IF NOT EXISTS consultations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expert_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    slot_id INTEGER NOT NULL UNIQUE,
                    payment_id INTEGER UNIQUE,
                    date_time TEXT NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY (expert_id) REFERENCES experts(id),
                    FOREIGN KEY (student_id) REFERENCES students(id),
                    FOREIGN KEY (slot_id) REFERENCES slots(id),
                    FOREIGN KEY (payment_id) REFERENCES payments(id)
                );

                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consultation_id INTEGER NOT NULL UNIQUE,
                    student_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    FOREIGN KEY (consultation_id) REFERENCES consultations(id),
                    FOREIGN KEY (student_id) REFERENCES students(id)
                );

                CREATE TABLE IF NOT EXISTS complaints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    expert_id INTEGER NOT NULL,
                    material_id INTEGER,
                    moderator_id INTEGER,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    decision TEXT,
                    FOREIGN KEY (student_id) REFERENCES students(id),
                    FOREIGN KEY (expert_id) REFERENCES experts(id),
                    FOREIGN KEY (material_id) REFERENCES materials(id),
                    FOREIGN KEY (moderator_id) REFERENCES moderators(id)
                );
                """
            )
            cur = conn.execute("SELECT COUNT(*) FROM moderators")
            if cur.fetchone()[0] == 0:
                conn.execute("INSERT INTO moderators (name) VALUES (?)", ("Модератор платформы",))

    # --- Students ---
    def save_student(self, student: Student) -> Student:
        with self._connect() as conn:
            if student.id:
                conn.execute(
                    "UPDATE students SET name = ?, email = ? WHERE id = ?",
                    (student.name, student.email, student.id),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO students (name, email) VALUES (?, ?)",
                    (student.name, student.email),
                )
                student.id = cur.lastrowid
        return student

    def get_latest_student(self) -> Optional[Student]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM students ORDER BY id DESC LIMIT 1").fetchone()
            return Student(id=row["id"], name=row["name"], email=row["email"]) if row else None

    def find_student(self, student_id: int) -> Optional[Student]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
            return Student(id=row["id"], name=row["name"], email=row["email"]) if row else None

    # --- Experts ---
    def save_expert(self, expert: Expert) -> Expert:
        with self._connect() as conn:
            if expert.id:
                conn.execute(
                    """
                    UPDATE experts
                    SET name = ?, specialization = ?, qualification = ?, rating = ?, verification_status = ?
                    WHERE id = ?
                    """,
                    (
                        expert.name,
                        expert.specialization,
                        expert.qualification,
                        expert.rating,
                        expert.verification_status,
                        expert.id,
                    ),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO experts (name, specialization, qualification, rating, verification_status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        expert.name,
                        expert.specialization,
                        expert.qualification,
                        expert.rating,
                        expert.verification_status,
                    ),
                )
                expert.id = cur.lastrowid
        return expert

    def get_latest_expert(self) -> Optional[Expert]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM experts ORDER BY id DESC LIMIT 1").fetchone()
            return self._row_to_expert(row) if row else None

    def find_expert(self, expert_id: int) -> Optional[Expert]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM experts WHERE id = ?", (expert_id,)).fetchone()
            return self._row_to_expert(row) if row else None

    def find_verified_experts(self, topic: str) -> list[Expert]:
        pattern = f"%{topic.strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM experts
                WHERE verification_status = 'verified'
                  AND (specialization LIKE ? OR name LIKE ? OR qualification LIKE ?)
                ORDER BY rating DESC
                """,
                (pattern, pattern, pattern),
            ).fetchall()
            return [self._row_to_expert(r) for r in rows]

    def _row_to_expert(self, row: sqlite3.Row) -> Expert:
        return Expert(
            id=row["id"],
            name=row["name"],
            specialization=row["specialization"],
            qualification=row["qualification"],
            rating=row["rating"],
            verification_status=row["verification_status"],
        )

    # --- Moderators ---
    def get_moderator(self) -> Moderator:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM moderators LIMIT 1").fetchone()
            return Moderator(id=row["id"], name=row["name"])

    # --- Application Forms ---
    def save_application_form(self, form: ApplicationForm) -> ApplicationForm:
        expert_id = form.expert.id if form.expert else None
        moderator_id = form.moderator.id if form.moderator else None
        with self._connect() as conn:
            if form.id:
                conn.execute(
                    """
                    UPDATE application_forms
                    SET expert_id = ?, moderator_id = ?, specialization = ?,
                        qualification = ?, status = ?, rejection_reason = ?
                    WHERE id = ?
                    """,
                    (
                        expert_id,
                        moderator_id,
                        form.specialization,
                        form.qualification,
                        form.status,
                        form.rejection_reason,
                        form.id,
                    ),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO application_forms (expert_id, moderator_id, specialization, qualification, status, rejection_reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        expert_id,
                        moderator_id,
                        form.specialization,
                        form.qualification,
                        form.status,
                        form.rejection_reason,
                    ),
                )
                form.id = cur.lastrowid
        return form

    def find_application_form(self, form_id: int) -> Optional[ApplicationForm]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM application_forms WHERE id = ?", (form_id,)).fetchone()
            return self._row_to_form(row) if row else None

    def find_expert_application_form(self, expert_id: int) -> Optional[ApplicationForm]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM application_forms WHERE expert_id = ? ORDER BY id DESC LIMIT 1",
                (expert_id,),
            ).fetchone()
            return self._row_to_form(row) if row else None

    def find_application_forms_by_status(self, status: str) -> list[ApplicationForm]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM application_forms WHERE status = ? ORDER BY id ASC",
                (status,),
            ).fetchall()
            return [self._row_to_form(r) for r in rows]

    def _row_to_form(self, row: sqlite3.Row) -> ApplicationForm:
        expert = self.find_expert(row["expert_id"]) if row["expert_id"] else None
        return ApplicationForm(
            id=row["id"],
            specialization=row["specialization"],
            qualification=row["qualification"],
            status=row["status"],
            expert=expert,
            rejection_reason=row["rejection_reason"],
        )

    # --- Materials ---
    def save_material(self, material: Material) -> Material:
        expert_id = material.author.id if material.author else None
        pub_date_str = material.publication_date.isoformat()
        with self._connect() as conn:
            if material.id:
                conn.execute(
                    """
                    UPDATE materials
                    SET expert_id = ?, type = ?, title = ?, publication_date = ?, content = ?
                    WHERE id = ?
                    """,
                    (
                        expert_id,
                        material.type,
                        material.title,
                        pub_date_str,
                        material.content,
                        material.id,
                    ),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO materials (expert_id, type, title, publication_date, content)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        expert_id,
                        material.type,
                        material.title,
                        pub_date_str,
                        material.content,
                    ),
                )
                material.id = cur.lastrowid
        return material

    def find_materials_by_expert(self, expert_id: int) -> list[Material]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM materials WHERE expert_id = ? ORDER BY id DESC",
                (expert_id,),
            ).fetchall()
            return [self._row_to_material(r) for r in rows]

    def find_material(self, material_id: int) -> Optional[Material]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
            return self._row_to_material(row) if row else None

    def _row_to_material(self, row: sqlite3.Row) -> Material:
        author = self.find_expert(row["expert_id"]) if row["expert_id"] else None
        return Material(
            id=row["id"],
            type=row["type"],
            title=row["title"],
            publication_date=date.fromisoformat(row["publication_date"]),
            content=row["content"],
            author=author,
        )

    # --- Slots ---
    def save_slot(self, slot: Slot) -> Slot:
        expert_id = slot.expert.id if slot.expert else None
        dt_str = slot.date_time.isoformat()
        with self._connect() as conn:
            if slot.id:
                conn.execute(
                    "UPDATE slots SET expert_id = ?, date_time = ?, status = ? WHERE id = ?",
                    (expert_id, dt_str, slot.status, slot.id),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO slots (expert_id, date_time, status) VALUES (?, ?, ?)",
                    (expert_id, dt_str, slot.status),
                )
                slot.id = cur.lastrowid
        return slot

    def find_free_slots(self, expert_id: int) -> list[Slot]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM slots WHERE expert_id = ? AND status = 'free' ORDER BY date_time ASC",
                (expert_id,),
            ).fetchall()
            return [self._row_to_slot(r) for r in rows]

    def find_slot(self, slot_id: int) -> Optional[Slot]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM slots WHERE id = ?", (slot_id,)).fetchone()
            return self._row_to_slot(row) if row else None

    def _row_to_slot(self, row: sqlite3.Row) -> Slot:
        expert = self.find_expert(row["expert_id"]) if row["expert_id"] else None
        return Slot(
            id=row["id"],
            date_time=datetime.fromisoformat(row["date_time"]),
            status=row["status"],
            expert=expert,
        )

    # --- Payments & Consultations ---
    def save_payment(self, payment: Payment) -> Payment:
        student_id = payment.student.id if payment.student else None
        slot_id = payment.slot.id if payment.slot else None
        with self._connect() as conn:
            if payment.id:
                conn.execute(
                    "UPDATE payments SET student_id = ?, slot_id = ?, amount = ?, status = ? WHERE id = ?",
                    (student_id, slot_id, payment.amount, payment.status, payment.id),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO payments (student_id, slot_id, amount, status) VALUES (?, ?, ?, ?)",
                    (student_id, slot_id, payment.amount, payment.status),
                )
                payment.id = cur.lastrowid
        return payment

    def save_payment_status(self, payment: Payment, status: str) -> None:
        payment.status = status
        with self._connect() as conn:
            conn.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment.id))

    def occupy_slot_and_save_consultation(
        self,
        slot: Slot,
        student: Student,
        payment: Optional[Payment] = None,
    ) -> Consultation:
        with self._connect() as conn:
            slot.status = "occupied"
            conn.execute("UPDATE slots SET status = 'occupied' WHERE id = ?", (slot.id,))
            expert_id = slot.expert.id if slot.expert else None
            payment_id = payment.id if payment else None
            dt_str = slot.date_time.isoformat()
            cur = conn.execute(
                """
                INSERT INTO consultations (expert_id, student_id, slot_id, payment_id, date_time, status)
                VALUES (?, ?, ?, ?, ?, 'confirmed')
                """,
                (expert_id, student.id, slot.id, payment_id, dt_str),
            )
            consultation_id = cur.lastrowid
        return Consultation(
            id=consultation_id,
            date_time=slot.date_time,
            status="confirmed",
            expert=slot.expert,
            student=student,
            slot=slot,
            payment=payment,
        )

    def find_consultation(self, consultation_id: int) -> Optional[Consultation]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM consultations WHERE id = ?", (consultation_id,)).fetchone()
            return self._row_to_consultation(row) if row else None

    def find_consultations_by_student(self, student_id: int) -> list[Consultation]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM consultations WHERE student_id = ? ORDER BY date_time DESC",
                (student_id,),
            ).fetchall()
            return [self._row_to_consultation(r) for r in rows]

    def find_consultations_by_expert(self, expert_id: int) -> list[Consultation]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM consultations WHERE expert_id = ? ORDER BY date_time DESC",
                (expert_id,),
            ).fetchall()
            return [self._row_to_consultation(r) for r in rows]

    def save_consultation(self, consultation: Consultation) -> Consultation:
        with self._connect() as conn:
            conn.execute(
                "UPDATE consultations SET status = ? WHERE id = ?",
                (consultation.status, consultation.id),
            )
        return consultation

    def _row_to_consultation(self, row: sqlite3.Row) -> Consultation:
        expert = self.find_expert(row["expert_id"]) if row["expert_id"] else None
        student = self.find_student(row["student_id"]) if row["student_id"] else None
        slot = self.find_slot(row["slot_id"]) if row["slot_id"] else None
        return Consultation(
            id=row["id"],
            date_time=datetime.fromisoformat(row["date_time"]),
            status=row["status"],
            expert=expert,
            student=student,
            slot=slot,
        )

    # --- Reviews ---
    def save_review(self, review: Review) -> Review:
        consultation_id = review.consultation.id if review.consultation else None
        student_id = review.author.id if review.author else None
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO reviews (consultation_id, student_id, rating, comment)
                VALUES (?, ?, ?, ?)
                """,
                (consultation_id, student_id, review.rating, review.comment),
            )
            review.id = cur.lastrowid
        return review

    def find_review_by_consultation(self, consultation_id: int) -> Optional[Review]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM reviews WHERE consultation_id = ?",
                (consultation_id,),
            ).fetchone()
            if not row:
                return None
            return Review(
                id=row["id"],
                rating=row["rating"],
                comment=row["comment"],
            )

    def find_reviews(self, expert: Expert) -> list[Review]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.* FROM reviews r
                JOIN consultations c ON r.consultation_id = c.id
                WHERE c.expert_id = ?
                """,
                (expert.id,),
            ).fetchall()
            return [
                Review(id=r["id"], rating=r["rating"], comment=r["comment"])
                for r in rows
            ]

    # --- Complaints ---
    def save_complaint(self, complaint: Complaint) -> Complaint:
        student_id = complaint.author.id if complaint.author else None
        expert_id = complaint.expert.id if complaint.expert else None
        material_id = complaint.material.id if complaint.material else None
        moderator_id = complaint.moderator.id if complaint.moderator else None
        with self._connect() as conn:
            if complaint.id:
                conn.execute(
                    """
                    UPDATE complaints
                    SET status = ?, decision = ?, moderator_id = ?
                    WHERE id = ?
                    """,
                    (complaint.status, complaint.decision, moderator_id, complaint.id),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO complaints (student_id, expert_id, material_id, moderator_id, reason, status, decision)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        expert_id,
                        material_id,
                        moderator_id,
                        complaint.reason,
                        complaint.status,
                        complaint.decision,
                    ),
                )
                complaint.id = cur.lastrowid
        return complaint

    def find_complaint(self, complaint_id: int) -> Optional[Complaint]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
            return self._row_to_complaint(row) if row else None

    def find_complaints_by_status(self, status: str) -> list[Complaint]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM complaints WHERE status = ? ORDER BY id ASC",
                (status,),
            ).fetchall()
            return [self._row_to_complaint(r) for r in rows]

    def _row_to_complaint(self, row: sqlite3.Row) -> Complaint:
        author = self.find_student(row["student_id"]) if row["student_id"] else None
        expert = self.find_expert(row["expert_id"]) if row["expert_id"] else None
        material = self.find_material(row["material_id"]) if row["material_id"] else None
        return Complaint(
            id=row["id"],
            reason=row["reason"],
            status=row["status"],
            decision=row["decision"],
            author=author,
            expert=expert,
            material=material,
        )