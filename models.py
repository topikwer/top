from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Student:
    id: int
    name: str
    email: str


@dataclass
class Expert:
    id: int
    name: str
    specialization: str
    qualification: str
    rating: float = 0.0
    verification_status: str = "not_submitted"


@dataclass
class Moderator:
    id: int
    name: str


@dataclass
class ApplicationForm:
    id: int
    specialization: str
    qualification: str
    status: str = "pending"
    expert: Optional[Expert] = None
    moderator: Optional[Moderator] = None
    rejection_reason: Optional[str] = None


@dataclass
class Material:
    id: int
    type: str
    title: str
    publication_date: date
    content: str = ""
    author: Optional[Expert] = None


@dataclass
class Slot:
    id: int
    date_time: datetime
    status: str = "free"
    expert: Optional[Expert] = None


@dataclass
class Payment:
    id: int
    amount: float
    status: str = "pending"
    student: Optional[Student] = None
    slot: Optional[Slot] = None


@dataclass
class Consultation:
    id: int
    date_time: datetime
    status: str = "confirmed"
    expert: Optional[Expert] = None
    student: Optional[Student] = None
    slot: Optional[Slot] = None
    payment: Optional[Payment] = None


@dataclass
class Review:
    id: int
    rating: int
    comment: Optional[str] = None
    consultation: Optional[Consultation] = None
    author: Optional[Student] = None


@dataclass
class Complaint:
    id: int
    reason: str
    status: str = "pending"
    decision: Optional[str] = None
    author: Optional[Student] = None
    expert: Optional[Expert] = None
    material: Optional[Material] = None
    moderator: Optional[Moderator] = None