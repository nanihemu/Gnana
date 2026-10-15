import datetime as dt
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def now():
    return dt.datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # student|teacher|parent|admin
    level: Mapped[str] = mapped_column(String(40), default="high school")  # student level
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Classroom(Base):
    __tablename__ = "classrooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class ParentLink(Base):
    __tablename__ = "parent_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    classroom_id: Mapped[int | None] = mapped_column(ForeignKey("classrooms.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(300), default="")
    kind: Mapped[str] = mapped_column(String(20), default="text")  # text|document|image|audio|video
    level: Mapped[str] = mapped_column(String(40), default="high school")
    text: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[list] = mapped_column(JSON, default=list)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    file_path: Mapped[str] = mapped_column(String(500), default="")  # original upload (teachers' videos, PDFs, notes)
    video_path: Mapped[str] = mapped_column(String(300), default="")
    video_status: Mapped[str] = mapped_column(String(20), default="none")  # none|processing|ready|failed
    video_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Quiz(Base):
    __tablename__ = "quizzes"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    classroom_id: Mapped[int | None] = mapped_column(ForeignKey("classrooms.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="quiz")  # quiz|assessment
    questions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    score: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    results: Mapped[list] = mapped_column(JSON, default=list)  # per-question result
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class CommTask(Base):
    """A daily communication-skills task (speak / write / vocab) for one student."""
    __tablename__ = "comm_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    level: Mapped[str] = mapped_column(String(40))
    skill: Mapped[str] = mapped_column(String(20))  # speak|write|vocab
    source: Mapped[str] = mapped_column(String(20), default="auto")  # auto|teacher
    title: Mapped[str] = mapped_column(String(200))
    prompt: Mapped[str] = mapped_column(Text)
    target: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    response: Mapped[str] = mapped_column(Text, default="")
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    scores: Mapped[dict] = mapped_column(JSON, default=dict)
    feedback: Mapped[dict] = mapped_column(JSON, default=dict)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # null = AI
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
